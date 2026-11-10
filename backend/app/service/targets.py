from backend.app.core.constants import ROUTE_ALIASES, SUBWAY_ROUTES
from backend.app.core.errors import APIError
from backend.app.repository.StationRepository import StationRepository


async def resolve_target(kind: str, target_id: str, stations: StationRepository) -> str:
    """Validate and normalize a station or subway-line preference target."""
    if kind == "route":
        target = ROUTE_ALIASES.get(target_id.upper(), target_id.upper())
        if target not in SUBWAY_ROUTES:
            raise APIError(404, "Subway route not found.")
        return target
    if kind != "station":
        raise APIError(422, "Target kind must be station or route.")
    await stations.ensure_loaded()
    if stations.get(target_id) is None:
        raise APIError(404, "Station not found")
    return target_id
