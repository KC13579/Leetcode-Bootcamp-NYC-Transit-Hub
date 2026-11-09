import hashlib

from backend.app.core.errors import APIError
from backend.app.models.planning import FavoriteKind, Subscription, SubscriptionSettings
from backend.app.repository.FavoriteRepository import FavoriteRepository
from backend.app.sources.firebase.client import FirebaseClient


class NotificationRepository:
    def __init__(self, client: FirebaseClient):
        """Store the dependencies and initialize the state required by this component."""
        self.client = client

    async def list_subscriptions(self, user_id: str) -> list[Subscription]:
        """Return notification preferences belonging to the verified user."""
        rows = await self.client.list_docs(
            "transit_subscriptions", [("user_id", "==", user_id)]
        )
        return sorted(
            [
                Subscription(
                    kind=row["kind"], target_id=row["target_id"], enabled=row["enabled"]
                )
                for row in rows
            ],
            key=lambda item: (item.kind, item.target_id),
        )

    async def save_subscription(
        self,
        user_id: str,
        kind: FavoriteKind,
        target_id: str,
        settings: SubscriptionSettings,
    ) -> Subscription:
        """Idempotently save an explicit notification preference for a validated target."""
        result = Subscription(kind=kind, target_id=target_id, enabled=settings.enabled)
        await self.client.set_doc(
            "transit_subscriptions",
            FavoriteRepository.key(user_id, kind, target_id),
            {"user_id": user_id, **result.model_dump()},
        )
        return result

    async def delete_subscription(
        self, user_id: str, kind: FavoriteKind, target_id: str
    ) -> None:
        """Idempotently remove the verified user's notification preference."""
        await self.client.delete_doc(
            "transit_subscriptions", FavoriteRepository.key(user_id, kind, target_id)
        )

    async def enabled_subscriptions(self) -> list[dict]:
        """Load subscriptions whose owners explicitly enabled notifications."""
        return await self.client.list_docs(
            "transit_subscriptions", [("enabled", "==", True)]
        )

    async def register_device(self, user_id: str, token: str) -> None:
        """Associate an FCM registration token with the verified user."""
        await self.client.set_doc(
            "transit_devices",
            hashlib.sha256(token.encode()).hexdigest(),
            {"user_id": user_id, "token": token},
        )

    async def delete_device(self, user_id: str, token: str) -> None:
        """Remove a device registration only when it belongs to the verified user."""
        await self.client.delete_device_for_user(user_id, token)

    async def devices_for_user(self, user_id: str) -> list[str]:
        """Return FCM registrations currently owned by the verified user."""
        return [
            row["token"]
            for row in await self.client.list_docs(
                "transit_devices", [("user_id", "==", user_id)]
            )
        ]
