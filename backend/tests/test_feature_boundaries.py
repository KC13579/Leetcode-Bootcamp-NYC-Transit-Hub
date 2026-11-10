import ast
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import httpx
import pytest
from firebase_admin import auth, messaging
from google.api_core.exceptions import ServiceUnavailable
from google.transit import gtfs_realtime_pb2

from backend.app.config import get_settings
from backend.app.core.errors import APIError
from backend.app.models.planning import TripPlanRequest
from backend.app.repository.AlertRepository import AlertRepository
from backend.app.repository.RerouteRepository import RerouteRepository
from backend.app.repository.StationRepository import StationRepository
from backend.app.service.AlertService import AlertService
from backend.app.service.RerouteService import RerouteService
from backend.app.sources.firebase.client import FirebaseClient
from backend.app.sources.google.client import GoogleClient
from backend.app.sources.mta.alerts import parse_active_alerts
from backend.app.sources.mta.client import MTAClient


@pytest.mark.parametrize(
    "status,expected", [(400, 422), (403, 502), (404, 404), (429, 503), (500, 502)]
)
async def test_google_errors_are_sanitized(status, expected):
    client = GoogleClient(
        replace(get_settings(), google_maps_api_key="private-test-key"),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, text="upstream secret details")
        ),
    )
    try:
        with pytest.raises(APIError) as captured:
            await client.request(
                "GET", "https://places.googleapis.com/v1/places/example", fields="id"
            )
        assert captured.value.status_code == expected
        assert "secret" not in captured.value.detail
        assert "private-test-key" not in captured.value.detail
    finally:
        await client.close()


@pytest.mark.parametrize("payload", [[], "text", None])
async def test_google_rejects_non_object_payloads(payload):
    client = GoogleClient(
        replace(get_settings(), google_maps_api_key="test-key"),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload)
        ),
    )
    try:
        with pytest.raises(APIError) as captured:
            await client.request(
                "GET", "https://places.googleapis.com/v1/places/example", fields="id"
            )
        assert captured.value.status_code == 502
    finally:
        await client.close()


async def test_firebase_verifier_requires_sdk_signature_expiry_and_revocation_checks(
    monkeypatch,
):
    client = FirebaseClient(replace(get_settings(), firebase_project_id="test-project"))
    monkeypatch.setattr(client, "get_app", lambda: "sdk-app")
    calls = []

    def verify(token, **kwargs):
        calls.append((token, kwargs))
        return {"uid": "verified-user", "sub": "verified-user"}

    monkeypatch.setattr(auth, "verify_id_token", verify)
    assert await client.verify_token("signed-token") == "verified-user"
    assert calls == [("signed-token", {"app": "sdk-app", "check_revoked": True})]

    def invalid(*args, **kwargs):
        raise auth.InvalidIdTokenError("bad token")

    monkeypatch.setattr(auth, "verify_id_token", invalid)
    with pytest.raises(APIError) as captured:
        await client.verify_token("forged-token")
    assert captured.value.status_code == 401


async def test_firebase_certificate_failures_are_unavailable_not_authentication_success(
    monkeypatch,
):
    client = FirebaseClient(replace(get_settings(), firebase_project_id="test-project"))
    monkeypatch.setattr(client, "get_app", lambda: "sdk-app")

    def unavailable(*args, **kwargs):
        raise auth.CertificateFetchError("offline", RuntimeError("offline"))

    monkeypatch.setattr(auth, "verify_id_token", unavailable)
    with pytest.raises(APIError) as captured:
        await client.verify_token("some-token")
    assert captured.value.status_code == 503


async def test_firebase_data_failures_do_not_become_empty_successful_results():
    client = FirebaseClient(get_settings())

    def unavailable():
        raise ServiceUnavailable("offline")

    with pytest.raises(APIError) as captured:
        await client._run(unavailable)
    assert captured.value.status_code == 503


async def test_fcm_uses_real_message_shape_and_removes_rejected_registration(
    monkeypatch,
):
    client = FirebaseClient(get_settings())
    monkeypatch.setattr(client, "get_app", lambda: "sdk-app")
    calls = []
    monkeypatch.setattr(
        messaging, "send", lambda message, app: calls.append((message, app))
    )
    assert await client.send_notification(
        "device-token", "Delay", "Please check service", {"route": "F"}
    )
    assert calls[0][0].token == "device-token"
    assert calls[0][0].notification.title == "Delay"
    assert calls[0][1] == "sdk-app"

    def invalid(message, app):
        raise messaging.UnregisteredError("invalid registration")

    removed = []

    async def remove(collection, key):
        removed.append((collection, key))

    monkeypatch.setattr(messaging, "send", invalid)
    monkeypatch.setattr(client, "delete_doc", remove)
    assert not await client.send_notification("device-token", "Delay", "Message", {})
    assert removed[0][0] == "transit_devices"


def test_alert_window_keeps_future_disruptions_and_respects_end_time():
    now = datetime.now(UTC)
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    alert = feed.entity.add(id="future").alert
    alert.header_text.translation.add(text="Planned reroute", language="en")
    alert.effect = gtfs_realtime_pb2.Alert.DETOUR
    period = alert.active_period.add(
        start=int((now + timedelta(hours=1)).timestamp()),
        end=int((now + timedelta(hours=2)).timestamp()),
    )
    alert.informed_entity.add(route_id="F").trip.direction_id = 0
    assert parse_active_alerts(feed.SerializeToString(), now=now) == []
    result = parse_active_alerts(
        feed.SerializeToString(),
        now=now,
        window_end=now + timedelta(hours=1, minutes=10),
    )
    assert len(result) == 1 and result[0].direction_ids == ("0",)
    assert (
        parse_active_alerts(feed.SerializeToString(), now=now + timedelta(hours=3))
        == []
    )


async def test_reroute_uses_explicit_skips_and_preserves_missing_stop_uncertainty():
    now = datetime.now(UTC)
    stations = (
        "Complex ID,GTFS Stop ID,Stop Name,Borough,Daytime Routes,GTFS Latitude,GTFS Longitude,North Direction Label,South Direction Label\n"
        "1,101,First,M,F,40.7,-74,N,S\n2,102,Second,M,F,40.71,-74,N,S\n3,103,Third,M,F,40.72,-74,N,S\n"
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "stop_times.txt",
            "trip_id,stop_id,stop_sequence\nknown,101N,1\nknown,102N,2\nknown,103N,3\n",
        )
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = int(now.timestamp())
    update = feed.entity.add(id="known").trip_update
    update.trip.trip_id = "known"
    update.trip.route_id = "F"
    update.trip.direction_id = 0
    update.stop_time_update.add(stop_id="101N", stop_sequence=1)
    update.stop_time_update.add(
        stop_id="102N", stop_sequence=2, schedule_relationship=1
    )
    # The absent final update is not evidence that the third stop is skipped.
    alerts = gtfs_realtime_pb2.FeedMessage()
    alerts.header.gtfs_realtime_version = "2.0"
    alerts.header.timestamp = int(now.timestamp())

    def respond(request):
        if str(request.url).endswith("Stations.csv"):
            return httpx.Response(200, text=stations)
        if str(request.url).endswith("gtfs_subway.zip"):
            return httpx.Response(200, content=buffer.getvalue())
        return httpx.Response(
            200,
            content=(
                alerts.SerializeToString()
                if "alerts" in str(request.url)
                else feed.SerializeToString()
            ),
        )

    client = MTAClient(get_settings(), transport=httpx.MockTransport(respond))
    try:
        registry = StationRepository(client)
        service = RerouteService(
            RerouteRepository(client),
            registry,
            AlertService(AlertRepository(client), registry),
        )
        result = await service.find_patterns("F", "0")
        assert len(result) == 1
        assert result[0].skipped_station_ids == ["mta-complex:2"]
        assert result[0].expected_station_ids == ["mta-complex:1"]
        assert result[0].evidence_status == "partial"
        assert await service.find_patterns("F", "1") == []
    finally:
        await client.close()


async def test_missing_feed_timestamp_never_produces_good_service():
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"

    def respond(request):
        if str(request.url).endswith("Stations.csv"):
            return httpx.Response(
                200,
                text="Complex ID,GTFS Stop ID,Stop Name,Borough,Daytime Routes,GTFS Latitude,GTFS Longitude\n1,101,First,M,F,40.7,-74\n",
            )
        return httpx.Response(200, content=feed.SerializeToString())

    from backend.app.service.StatusService import StatusService

    client = MTAClient(get_settings(), transport=httpx.MockTransport(respond))
    try:
        alerts = AlertService(AlertRepository(client), StationRepository(client))
        results = await StatusService(alerts).get_status()
        assert all(result.status == "Unknown" for result in results)
    finally:
        await client.close()


def test_every_backend_method_has_an_english_entry_docstring():
    base = Path(__file__).resolve().parents[1] / "app"
    for path in base.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                summary = ast.get_docstring(node)
                assert (
                    summary and summary.isascii()
                ), f"Missing English entry documentation: {path}:{node.name}"
