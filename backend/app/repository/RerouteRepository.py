import csv
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO, TextIOWrapper
from zipfile import ZipFile, BadZipFile

from google.transit import gtfs_realtime_pb2
from google.protobuf.message import DecodeError

from backend.app.core.constants import ROUTE_ALIASES
from backend.app.core.errors import APIError
from backend.app.sources.mta.client import MTAClient
from backend.app.sources.mta.realtime import feed_paths_for_routes


@dataclass
class PatternEvidence:
    trip_id: str
    direction: str | None
    normal_stops: list[str] | None
    listed_stops: list[str]
    skipped_stops: list[str]
    canceled: bool
    updated_at: datetime | None


class RerouteRepository:
    def __init__(self, client: MTAClient):
        """Store the dependencies and initialize the state required by this component."""
        self.client = client
        self._normal: dict[str, list[str]] = {}
        self._expires_at = 0.0

    async def find_patterns(
        self, route_id: str, direction: str | None
    ) -> list[PatternEvidence]:
        """Return trip-pattern evidence while distinguishing explicit changes from incomplete data."""
        await self._load_normal_patterns()
        result = []
        for path in sorted(feed_paths_for_routes([route_id])):
            payload = await self.client.get_feed(path)
            try:
                message = gtfs_realtime_pb2.FeedMessage()
                message.ParseFromString(payload)
            except DecodeError as exc:
                raise APIError(502, "MTA returned invalid trip-update data.") from exc
            updated = (
                datetime.fromtimestamp(message.header.timestamp, UTC)
                if message.header.timestamp
                else None
            )
            for entity in message.entity:
                if not entity.HasField("trip_update"):
                    continue
                update = entity.trip_update
                trip = update.trip
                if ROUTE_ALIASES.get(trip.route_id, trip.route_id) != route_id:
                    continue
                trip_direction = (
                    str(trip.direction_id) if trip.HasField("direction_id") else None
                )
                listed = [
                    item.stop_id
                    for item in update.stop_time_update
                    if item.stop_id and item.schedule_relationship != 1
                ]
                skipped = [
                    item.stop_id
                    for item in update.stop_time_update
                    if item.stop_id and item.schedule_relationship == 1
                ]
                if trip_direction is None:
                    suffixes = {stop[-1:] for stop in listed + skipped}
                    trip_direction = (
                        "0" if suffixes == {"N"} else "1" if suffixes == {"S"} else None
                    )
                if direction is not None and trip_direction != direction:
                    continue
                result.append(
                    PatternEvidence(
                        trip.trip_id,
                        trip_direction,
                        self._normal.get(trip.trip_id),
                        listed,
                        skipped,
                        trip.schedule_relationship == 3,
                        updated,
                    )
                )
        return result

    async def _load_normal_patterns(self) -> None:
        """Cache scheduled stop sequences for exact trip-ID comparisons."""
        if time.monotonic() < self._expires_at:
            return
        payload = await self.client.get_static_gtfs()
        try:
            grouped = {}
            with ZipFile(BytesIO(payload)) as archive:
                if "stop_times.txt" not in archive.namelist():
                    self._normal = {}
                    self._expires_at = time.monotonic() + 3600
                    return
                with archive.open("stop_times.txt") as stream:
                    for row in csv.DictReader(
                        TextIOWrapper(stream, encoding="utf-8-sig")
                    ):
                        grouped.setdefault(row["trip_id"], []).append(
                            (int(row["stop_sequence"]), row["stop_id"])
                        )
            self._normal = {
                trip: [stop for _, stop in sorted(stops)]
                for trip, stops in grouped.items()
            }
            self._expires_at = time.monotonic() + 21600
        except (BadZipFile, KeyError, ValueError) as exc:
            raise APIError(
                502, "MTA returned invalid static stop-sequence data."
            ) from exc
