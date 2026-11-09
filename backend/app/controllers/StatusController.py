from fastapi import APIRouter

from backend.app.controllers.dependencies import StatusDependency
from backend.app.models import ServiceStatus

router = APIRouter(tags=["Service status"])


@router.get("/status", response_model=list[ServiceStatus])
async def get_status(service: StatusDependency) -> list[ServiceStatus]:
    """Aggregate alerts into per-line service states while retaining freshness information."""
    return await service.get_status()
