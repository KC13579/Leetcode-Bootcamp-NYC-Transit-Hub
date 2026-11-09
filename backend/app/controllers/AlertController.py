from fastapi import APIRouter

from backend.app.controllers.dependencies import AlertDependency
from backend.app.models import ServiceAlert

router = APIRouter(tags=["Alerts"])


@router.get("/alerts", response_model=list[ServiceAlert])
async def get_alerts(
    service: AlertDependency,
    route: str | None = None,
    station_id: str | None = None,
) -> list[ServiceAlert]:
    """Return normalized alerts filtered by line, station and the requested time window."""
    return await service.get_alerts(route=route, station_id=station_id)
