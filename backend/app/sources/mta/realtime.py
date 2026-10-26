from dataclasses import dataclass
from datetime import UTC, datetime

from google.transit import gtfs_realtime_pb2


FEEDS_BY_ROUTE = {
    **{route: "nyct%2Fgtfs" for route in ("1", "2", "3", "4", "5", "6", "7")},
    **{route: "nyct%2Fgtfs-ace" for route in ("A", "C", "E")},
    **{route: "nyct%2Fgtfs-bdfm" for route in ("B", "D", "F", "M")},
    "G": "nyct%2Fgtfs-g",
    **{route: "nyct%2Fgtfs-jz" for route in ("J", "Z")},
    **{route: "nyct%2Fgtfs-nqrw" for route in ("N", "Q", "R", "W")},
    "L": "nyct%2Fgtfs-l",
    "SIR": "nyct%2Fgtfs-si",
}


@dataclass(frozen=True)
class MTAArrival:
    route: str
    stop_id: str
    trip_id: str
    arrival_time: datetime


def feed_paths_for_routes(routes: list[str]) -> set[str]:
    paths = {FEEDS_BY_ROUTE[route] for route in routes if route in FEEDS_BY_ROUTE}
    # The three subway shuttles are split between the numbered and ACE feeds.
    if "S" in routes:
        paths.update({"nyct%2Fgtfs", "nyct%2Fgtfs-ace"})
    return paths or {"nyct%2Fgtfs"}


def parse_arrivals(payload: bytes) -> list[MTAArrival]:
    message = gtfs_realtime_pb2.FeedMessage()
    message.ParseFromString(payload)
    arrivals: list[MTAArrival] = []

    for entity in message.entity:
        if not entity.HasField("trip_update"):
            continue
        trip = entity.trip_update.trip
        for update in entity.trip_update.stop_time_update:
            timestamp = update.arrival.time or update.departure.time
            if not timestamp or not update.stop_id:
                continue
            arrivals.append(
                MTAArrival(
                    route=trip.route_id,
                    stop_id=update.stop_id,
                    trip_id=trip.trip_id,
                    arrival_time=datetime.fromtimestamp(timestamp, tz=UTC),
                )
            )
    return arrivals
