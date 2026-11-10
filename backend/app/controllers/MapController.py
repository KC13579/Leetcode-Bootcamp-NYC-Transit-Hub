from fastapi import APIRouter

from backend.app.controllers.dependencies import MapDependency
from backend.app.models import MapNetwork

router = APIRouter(prefix="/map", tags=["Map"])


@router.get("/lines", response_model=MapNetwork)
async def get_map_network(service: MapDependency) -> MapNetwork:
    """Return the static subway line geometry used by the map."""
    return await service.get_map_network()
