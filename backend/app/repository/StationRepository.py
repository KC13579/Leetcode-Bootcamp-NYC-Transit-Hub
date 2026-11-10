import asyncio
import math
import re

from backend.app.models import Station
from backend.app.sources.mta.client import MTAClient
from backend.app.sources.mta.static import parse_station_rows


class StationRepository:
    """Maps MTA stop/platform IDs to one rider-facing station-complex ID."""

    def __init__(self, client: MTAClient):
        """Store the dependencies and initialize the state required by this component."""
        self._client = client
        self._stations: dict[str, Station] = {}
        self._stop_to_station: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def ensure_loaded(self) -> None:
        """Load station metadata once while preventing simultaneous duplicate downloads."""
        if self._stations:
            return
        async with self._lock:
            if self._stations:
                return
            self._load(await self._client.get_stations_csv())

    def _load(self, csv_text: str) -> None:
        """Group platforms into canonical station complexes and build stop-ID aliases."""
        grouped: dict[str, list] = {}
        for row in parse_station_rows(csv_text):
            grouped.setdefault(row.complex_id, []).append(row)

        stations: dict[str, Station] = {}
        aliases: dict[str, str] = {}
        for complex_id, rows in grouped.items():
            canonical_id = f"mta-complex:{complex_id}"
            names = list(dict.fromkeys(row.name for row in rows))
            stop_ids = sorted({row.stop_id for row in rows})
            station = Station(
                id=canonical_id,
                name=" / ".join(names),
                borough=rows[0].borough,
                ada_status=(
                    "full"
                    if all(row.ada == "1" for row in rows)
                    else (
                        "partial"
                        if any(row.ada in {"1", "2"} for row in rows)
                        else (
                            "none" if all(row.ada == "0" for row in rows) else "unknown"
                        )
                    )
                ),
                latitude=sum(row.latitude for row in rows) / len(rows),
                longitude=sum(row.longitude for row in rows) / len(rows),
                routes=sorted({route for row in rows for route in row.routes}),
                stop_ids=stop_ids,
                north_direction_label=next(
                    (
                        row.north_direction_label
                        for row in rows
                        if row.north_direction_label
                    ),
                    None,
                ),
                south_direction_label=next(
                    (
                        row.south_direction_label
                        for row in rows
                        if row.south_direction_label
                    ),
                    None,
                ),
            )
            stations[canonical_id] = station
            for stop_id in stop_ids:
                aliases[stop_id] = canonical_id
                aliases[f"{stop_id}N"] = canonical_id
                aliases[f"{stop_id}S"] = canonical_id

        self._stations = stations
        self._stop_to_station = aliases

    def get(self, station_id: str) -> Station | None:
        """Read a canonical station from the loaded in-memory index."""
        return self._stations.get(station_id)

    def resolve_stop_id(self, stop_id: str) -> str | None:
        """Translate an MTA platform or parent-stop ID into a canonical station ID."""
        return self._stop_to_station.get(stop_id)

    def search(self, query: str = "", limit: int = 100) -> list[Station]:
        """Search the loaded station index and return name-sorted matching stations."""
        normalized = query.casefold().strip()
        stations = self._stations.values()
        if normalized:
            stations = (
                station
                for station in stations
                if normalized in station.name.casefold()
                or normalized in " ".join(station.routes).casefold()
            )
        return sorted(stations, key=lambda station: station.name)[:limit]

    def match_stop(self, name: str, location: dict, route: str | None) -> str | None:
        """Resolve a provider stop only when its name or nearby location identifies a unique station."""
        candidates = [
            station
            for station in self._stations.values()
            if not route or route in station.routes
        ]
        latlon = location.get("latLng", {})
        if "latitude" in latlon and "longitude" in latlon:
            ranked = sorted(
                (
                    self._distance(
                        latlon["latitude"], latlon["longitude"], s.latitude, s.longitude
                    ),
                    s.id,
                )
                for s in candidates
            )
            if (
                ranked
                and ranked[0][0] < 250
                and (len(ranked) == 1 or ranked[1][0] - ranked[0][0] > 25)
            ):
                return ranked[0][1]
            return None
        key = re.sub(r"[^a-z0-9]", "", name.casefold())
        matches = [
            s.id
            for s in candidates
            if any(
                re.sub(r"[^a-z0-9]", "", part.casefold()) == key
                for part in s.name.split(" / ")
            )
        ]
        return matches[0] if key and len(matches) == 1 else None

    @staticmethod
    def _distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the great-circle distance in meters between two coordinates."""
        x1, x2 = math.radians(lat1), math.radians(lat2)
        delta = (
            math.sin((x2 - x1) / 2) ** 2
            + math.cos(x1) * math.cos(x2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
        )
        return 6371000 * 2 * math.asin(min(1, math.sqrt(delta)))
