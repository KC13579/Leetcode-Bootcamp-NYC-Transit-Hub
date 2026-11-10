import math
from datetime import UTC, datetime, timedelta

from backend.app.core.constants import ROUTE_ALIASES
from backend.app.models import Arrival
from backend.app.repository.ArrivalRepository import ArrivalRepository
from backend.app.repository.StationRepository import StationRepository


class ArrivalService:
    def __init__(self, repository: ArrivalRepository, stations: StationRepository):
        """Store the dependencies and initialize the state required by this component."""
        self.repository = repository
        self.stations = stations

    async def get_arrivals(self, station_id: str, limit: int) -> list[Arrival] | None:
        """Return upcoming arrivals after station matching, time filtering, deduplication and sorting."""
        await self.stations.ensure_loaded()
        station = self.stations.get(station_id)
        if not station:
            return None

        raw_arrivals = await self.repository.find_by_routes(station.routes)
        now = datetime.now(UTC)
        cutoff = now + timedelta(hours=2)
        results: list[Arrival] = []
        seen: set[tuple[str, str, datetime]] = set()
        for item in raw_arrivals:
            if self.stations.resolve_stop_id(item.stop_id) != station_id:
                continue
            if not now <= item.arrival_time <= cutoff:
                continue
            route = ROUTE_ALIASES.get(item.route, item.route)
            key = (item.trip_id, item.stop_id, item.arrival_time)
            if key in seen:
                continue
            seen.add(key)
            northbound = item.stop_id.endswith("N")
            results.append(
                Arrival(
                    route=route,
                    direction="Northbound" if northbound else "Southbound",
                    destination=(
                        station.north_direction_label
                        if northbound
                        else station.south_direction_label
                    ),
                    arrival_time=item.arrival_time,
                    minutes_away=max(
                        0, math.ceil((item.arrival_time - now).total_seconds() / 60)
                    ),
                    trip_id=item.trip_id,
                )
            )
        return sorted(results, key=lambda item: item.arrival_time)[:limit]
