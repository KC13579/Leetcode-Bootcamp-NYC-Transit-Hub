import httpx

from backend.app.config import Settings
from backend.app.core.errors import APIError


class GoogleClient:
    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ):
        """Store the dependencies and initialize the state required by this component."""
        self.settings = settings
        self.http = httpx.AsyncClient(timeout=20, transport=transport)

    async def close(self) -> None:
        """Close the shared HTTP client and release its network resources."""
        await self.http.aclose()

    async def request(self, method: str, url: str, *, fields: str, **kwargs) -> dict:
        """Call a Google API using server credentials and return sanitized provider errors."""
        if not self.settings.google_maps_api_key:
            raise APIError(
                503, "Google Maps is not configured. Set GOOGLE_MAPS_API_KEY."
            )
        try:
            response = await self.http.request(
                method,
                url,
                headers={
                    "X-Goog-Api-Key": self.settings.google_maps_api_key,
                    "X-Goog-FieldMask": fields,
                },
                **kwargs
            )
        except httpx.TimeoutException as exc:
            raise APIError(504, "The Google Maps request timed out.") from exc
        except httpx.HTTPError as exc:
            raise APIError(502, "Google Maps is temporarily unavailable.") from exc
        if response.status_code == 404:
            raise APIError(404, "Place not found.")
        if response.status_code == 429:
            raise APIError(503, "Google Maps quota is temporarily unavailable.")
        if response.status_code == 400:
            raise APIError(
                422,
                "Google Maps could not use the supplied location or transit parameters.",
            )
        if response.status_code >= 400:
            raise APIError(
                502,
                "Google Maps rejected the request. Check the server configuration and input.",
            )
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object")
            return data
        except ValueError as exc:
            raise APIError(502, "Google Maps returned an invalid response.") from exc
