from backend.app.core.constants import SUBWAY_ROUTES
from backend.app.models import ServiceAlert, ServiceStatus
from backend.app.service.AlertService import AlertService


class StatusService:
    def __init__(self, alerts: AlertService):
        """Store the dependencies and initialize the state required by this component."""
        self.alerts = alerts

    async def get_status(self) -> list[ServiceStatus]:
        """Aggregate alerts into per-line service states while retaining freshness information."""
        alerts = await self.alerts.get_alerts()
        statuses: list[ServiceStatus] = []
        for route in SUBWAY_ROUTES:
            relevant = [
                alert for alert in alerts if route in alert.routes or not alert.routes
            ]
            statuses.append(
                ServiceStatus(
                    route=route,
                    status=(
                        self._status_for(relevant)
                        if self.alerts.data_status == "fresh"
                        else "Unknown"
                    ),
                    updated_at=self.alerts.repository.updated_at,
                    data_status=self.alerts.data_status,
                    alert_count=len(relevant),
                    alerts=relevant,
                )
            )
        return statuses

    @staticmethod
    def _status_for(alerts: list[ServiceAlert]) -> str:
        """Select the most significant reported service state for a line."""
        effects = {alert.effect for alert in alerts}
        titles = " ".join(alert.title.casefold() for alert in alerts)
        if "NO_SERVICE" in effects or "suspend" in titles:
            return "Suspended"
        if "DETOUR" in effects or "rerout" in titles:
            return "Rerouted"
        if {"SIGNIFICANT_DELAYS", "REDUCED_SERVICE"} & effects or "delay" in titles:
            return "Delays"
        if alerts:
            return "Service Change"
        return "Good Service"
