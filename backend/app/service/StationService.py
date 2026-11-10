from backend.app.models import Station
from backend.app.repository.StationRepository import StationRepository


class StationService:
    def __init__(self, repository: StationRepository):
        """Store the dependencies and initialize the state required by this component."""
        self.repository = repository

    async def list_stations(self, query: str, limit: int) -> list[Station]:
        """Search canonical stations by name or line and limit the ordered results."""
        await self.repository.ensure_loaded()
        return self.repository.search(query, limit)

    async def get_station(self, station_id: str) -> Station | None:
        """Return the station identified by its canonical application ID."""
        await self.repository.ensure_loaded()
        return self.repository.get(station_id)
