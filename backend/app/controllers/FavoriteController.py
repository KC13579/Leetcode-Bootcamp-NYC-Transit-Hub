from fastapi import APIRouter, Response

from backend.app.controllers.dependencies import CurrentUser, FavoriteDependency
from backend.app.models.planning import Favorite, FavoriteKind

router = APIRouter(
    prefix="/me/favorites",
    tags=["Favorites"],
    responses={
        503: {
            "description": "Authentication and favorites require configured external services."
        }
    },
)


@router.get("", response_model=list[Favorite])
async def list_favorites(
    user_id: CurrentUser, service: FavoriteDependency
) -> list[Favorite]:
    """Return only favorites belonging to the verified user."""
    return await service.list_favorites(user_id)


@router.put("/{kind}/{target_id}", response_model=Favorite)
async def save_favorite(
    kind: FavoriteKind,
    target_id: str,
    user_id: CurrentUser,
    service: FavoriteDependency,
) -> Favorite:
    """Idempotently persist a validated favorite under the verified user."""
    return await service.save_favorite(user_id, kind, target_id)


@router.delete("/{kind}/{target_id}", status_code=204)
async def delete_favorite(
    kind: FavoriteKind,
    target_id: str,
    user_id: CurrentUser,
    service: FavoriteDependency,
) -> Response:
    """Idempotently remove a favorite without affecting another user."""
    await service.delete_favorite(user_id, kind, target_id)
    return Response(status_code=204)
