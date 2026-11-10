from backend.app.models import MapNetwork
from backend.app.sources.mta.client import MTAClient
from backend.app.sources.mta.map_lines import parse_map_network


class MapRepository:
    def __init__(self, client: MTAClient):
        """Store the dependencies and initialize the state required by this component."""
        self.client = client
        self._network: MapNetwork | None = None

    async def get_network(self) -> MapNetwork:
        """Parse and cache a map network from the MTA static GTFS archive."""
        if self._network is None:
            self._network = parse_map_network(await self.client.get_static_gtfs())
        return self._network
