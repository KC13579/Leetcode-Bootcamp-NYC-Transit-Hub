from datetime import UTC, datetime, timedelta
from dataclasses import replace
import json
import hashlib
from copy import deepcopy

from backend.app.core.errors import APIError
from backend.app.sources.google.client import GoogleClient
from backend.app.config import get_settings
from io import BytesIO
from zipfile import ZipFile

import httpx
import pytest
from fastapi.testclient import TestClient
from google.transit import gtfs_realtime_pb2

import backend.app.main as main
from backend.app.sources.mta.client import MTAClient


class MemoryFirebase:
    def __init__(self):
        self.rows = {}
        self.deliveries = {}
        self.sent = []

    async def verify_token(self, token):
        if token not in {"alice", "bob"}:
            raise APIError(401, "Invalid or expired Firebase ID token.")
        return token

    async def list_docs(self, collection, filters=None):
        return [
            dict(deepcopy(value), _id=key)
            for (name, key), value in self.rows.items()
            if name == collection
            and all(
                value.get(field) == expected for field, op, expected in filters or []
            )
        ]

    async def get_doc(self, collection, key):
        return deepcopy(self.rows.get((collection, key)))

    async def set_doc(self, collection, key, data):
        self.rows[collection, key] = deepcopy(data)

    async def delete_doc(self, collection, key):
        self.rows.pop((collection, key), None)

    async def delete_device_for_user(self, user_id, token):
        key = hashlib.sha256(token.encode()).hexdigest()
        if self.rows.get(("transit_devices", key), {}).get("user_id") == user_id:
            self.rows.pop(("transit_devices", key), None)

    async def claim_delivery(self, key):
        if self.deliveries.get(key):
            return False
        self.deliveries[key] = True
        return True

    async def finish_delivery(self, key, sent):
        self.deliveries[key] = sent

    async def send_notification(self, token, title, body, data):
        self.sent.append((token, title, body, data))
        return True


@pytest.fixture
def client(monkeypatch):
    """Exercise real controllers, services and repositories without external calls."""
    cloud = MemoryFirebase()
    monkeypatch.setattr(main, "FirebaseClient", lambda settings: cloud)
    settings = replace(
        get_settings(), google_maps_api_key="test-key", notifications_enabled=False
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    stations = (
        "Complex ID,GTFS Stop ID,Stop Name,Borough,Daytime Routes,"
        "GTFS Latitude,GTFS Longitude,North Direction Label,South Direction Label,ADA\n"
        "611,127,Times Sq-42 St,M,1,40.755,-73.987,Uptown,Downtown,1\n"
        "612,128,Penn Station,M,1,40.750,-73.990,Uptown,Downtown,1\n"
    )
    now = datetime.now(UTC)
    arrivals = gtfs_realtime_pb2.FeedMessage()
    arrivals.header.gtfs_realtime_version = "2.0"
    arrivals.header.timestamp = int(now.timestamp())
    for index, (stop_id, minutes) in enumerate(
        [("127N", 5), ("127N", 5), ("127N", -5), ("999N", 6)]
    ):
        entity = arrivals.entity.add()
        entity.id = str(index)
        entity.trip_update.trip.trip_id = "trip-1"
        entity.trip_update.trip.route_id = "1"
        update = entity.trip_update.stop_time_update.add()
        update.stop_id = stop_id
        update.arrival.time = int((now + timedelta(minutes=minutes)).timestamp())
    alerts = gtfs_realtime_pb2.FeedMessage()
    alerts.header.gtfs_realtime_version = "2.0"
    alerts.header.timestamp = int(now.timestamp())
    entity = alerts.entity.add()
    entity.id = "delay-1"
    entity.alert.effect = gtfs_realtime_pb2.Alert.SIGNIFICANT_DELAYS
    entity.alert.header_text.translation.add(text="Delays", language="en")
    entity.alert.informed_entity.add(route_id="1", stop_id="127N")
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "routes.txt", "route_id,route_short_name,route_color\n1,1,EE352E\n"
        )
        archive.writestr("trips.txt", "route_id,trip_id,shape_id\n1,t1,s1\n")
        archive.writestr(
            "shapes.txt",
            "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\n"
            "s1,40.75,-73.98,1\ns1,40.76,-73.99,2\n",
        )

    requests = []

    def respond(request):
        requests.append(request)
        if "ene_equipments" in str(request.url):
            return httpx.Response(
                200,
                json=[
                    {
                        "stationcomplexid": "611",
                        "equipmentno": "EL1",
                        "equipmenttype": "EL",
                        "serving": "Street to platform",
                    },
                    {
                        "stationcomplexid": "611",
                        "equipmentno": "ES1",
                        "equipmenttype": "ES",
                    },
                ],
            )
        if "nyct_ene.json" in str(request.url):
            return httpx.Response(
                200,
                json=[
                    {
                        "equipment": "EL1",
                        "outagedate": "01/01/2020 01:00:00 PM",
                        "reason": "Repair",
                        "isupcomingoutage": "N",
                    }
                ],
            )

        if str(request.url).endswith("Stations.csv"):
            return httpx.Response(200, text=stations)
        if str(request.url).endswith("gtfs_subway.zip"):
            return httpx.Response(200, content=buffer.getvalue())
        if "subway-alerts" in str(request.url):
            return httpx.Response(200, content=alerts.SerializeToString())
        return httpx.Response(200, content=arrivals.SerializeToString())

    monkeypatch.setattr(
        main,
        "MTAClient",
        lambda settings: MTAClient(settings, transport=httpx.MockTransport(respond)),
    )

    def google_respond(request):
        requests.append(request)
        if request.url.path.endswith("places:autocomplete"):
            return httpx.Response(
                200,
                json={
                    "suggestions": [
                        {
                            "placePrediction": {
                                "placeId": "place-1",
                                "structuredFormat": {
                                    "mainText": {"text": "Times Square"},
                                    "secondaryText": {"text": "NYC"},
                                },
                            }
                        }
                    ]
                },
            )
        if request.url.host == "places.googleapis.com":
            return httpx.Response(
                200,
                json={
                    "id": "place-1",
                    "displayName": {"text": "Times Square"},
                    "formattedAddress": "NYC",
                    "location": {"latitude": 40.755, "longitude": -73.987},
                },
            )
        return httpx.Response(
            200,
            json={
                "routes": [
                    {
                        "duration": "600s",
                        "polyline": {"encodedPolyline": "encoded-path"},
                        "legs": [
                            {
                                "steps": [
                                    {"travelMode": "WALK", "staticDuration": "60s"},
                                    {
                                        "travelMode": "TRANSIT",
                                        "staticDuration": "300s",
                                        "transitDetails": {
                                            "transitLine": {
                                                "nameShort": "1",
                                                "vehicle": {"type": "SUBWAY"},
                                            },
                                            "stopDetails": {
                                                "departureStop": {
                                                    "name": "Times Sq-42 St",
                                                    "location": {
                                                        "latLng": {
                                                            "latitude": 40.755,
                                                            "longitude": -73.987,
                                                        }
                                                    },
                                                },
                                                "arrivalStop": {
                                                    "name": "Penn Station",
                                                    "location": {
                                                        "latLng": {
                                                            "latitude": 40.750,
                                                            "longitude": -73.990,
                                                        }
                                                    },
                                                },
                                            },
                                        },
                                    },
                                ]
                            }
                        ],
                    }
                ]
            },
        )

    monkeypatch.setattr(
        main,
        "GoogleClient",
        lambda settings: GoogleClient(
            settings, transport=httpx.MockTransport(google_respond)
        ),
    )
    with TestClient(main.app) as test_client:
        test_client.cloud = cloud
        test_client.requests = requests
        yield test_client


def test_existing_routes_keep_their_behavior_through_all_layers(client):
    station_id = "mta-complex:611"
    response = client.get("/api/stations", params={"query": "times", "limit": 1})
    assert response.status_code == 200
    assert response.json()[0]["id"] == station_id
    assert client.get(f"/api/stations/{station_id}").json()["routes"] == ["1"]
    assert client.get("/api/stations/missing").status_code == 404
    assert client.get("/api/stations/missing/arrivals").status_code == 404
    arrivals = client.get(f"/api/stations/{station_id}/arrivals").json()
    assert len(arrivals) == 1  # Deduplicate and exclude past or unrelated stops.
    assert arrivals[0]["direction"] == "Northbound"
    assert arrivals[0]["destination"] == "Uptown"
    alerts = client.get("/api/alerts", params={"station_id": station_id}).json()
    assert alerts[0]["station_ids"] == [station_id]
    assert client.get("/api/alerts", params={"route": "F"}).json() == []
    statuses = client.get("/api/status").json()
    assert next(item for item in statuses if item["route"] == "1")["status"] == "Delays"
    assert (
        next(item for item in statuses if item["route"] == "F")["status"]
        == "Good Service"
    )
    network = client.get("/api/map/lines").json()
    assert network["lines"][0]["route"] == "1"


TRIP = {
    "origin": {"station_id": "mta-complex:611"},
    "destination": {"latitude": 40.7, "longitude": -74.0},
}


def test_openapi_exposes_contracts_and_firebase_authentication(client):
    schema = client.get("/openapi.json").json()
    assert "503" in schema["paths"]["/api/trips/plan"]["post"]["responses"]
    assert schema["paths"]["/api/me/favorites"]["get"]["security"] == [
        {"FirebaseIDToken": []}
    ]
    assert "TripPlanRequest" in schema["components"]["schemas"]


def test_trip_contract_rejects_ambiguous_locations_and_conflicting_times(client):
    body = {**TRIP, "origin": {"station_id": "611", "place_id": "ambiguous"}}
    assert client.post("/api/trips/plan", json=body).status_code == 422
    body = {
        **TRIP,
        "departure_time": "2026-11-09T18:00:00Z",
        "arrival_time": "2026-11-09T19:00:00Z",
    }
    assert client.post("/api/trips/plan", json=body).status_code == 422


def test_upstream_failures_keep_the_existing_502_response(client, monkeypatch):
    async def unavailable():
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(
        main.app.state.services.station.repository, "ensure_loaded", unavailable
    )
    response = client.get("/api/stations")
    assert response.status_code == 502
    assert response.json() == {
        "detail": "The MTA data service is temporarily unavailable."
    }


def test_cors_allows_the_planned_frontend_write_methods(client):
    response = client.options(
        "/api/trips/plan",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert "POST" in response.headers["access-control-allow-methods"]


@pytest.mark.parametrize("path", ["/api/me/favorites", "/api/me/subscriptions"])
def test_private_data_requires_verified_token(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert (
        client.get(path, headers={"Authorization": "Bearer forged"}).status_code == 401
    )


def test_google_trip_resolution_normalization_and_session_tokens(client):
    response = client.post("/api/trips/plan", json=TRIP)
    assert response.status_code == 200
    route = response.json()["routes"][0]
    assert route["duration_seconds"] == 600
    assert route["transfer_count"] == 0
    assert [step["mode"] for step in route["segments"]] == ["walking", "subway"]
    assert route["segments"][1]["boarding_station_id"] == "mta-complex:611"
    assert route["segments"][1]["alighting_station_id"] == "mta-complex:612"
    request = next(
        request
        for request in client.requests
        if request.url.host == "routes.googleapis.com"
    )
    body = json.loads(request.content)
    assert body["origin"] == {
        "location": {"latLng": {"latitude": 40.755, "longitude": -73.987}}
    }
    assert body["travelMode"] == "TRANSIT"
    assert (
        client.get(
            "/api/places/autocomplete?query=Times&session_token=session-1"
        ).json()[0]["place_id"]
        == "place-1"
    )
    assert (
        client.get("/api/places/place-1?session_token=session-1").json()["latitude"]
        == 40.755
    )
    autocomplete = next(
        r for r in client.requests if r.url.path.endswith("places:autocomplete")
    )
    assert json.loads(autocomplete.content)["sessionToken"] == "session-1"
    detail = next(r for r in client.requests if r.url.path.endswith("/place-1"))
    assert detail.url.params["sessionToken"] == "session-1"


def test_accessibility_links_equipment_without_inventing_operational_status(client):
    response = client.get("/api/stations/mta-complex:611/accessibility")
    assert response.status_code == 200
    body = response.json()
    assert body["accessible"] is True
    assert body["equipment"][0]["status"] == "out_of_service"
    assert body["equipment"][0]["reason"] == "Repair"
    assert body["equipment"][1]["status"] == "unknown"
    assert body["equipment_status_complete"] is False
    assert client.get("/api/stations/missing/accessibility").status_code == 404


def test_favorites_are_idempotent_and_isolated_by_verified_user(client):
    alice = {"Authorization": "Bearer alice"}
    bob = {"Authorization": "Bearer bob"}
    path = "/api/me/favorites/route/f"
    for _ in range(2):
        response = client.put(path, headers=alice)
        assert response.status_code == 200
        assert response.json() == {"kind": "route", "target_id": "F"}
    assert len(client.get("/api/me/favorites", headers=alice).json()) == 1
    assert client.get("/api/me/favorites", headers=bob).json() == []
    assert client.delete(path, headers=bob).status_code == 204
    assert len(client.get("/api/me/favorites", headers=alice).json()) == 1
    for _ in range(2):
        assert client.delete(path, headers=alice).status_code == 204
    assert client.get("/api/me/favorites", headers=alice).json() == []
    assert client.put("/api/me/favorites/route/FAKE", headers=alice).status_code == 404
    assert (
        client.put("/api/me/favorites/station/missing", headers=alice).status_code
        == 404
    )


def test_subscriptions_devices_delivery_deduplication_and_opt_out(client):
    alice = {"Authorization": "Bearer alice"}
    bob = {"Authorization": "Bearer bob"}
    path = "/api/me/subscriptions/route/1"
    assert client.put(path, headers=alice, json={"enabled": True}).status_code == 200
    assert client.get("/api/me/subscriptions", headers=bob).json() == []
    device = {"token": "test-device-registration-token"}
    register = "/api/me/subscriptions/devices/register"
    assert client.put(register, headers=alice, json=device).status_code == 204
    summary = client.portal.call(main.app.state.services.notification.dispatch_updates)
    assert summary.sent == 1
    assert len(client.cloud.sent) == 1
    summary = client.portal.call(main.app.state.services.notification.dispatch_updates)
    assert summary.sent == 0 and summary.skipped == 1
    # Another user's remove request must not remove Alice's registration.
    remove = "/api/me/subscriptions/devices/remove"
    assert client.post(remove, headers=bob, json=device).status_code == 204
    assert any(
        row.get("token") == device["token"] for row in client.cloud.rows.values()
    )
    assert client.put(path, headers=alice, json={"enabled": False}).status_code == 200
    assert (
        client.portal.call(main.app.state.services.notification.dispatch_updates).sent
        == 0
    )
    assert client.post(remove, headers=alice, json=device).status_code == 204
    assert not any(
        row.get("token") == device["token"] for row in client.cloud.rows.values()
    )
    assert client.delete(path, headers=alice).status_code == 204


def test_impact_analysis_uses_time_station_and_direction_not_just_route_name(client):
    now = datetime.now(UTC)
    body = {
        "departure_time": now.isoformat(),
        "route": {
            "duration_seconds": 300,
            "transfer_count": 0,
            "segments": [
                {
                    "mode": "subway",
                    "duration_seconds": 300,
                    "route_id": "1",
                    "boarding_station_id": "mta-complex:611",
                    "alighting_station_id": "mta-complex:612",
                }
            ],
        },
    }
    response = client.post("/api/trips/impacts", json=body)
    assert response.status_code == 200
    assert response.json()[0]["scope"] == "segment"
    body["route"]["segments"][0]["route_id"] = "F"
    assert client.post("/api/trips/impacts", json=body).json() == []


def test_unconfigured_integrations_return_explicit_service_errors(client):
    from backend.app.sources.firebase.client import FirebaseClient

    main.app.state.google.settings = replace(get_settings(), google_maps_api_key="")
    response = client.get("/api/places/place-1")
    assert response.status_code == 503
    assert "GOOGLE_MAPS_API_KEY" in response.json()["detail"]
    main.app.state.firebase = FirebaseClient(
        replace(get_settings(), firebase_project_id="")
    )
    assert (
        client.get(
            "/api/me/favorites", headers={"Authorization": "Bearer not-real"}
        ).status_code
        == 503
    )


def test_google_error_mapping_empty_routes_and_timeout(client, monkeypatch):
    def unavailable(request):
        raise httpx.ReadTimeout("timeout")

    client.portal.call(main.app.state.google.http.aclose)
    main.app.state.google.http = httpx.AsyncClient(
        transport=httpx.MockTransport(unavailable)
    )
    assert client.get("/api/places/place-1").status_code == 504


def test_reroute_input_validation_and_no_false_changes(client):
    assert client.get("/api/routes/FAKE/reroutes").status_code == 404
    assert client.get("/api/routes/1/reroutes?direction=bad").status_code == 422
    assert client.get("/api/routes/1/reroutes").json() == []
