from fastapi import APIRouter, Response

from backend.app.controllers.dependencies import CurrentUser, NotificationDependency
from backend.app.models.planning import (
    FavoriteKind,
    Subscription,
    SubscriptionSettings,
    DeviceRegistration,
)

router = APIRouter(
    prefix="/me/subscriptions",
    tags=["Notifications"],
    responses={
        503: {
            "description": "Authentication and subscriptions require configured external services."
        }
    },
)


@router.put("/devices/register", status_code=204)
async def register_device(
    body: DeviceRegistration, user_id: CurrentUser, service: NotificationDependency
) -> Response:
    """Associate an FCM registration token with the verified user."""
    await service.register_device(user_id, body.token)
    return Response(status_code=204)


@router.post("/devices/remove", status_code=204)
async def delete_device(
    body: DeviceRegistration, user_id: CurrentUser, service: NotificationDependency
) -> Response:
    """Remove a device registration only when it belongs to the verified user."""
    await service.delete_device(user_id, body.token)
    return Response(status_code=204)


@router.get("", response_model=list[Subscription])
async def list_subscriptions(
    user_id: CurrentUser, service: NotificationDependency
) -> list[Subscription]:
    """Return notification preferences belonging to the verified user."""
    return await service.list_subscriptions(user_id)


@router.put("/{kind}/{target_id}", response_model=Subscription)
async def save_subscription(
    kind: FavoriteKind,
    target_id: str,
    user_id: CurrentUser,
    service: NotificationDependency,
    settings: SubscriptionSettings,
) -> Subscription:
    """Idempotently save an explicit notification preference for a validated target."""
    return await service.save_subscription(user_id, kind, target_id, settings)


@router.delete("/{kind}/{target_id}", status_code=204)
async def delete_subscription(
    kind: FavoriteKind,
    target_id: str,
    user_id: CurrentUser,
    service: NotificationDependency,
) -> Response:
    """Idempotently remove the verified user's notification preference."""
    await service.delete_subscription(user_id, kind, target_id)
    return Response(status_code=204)
