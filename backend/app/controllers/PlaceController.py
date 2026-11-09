from fastapi import APIRouter, Query

from backend.app.controllers.dependencies import PlaceDependency
from backend.app.models.planning import PlaceDetails, PlaceSuggestion

router = APIRouter(
    prefix="/places",
    tags=["Places"],
    responses={
        503: {
            "description": "Place search is unavailable until its external service is configured."
        }
    },
)


@router.get("/autocomplete", response_model=list[PlaceSuggestion])
async def autocomplete(
    service: PlaceDependency,
    query: str = Query(min_length=1),
    session_token: str | None = None,
) -> list[PlaceSuggestion]:
    """Return place suggestions for a validated search query and optional billing session."""
    return await service.autocomplete(query, session_token)


@router.get("/{place_id}", response_model=PlaceDetails)
async def get_place(
    place_id: str,
    service: PlaceDependency,
    session_token: str | None = None,
) -> PlaceDetails:
    """Return display information and usable coordinates for a Google place ID."""
    return await service.get_place(place_id, session_token)
