from urllib.parse import quote

from backend.app.core.errors import APIError
from backend.app.models.planning import PlaceDetails, PlaceSuggestion
from backend.app.sources.google.client import GoogleClient


class PlaceRepository:
    def __init__(self, client: GoogleClient):
        """Store the dependencies and initialize the state required by this component."""
        self.client = client

    async def autocomplete(
        self, query: str, session_token: str | None
    ) -> list[PlaceSuggestion]:
        """Return place suggestions for a validated search query and optional billing session."""
        body = {
            "input": query,
            "includedRegionCodes": ["us"],
            "languageCode": "en",
            "locationBias": {
                "circle": {
                    "center": {"latitude": 40.754, "longitude": -73.984},
                    "radius": 50000,
                }
            },
        }
        if session_token:
            body["sessionToken"] = session_token
        data = await self.client.request(
            "POST",
            "https://places.googleapis.com/v1/places:autocomplete",
            fields="suggestions.placePrediction.placeId,suggestions.placePrediction.text,suggestions.placePrediction.structuredFormat",
            json=body,
        )
        try:
            return [
                PlaceSuggestion(
                    place_id=p["placeId"],
                    name=p.get("structuredFormat", {}).get("mainText", {}).get("text")
                    or p.get("text", {}).get("text", ""),
                    address=p.get("structuredFormat", {})
                    .get("secondaryText", {})
                    .get("text"),
                )
                for item in data.get("suggestions", [])
                if (p := item.get("placePrediction")) and p.get("placeId")
            ]
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            raise APIError(
                502, "Google Maps returned invalid place suggestions."
            ) from exc

    async def get_place(self, place_id: str, session_token: str | None) -> PlaceDetails:
        """Return display information and usable coordinates for a Google place ID."""
        params = {"languageCode": "en"}
        if session_token:
            params["sessionToken"] = session_token
        data = await self.client.request(
            "GET",
            f"https://places.googleapis.com/v1/places/{quote(place_id, safe='')}",
            fields="id,displayName,formattedAddress,location",
            params=params,
        )
        try:
            location = data.get("location", {})
            if "latitude" not in location or "longitude" not in location:
                raise APIError(502, "The place has no usable coordinates.")
            return PlaceDetails(
                place_id=data.get("id", place_id),
                name=data.get("displayName", {}).get("text", ""),
                address=data.get("formattedAddress"),
                latitude=location["latitude"],
                longitude=location["longitude"],
            )
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            raise APIError(502, "Google Maps returned invalid place details.") from exc
