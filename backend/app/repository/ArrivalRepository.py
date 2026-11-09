import asyncio

from backend.app.sources.mta.client import MTAClient
from backend.app.sources.mta.realtime import (
    MTAArrival,
    feed_paths_for_routes,
    parse_arrivals,
)


class ArrivalRepository:
    def __init__(self, client: MTAClient):
        """Store the dependencies and initialize the state required by this component."""
        self.client = client

    async def find_by_routes(self, routes: list[str]) -> list[MTAArrival]:
        """Fetch and decode the real-time feeds needed for the supplied subway lines."""
        payloads = await asyncio.gather(
            *(self.client.get_feed(path) for path in feed_paths_for_routes(routes))
        )
        return [arrival for payload in payloads for arrival in parse_arrivals(payload)]
