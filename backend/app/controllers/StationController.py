from fastapi import APIRouter, HTTPException, Query

from backend.app.controllers.dependencies import (
    AccessibilityDependency,
    ArrivalDependency,
    StationDependency,
)
from backend.app.models import Arrival, Station
from backend.app.models.planning import StationAccessibility

router = APIRouter(prefix="/stations", tags=["Stations"])


@router.get("", response_model=list[Station])
async def list_stations(
    service: StationDependency,
    query: str = "",
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Station]:
    """Search canonical stations by name or line and limit the ordered results."""
    return await service.list_stations(query, limit)


@router.get("/{station_id}", response_model=Station)
async def get_station(station_id: str, service: StationDependency) -> Station:
    """Return the station identified by its canonical application ID."""
    station = await service.get_station(station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return station


@router.get("/{station_id}/arrivals", response_model=list[Arrival])
async def get_arrivals(
    station_id: str,
    service: ArrivalDependency,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[Arrival]:
    """Return upcoming arrivals after station matching, time filtering, deduplication and sorting."""
    arrivals = await service.get_arrivals(station_id, limit)
    if arrivals is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return arrivals


@router.get(
    "/{station_id}/accessibility",
    response_model=StationAccessibility,
    responses={
        503: {
            "description": "Accessibility is unavailable until its external service is configured."
        }
    },
)
async def get_accessibility(
    station_id: str, service: AccessibilityDependency
) -> StationAccessibility:
    """Return station accessibility and equipment outage information."""
    return await service.get_station_accessibility(station_id)
