from backend.app.core.errors import APIError
from backend.app.models.planning import StationAccessibility
from backend.app.repository.AccessibilityRepository import AccessibilityRepository
from backend.app.repository.StationRepository import StationRepository


class AccessibilityService:
    def __init__(
        self, repository: AccessibilityRepository, stations: StationRepository
    ):
        """Store the dependencies and initialize the state required by this component."""
        self.repository = repository
        self.stations = stations

    async def get_station_accessibility(self, station_id: str) -> StationAccessibility:
        """Load station equipment and report outages without assuming missing records mean normal operation."""
        await self.stations.ensure_loaded()
        station = self.stations.get(station_id)
        if station is None:
            raise APIError(404, "Station not found")
        result = await self.repository.get_station_accessibility(station_id)
        return result.model_copy(
            update={
                "accessible": (
                    True
                    if station.ada_status == "full"
                    else False if station.ada_status == "none" else None
                )
            }
        )
