from backend.app.core.constants import ROUTE_ALIASES
import asyncio
import hashlib
import json
import logging

from backend.app.core.errors import APIError
from backend.app.models.planning import (
    DeliverySummary,
    FavoriteKind,
    Subscription,
    SubscriptionSettings,
)
from backend.app.models.transit import ServiceAlert
from backend.app.repository.NotificationRepository import NotificationRepository
from backend.app.repository.StationRepository import StationRepository
from backend.app.service.AlertService import AlertService
from backend.app.service.AccessibilityService import AccessibilityService
from backend.app.service.targets import resolve_target

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(
        self,
        repository: NotificationRepository,
        stations: StationRepository,
        alerts: AlertService,
        accessibility: AccessibilityService,
    ):
        """Store the dependencies and initialize the state required by this component."""
        self.repository = repository
        self.stations = stations
        self.alerts = alerts
        self.accessibility = accessibility
        self._dispatch_lock = asyncio.Lock()

    async def list_subscriptions(self, user_id: str) -> list[Subscription]:
        """Return notification preferences belonging to the verified user."""
        return await self.repository.list_subscriptions(user_id)

    async def save_subscription(
        self,
        user_id: str,
        kind: FavoriteKind,
        target_id: str,
        settings: SubscriptionSettings,
    ) -> Subscription:
        """Idempotently save an explicit notification preference for a validated target."""
        target = await resolve_target(kind, target_id, self.stations)
        return await self.repository.save_subscription(user_id, kind, target, settings)

    async def delete_subscription(
        self, user_id: str, kind: FavoriteKind, target_id: str
    ) -> None:
        """Idempotently remove the verified user's notification preference."""
        target = (
            ROUTE_ALIASES.get(target_id.upper(), target_id.upper())
            if kind == "route"
            else target_id
        )
        await self.repository.delete_subscription(user_id, kind, target)

    async def register_device(self, user_id: str, token: str) -> None:
        """Associate an FCM registration token with the verified user."""
        await self.repository.register_device(user_id, token)

    async def delete_device(self, user_id: str, token: str) -> None:
        """Remove a device registration only when it belongs to the verified user."""
        await self.repository.delete_device(user_id, token)

    async def dispatch_updates(self) -> DeliverySummary:
        """Deliver opted-in disruption updates with per-device delivery deduplication."""
        async with self._dispatch_lock:
            summary = DeliverySummary()
            for subscription in await self.repository.enabled_subscriptions():
                try:
                    await self._dispatch_subscription(subscription, summary)
                except Exception as exc:
                    # One failing subscription must not prevent other opted-in users from receiving updates.
                    logger.warning(
                        "Notification subscription processing failed (%s).",
                        type(exc).__name__,
                    )
                    summary.failed += 1
            return summary

    async def _dispatch_subscription(
        self, subscription: dict, summary: DeliverySummary
    ) -> None:
        """Match one subscription to current alerts and send each new event to its devices."""
        user_id = subscription["user_id"]
        tokens = await self.repository.devices_for_user(user_id)
        if not tokens:
            summary.skipped += 1
            return
        kind, target = subscription["kind"], subscription["target_id"]
        alerts = await self.alerts.get_alerts(
            route=target if kind == "route" else None,
            station_id=target if kind == "station" else None,
        )
        # Do not send notifications based on stale or unverifiable service-alert snapshots.
        alerts = [alert for alert in alerts if not alert.is_stale]
        if kind == "station":
            station = await self.accessibility.get_station_accessibility(target)
            for equipment in station.equipment:
                if equipment.status == "out_of_service":
                    alerts.append(
                        ServiceAlert(
                            id=f"equipment:{equipment.equipment_id}:{equipment.outage_start}",
                            title=f"{equipment.kind.title()} outage",
                            description=equipment.reason,
                            routes=[],
                            station_ids=[target],
                            effect="ACCESSIBILITY_ISSUE",
                            starts_at=equipment.outage_start,
                        )
                    )
        for alert in alerts:
            fingerprint = hashlib.sha256(
                json.dumps(
                    alert.model_dump(mode="json", exclude={"updated_at", "is_stale"}),
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            for token in tokens:
                key = hashlib.sha256(
                    f"{user_id}\0{token}\0{fingerprint}".encode()
                ).hexdigest()
                if not await self.repository.client.claim_delivery(key):
                    summary.skipped += 1
                    continue
                try:
                    sent = await self.repository.client.send_notification(
                        token,
                        alert.title,
                        alert.description or alert.title,
                        {"alert_id": alert.id, "kind": kind, "target_id": target},
                    )
                    await self.repository.client.finish_delivery(key, sent)
                    if sent:
                        summary.sent += 1
                    else:
                        summary.failed += 1
                except APIError:
                    await self.repository.client.finish_delivery(key, False)
                    summary.failed += 1

    async def run_worker(self, interval_seconds: int) -> None:
        """Run notification checks periodically until the task is cancelled."""
        while True:
            try:
                await self.dispatch_updates()
            except Exception as exc:
                logger.warning(
                    "Notification dispatch cycle failed (%s).", type(exc).__name__
                )
            await asyncio.sleep(interval_seconds)
