from backend.app.core.errors import APIError
from backend.app.models.planning import PlaceDetails, PlaceSuggestion
from backend.app.repository.PlaceRepository import PlaceRepository


class PlaceService:
    def __init__(self, repository: PlaceRepository):
        """Store the dependencies and initialize the state required by this component."""
        self.repository = repository

    async def autocomplete(
        self, query: str, session_token: str | None
    ) -> list[PlaceSuggestion]:
        """Return place suggestions for a validated search query and optional billing session."""
        query = query.strip()
        if not query or len(query) > 200:
            raise APIError(422, "Place query must contain 1 to 200 characters.")
        return await self.repository.autocomplete(query, session_token)

    async def get_place(self, place_id: str, session_token: str | None) -> PlaceDetails:
        """Return display information and usable coordinates for a Google place ID."""
        if not place_id.strip() or len(place_id) > 300:
            raise APIError(422, "Invalid place ID.")
        return await self.repository.get_place(place_id, session_token)
