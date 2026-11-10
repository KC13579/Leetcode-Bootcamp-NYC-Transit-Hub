from fastapi import APIRouter

from backend.app.controllers.dependencies import TripDependency
from backend.app.models.planning import (
    TripImpact,
    TripImpactRequest,
    TripPlanRequest,
    TripPlanResponse,
)

router = APIRouter(
    prefix="/trips",
    tags=["Trip planning"],
    responses={
        503: {
            "description": "Trip planning is unavailable until its external service is configured."
        }
    },
)


@router.post("/plan", response_model=TripPlanResponse)
async def plan_trip(body: TripPlanRequest, service: TripDependency) -> TripPlanResponse:
    """Plan transit alternatives for the validated origin, destination and travel time."""
    return await service.compute_routes(body)


@router.post("/impacts", response_model=list[TripImpact])
async def analyze_impacts(
    body: TripImpactRequest, service: TripDependency
) -> list[TripImpact]:
    """Compare each transit segment with alerts by line, station, direction and overlapping times."""
    return await service.analyze_impacts(body)
