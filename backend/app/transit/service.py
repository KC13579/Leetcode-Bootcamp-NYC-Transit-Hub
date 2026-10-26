import asyncio
import math
from datetime import UTC, datetime, timedelta

from app.models import Arrival, ServiceAlert, ServiceStatus, Station
from app.sources.mta.alerts import MTAAlert, parse_active_alerts
from app.sources.mta.client import MTAClient
from app.sources.mta.realtime import feed_paths_for_routes, parse_arrivals
from app.transit.station_registry import StationRegistry


SUBWAY_ROUTES = list("1234567") + list("ACEBDFMGJZLNRWQ") + ["S", "SIR"]
ROUTE_ALIASES = {"GS": "S", "FS": "S", "H": "S", "SI": "SIR"}


class TransitService:
    def __init__(self, client: MTAClient, stations: StationRegistry):
        self.client = client
        self.stations = stations

    async def list_stations(self, query: str, limit: int) -> list[Station]:
        await self.stations.ensure_loaded()
        return self.stations.search(query, limit)

    async def get_station(self, station_id: str) -> Station | None:
        await self.stations.ensure_loaded()
        return self.stations.get(station_id)

    async def get_arrivals(self, station_id: str, limit: int) -> list[Arrival] | None:
        await self.stations.ensure_loaded()
        station = self.stations.get(station_id)
        if not station:
            return None

        payloads = await asyncio.gather(
            *(self.client.get_feed(path) for path in feed_paths_for_routes(station.routes))
        )
        now = datetime.now(UTC)
        cutoff = now + timedelta(hours=2)
        results: list[Arrival] = []
        seen: set[tuple[str, str, datetime]] = set()
        for payload in payloads:
            for item in parse_arrivals(payload):
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

    async def get_alerts(
        self, route: str | None = None, station_id: str | None = None
    ) -> list[ServiceAlert]:
        await self.stations.ensure_loaded()
        payload = await self.client.get_feed("camsys%2Fsubway-alerts")
        alerts = [self._normalize_alert(item) for item in parse_active_alerts(payload)]
        if route:
            alerts = [item for item in alerts if route.upper() in item.routes]
        if station_id:
            alerts = [item for item in alerts if station_id in item.station_ids]
        return alerts

    async def get_status(self) -> list[ServiceStatus]:
        alerts = await self.get_alerts()
        statuses: list[ServiceStatus] = []
        for route in SUBWAY_ROUTES:
            relevant = [alert for alert in alerts if route in alert.routes]
            statuses.append(
                ServiceStatus(
                    route=route,
                    status=self._status_for(relevant),
                    alert_count=len(relevant),
                    alerts=relevant,
                )
            )
        return statuses

    def _normalize_alert(self, item: MTAAlert) -> ServiceAlert:
        station_ids = sorted(
            {
                canonical_id
                for stop_id in item.stop_ids
                if (canonical_id := self.stations.resolve_stop_id(stop_id))
            }
        )
        routes = sorted({ROUTE_ALIASES.get(route, route) for route in item.routes})
        return ServiceAlert(
            id=item.id,
            title=item.title,
            description=item.description,
            routes=routes,
            station_ids=station_ids,
            effect=item.effect,
            starts_at=item.starts_at,
            ends_at=item.ends_at,
        )

    @staticmethod
    def _status_for(alerts: list[ServiceAlert]) -> str:
        effects = {alert.effect for alert in alerts}
        titles = " ".join(alert.title.casefold() for alert in alerts)
        if "NO_SERVICE" in effects or "suspend" in titles:
            return "Suspended"
        if {"SIGNIFICANT_DELAYS", "REDUCED_SERVICE"} & effects or "delay" in titles:
            return "Delays"
        if alerts:
            return "Service Change"
        return "Good Service"
