from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.models import Arrival, ServiceAlert, ServiceStatus, Station
from app.transit.service import TransitService

router = APIRouter()


def get_transit_service(request: Request) -> TransitService:
    return request.app.state.transit_service


Transit = Annotated[TransitService, Depends(get_transit_service)]


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/stations", response_model=list[Station])
async def list_stations(
    transit: Transit,
    query: str = "",
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Station]:
    return await transit.list_stations(query, limit)


@router.get("/stations/{station_id}", response_model=Station)
async def get_station(station_id: str, transit: Transit) -> Station:
    station = await transit.get_station(station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return station


@router.get("/stations/{station_id}/arrivals", response_model=list[Arrival])
async def get_arrivals(
    station_id: str,
    transit: Transit,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[Arrival]:
    arrivals = await transit.get_arrivals(station_id, limit)
    if arrivals is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return arrivals


@router.get("/alerts", response_model=list[ServiceAlert])
async def get_alerts(
    transit: Transit,
    route: str | None = None,
    station_id: str | None = None,
) -> list[ServiceAlert]:
    return await transit.get_alerts(route=route, station_id=station_id)


@router.get("/status", response_model=list[ServiceStatus])
async def get_status(transit: Transit) -> list[ServiceStatus]:
    return await transit.get_status()
