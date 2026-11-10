from fastapi import APIRouter

from backend.app.controllers.dependencies import RerouteDependency
from backend.app.models.planning import ReroutePattern

router = APIRouter(
    prefix="/routes",
    tags=["Reroutes"],
    responses={
        503: {
            "description": "Reroute analysis is unavailable until its external service is configured."
        }
    },
)


@router.get("/{route_id}/reroutes", response_model=list[ReroutePattern])
async def get_reroutes(
    route_id: str,
    service: RerouteDependency,
    direction: str | None = None,
) -> list[ReroutePattern]:
    """Return direction-specific reroute evidence for a subway line."""
    return await service.find_patterns(route_id, direction)
