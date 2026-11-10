from datetime import UTC

from backend.app.models.planning import TripPlanRequest
from backend.app.sources.google.client import GoogleClient


class TripRepository:
    def __init__(self, client: GoogleClient):
        """Store the dependencies and initialize the state required by this component."""
        self.client = client

    async def compute_routes(self, request: TripPlanRequest) -> dict:
        """Compute transit alternatives using resolved locations and normalized provider responses."""
        body = {
            "origin": self._waypoint(request.origin),
            "destination": self._waypoint(request.destination),
            "travelMode": "TRANSIT",
            "computeAlternativeRoutes": True,
            "languageCode": "en-US",
        }
        if request.departure_time:
            body["departureTime"] = request.departure_time.astimezone(UTC).isoformat()
        if request.arrival_time:
            body["arrivalTime"] = request.arrival_time.astimezone(UTC).isoformat()
        return await self.client.request(
            "POST",
            "https://routes.googleapis.com/directions/v2:computeRoutes",
            fields="routes.duration,routes.polyline,routes.legs.steps,routes.legs.duration",
            json=body,
        )

    @staticmethod
    def _waypoint(location) -> dict:
        """Translate a resolved application location into a Google Routes waypoint."""
        if location.place_id:
            return {"placeId": location.place_id}
        return {
            "location": {
                "latLng": {
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                }
            }
        }
