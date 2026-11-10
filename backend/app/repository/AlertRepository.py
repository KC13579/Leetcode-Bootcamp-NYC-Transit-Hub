from datetime import UTC, datetime

from google.transit import gtfs_realtime_pb2
from google.protobuf.message import DecodeError

from backend.app.core.errors import APIError
from backend.app.sources.mta.alerts import MTAAlert, parse_active_alerts
from backend.app.sources.mta.client import MTAClient


class AlertRepository:
    def __init__(self, client: MTAClient):
        """Store the dependencies and initialize the state required by this component."""
        self.client = client
        self.updated_at: datetime | None = None

    async def find_active(
        self, at: datetime | None = None, window_end: datetime | None = None
    ) -> list[MTAAlert]:
        """Decode alerts overlapping the requested interval and retain the feed publication timestamp."""
        payload = await self.client.get_feed("camsys%2Fsubway-alerts")
        try:
            message = gtfs_realtime_pb2.FeedMessage()
            message.ParseFromString(payload)
            self.updated_at = (
                datetime.fromtimestamp(message.header.timestamp, UTC)
                if message.header.timestamp
                else None
            )
            return parse_active_alerts(payload, now=at, window_end=window_end)
        except DecodeError as exc:
            raise APIError(502, "MTA returned invalid alert data.") from exc
