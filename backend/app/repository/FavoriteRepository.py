import hashlib

from backend.app.models.planning import Favorite, FavoriteKind
from backend.app.sources.firebase.client import FirebaseClient


class FavoriteRepository:
    def __init__(self, client: FirebaseClient):
        """Store the dependencies and initialize the state required by this component."""
        self.client = client

    @staticmethod
    def key(user_id: str, kind: str, target_id: str) -> str:
        """Derive a deterministic user-scoped document key without using caller-provided paths."""
        return hashlib.sha256(f"{user_id}\0{kind}\0{target_id}".encode()).hexdigest()

    async def list_favorites(self, user_id: str) -> list[Favorite]:
        """Return only favorites belonging to the verified user."""
        rows = await self.client.list_docs(
            "transit_favorites", [("user_id", "==", user_id)]
        )
        return sorted(
            [Favorite(kind=row["kind"], target_id=row["target_id"]) for row in rows],
            key=lambda item: (item.kind, item.target_id),
        )

    async def save_favorite(
        self, user_id: str, kind: FavoriteKind, target_id: str
    ) -> Favorite:
        """Idempotently persist a validated favorite under the verified user."""
        favorite = Favorite(kind=kind, target_id=target_id)
        await self.client.set_doc(
            "transit_favorites",
            self.key(user_id, kind, target_id),
            {"user_id": user_id, **favorite.model_dump()},
        )
        return favorite

    async def delete_favorite(
        self, user_id: str, kind: FavoriteKind, target_id: str
    ) -> None:
        """Idempotently remove a favorite without affecting another user."""
        await self.client.delete_doc(
            "transit_favorites", self.key(user_id, kind, target_id)
        )
