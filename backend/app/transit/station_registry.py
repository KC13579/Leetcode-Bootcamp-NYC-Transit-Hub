import asyncio

from app.models import Station
from app.sources.mta.client import MTAClient
from app.sources.mta.static import parse_station_rows


class StationRegistry:
    """Maps MTA stop/platform IDs to one rider-facing station-complex ID."""

    def __init__(self, client: MTAClient):
        self._client = client
        self._stations: dict[str, Station] = {}
        self._stop_to_station: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def ensure_loaded(self) -> None:
        if self._stations:
            return
        async with self._lock:
            if self._stations:
                return
            self._load(await self._client.get_stations_csv())

    def _load(self, csv_text: str) -> None:
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
                latitude=sum(row.latitude for row in rows) / len(rows),
                longitude=sum(row.longitude for row in rows) / len(rows),
                routes=sorted({route for row in rows for route in row.routes}),
                stop_ids=stop_ids,
                north_direction_label=next(
                    (row.north_direction_label for row in rows if row.north_direction_label),
                    None,
                ),
                south_direction_label=next(
                    (row.south_direction_label for row in rows if row.south_direction_label),
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
        return self._stations.get(station_id)

    def resolve_stop_id(self, stop_id: str) -> str | None:
        return self._stop_to_station.get(stop_id)

    def search(self, query: str = "", limit: int = 100) -> list[Station]:
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
