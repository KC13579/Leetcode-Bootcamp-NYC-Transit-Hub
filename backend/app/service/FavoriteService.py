from backend.app.core.constants import ROUTE_ALIASES
from backend.app.models.planning import Favorite, FavoriteKind
from backend.app.repository.FavoriteRepository import FavoriteRepository
from backend.app.repository.StationRepository import StationRepository
from backend.app.service.targets import resolve_target


class FavoriteService:
    def __init__(self, repository: FavoriteRepository, stations: StationRepository):
        """Store the dependencies and initialize the state required by this component."""
        self.repository = repository
        self.stations = stations

    async def list_favorites(self, user_id: str) -> list[Favorite]:
        """Return only favorites belonging to the verified user."""
        return await self.repository.list_favorites(user_id)

    async def save_favorite(
        self, user_id: str, kind: FavoriteKind, target_id: str
    ) -> Favorite:
        """Idempotently persist a validated favorite under the verified user."""
        target = await resolve_target(kind, target_id, self.stations)
        return await self.repository.save_favorite(user_id, kind, target)

    async def delete_favorite(
        self, user_id: str, kind: FavoriteKind, target_id: str
    ) -> None:
        # Deletion must still work after a station or route disappears from the upstream catalog.
        """Idempotently remove a favorite without affecting another user."""
        target = (
            ROUTE_ALIASES.get(target_id.upper(), target_id.upper())
            if kind == "route"
            else target_id
        )
        await self.repository.delete_favorite(user_id, kind, target)
