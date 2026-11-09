from datetime import UTC, datetime

from backend.app.core.constants import ROUTE_ALIASES
from backend.app.models import ServiceAlert
from backend.app.repository.AlertRepository import AlertRepository
from backend.app.repository.StationRepository import StationRepository
from backend.app.sources.mta.alerts import MTAAlert


class AlertService:
    def __init__(self, repository: AlertRepository, stations: StationRepository):
        """Store the dependencies and initialize the state required by this component."""
        self.repository = repository
        self.stations = stations

    async def get_alerts(
        self,
        route: str | None = None,
        station_id: str | None = None,
        at: datetime | None = None,
        window_end: datetime | None = None,
    ) -> list[ServiceAlert]:
        """Return normalized alerts filtered by line, station and the requested time window."""
        await self.stations.ensure_loaded()
        items = await self.repository.find_active(at, window_end)
        alerts = [self._normalize_alert(item) for item in items]
        if route:
            alerts = [
                item
                for item in alerts
                if route.upper() in item.routes or not item.routes
            ]
        if station_id:
            station = self.stations.get(station_id)
            if station is None:
                from backend.app.core.errors import APIError

                raise APIError(404, "Station not found")
            alerts = [
                item
                for item in alerts
                if station_id in item.station_ids
                or (
                    item.scope == "line"
                    and (not item.routes or set(station.routes) & set(item.routes))
                )
            ]
        return alerts

    @property
    def data_status(self) -> str:
        """Describe whether the alert snapshot is fresh, stale or missing its source timestamp."""
        updated = self.repository.updated_at
        if updated is None:
            return "unknown"
        age = (datetime.now(UTC) - updated).total_seconds()
        return (
            "fresh"
            if -60 <= age <= self.repository.client.settings.feed_max_age_seconds
            else "stale"
        )

    def _normalize_alert(self, item: MTAAlert) -> ServiceAlert:
        """Map source alert fields and stop identifiers into the public application model."""
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
            cause=item.cause,
            direction_ids=list(item.direction_ids),
            updated_at=self.repository.updated_at,
            is_stale=self.data_status != "fresh",
            scope=(
                "line"
                if item.route_scoped
                else ("station" if station_ids else "unknown")
            ),
            disruption_type=self._disruption_type(item.effect, item.title),
            title=item.title,
            description=item.description,
            routes=routes,
            station_ids=station_ids,
            effect=item.effect,
            starts_at=item.starts_at,
            ends_at=item.ends_at,
        )

    @staticmethod
    def _disruption_type(effect: str, title: str) -> str:
        """Classify the reported service effect without inventing a numeric delay."""
        if effect == "NO_SERVICE":
            return "suspension"
        if effect == "DETOUR" or "rerout" in title.casefold():
            return "reroute"
        if effect in {"SIGNIFICANT_DELAYS", "REDUCED_SERVICE"}:
            return "delay"
        if effect in {"STOP_MOVED", "MODIFIED_SERVICE"}:
            return "service_change"
        return "other"
