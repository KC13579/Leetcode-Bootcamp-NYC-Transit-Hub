from datetime import UTC, datetime

from backend.app.core.constants import SUBWAY_ROUTES, ROUTE_ALIASES
from backend.app.core.errors import APIError
from backend.app.models.planning import ReroutePattern
from backend.app.repository.RerouteRepository import RerouteRepository
from backend.app.repository.StationRepository import StationRepository
from backend.app.service.AlertService import AlertService


class RerouteService:
    def __init__(
        self,
        repository: RerouteRepository,
        stations: StationRepository,
        alerts: AlertService,
    ):
        """Store the dependencies and initialize the state required by this component."""
        self.repository = repository
        self.stations = stations
        self.alerts = alerts

    async def find_patterns(
        self, route_id: str, direction: str | None
    ) -> list[ReroutePattern]:
        """Return trip-pattern evidence while distinguishing explicit changes from incomplete data."""
        route_id = ROUTE_ALIASES.get(route_id.upper(), route_id.upper())
        if route_id not in SUBWAY_ROUTES:
            raise APIError(404, "Subway route not found.")
        if direction not in {None, "0", "1"}:
            raise APIError(422, "Direction must be 0 (northbound) or 1 (southbound).")
        await self.stations.ensure_loaded()
        alerts = await self.alerts.get_alerts(route=route_id)
        relevant = [
            alert
            for alert in alerts
            if alert.disruption_type in {"reroute", "suspension", "service_change"}
            and (
                direction is None
                or not alert.direction_ids
                or direction in alert.direction_ids
            )
        ]
        evidence = await self.repository.find_patterns(route_id, direction)
        results = []
        for item in evidence:
            trip_alerts = [
                alert
                for alert in relevant
                if not alert.direction_ids or item.direction in alert.direction_ids
            ]
            expected = self._canonical(item.listed_stops)
            skipped = self._canonical(item.skipped_stops)
            added = (
                self._canonical(
                    [
                        stop
                        for stop in item.listed_stops
                        if stop not in item.normal_stops
                    ]
                )
                if item.normal_stops
                else None
            )
            if item.canceled:
                expected = []
                skipped = (
                    self._canonical(item.normal_stops) if item.normal_stops else skipped
                )
            if not (trip_alerts or skipped or added or item.canceled):
                continue
            age = (
                (datetime.now(UTC) - item.updated_at).total_seconds()
                if item.updated_at
                else None
            )
            fresh = (
                age is not None
                and -60 <= age <= self.repository.client.settings.feed_max_age_seconds
            )
            results.append(
                ReroutePattern(
                    route_id=route_id,
                    trip_id=item.trip_id,
                    direction=item.direction,
                    expected_station_ids=expected or ([] if item.canceled else None),
                    skipped_station_ids=skipped or None,
                    added_station_ids=added,
                    alert_ids=[alert.id for alert in trip_alerts],
                    updated_at=item.updated_at,
                    evidence_status="partial" if fresh else "unknown",
                )
            )
        if not results and relevant:
            results.append(
                ReroutePattern(
                    route_id=route_id,
                    direction=direction,
                    alert_ids=[a.id for a in relevant],
                    evidence_status="unknown",
                )
            )
        return results

    def _canonical(self, stops: list[str]) -> list[str]:
        """Resolve source stop IDs and collapse adjacent platforms belonging to the same station."""
        result = []
        for stop in stops:
            canonical = self.stations.resolve_stop_id(stop)
            if canonical and (not result or result[-1] != canonical):
                result.append(canonical)
        return result
