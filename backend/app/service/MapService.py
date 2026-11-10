from backend.app.models import MapNetwork
from backend.app.repository.MapRepository import MapRepository


class MapService:
    def __init__(self, repository: MapRepository):
        """Store the dependencies and initialize the state required by this component."""
        self.repository = repository

    async def get_map_network(self) -> MapNetwork:
        """Return the static subway line geometry used by the map."""
        return await self.repository.get_network()
