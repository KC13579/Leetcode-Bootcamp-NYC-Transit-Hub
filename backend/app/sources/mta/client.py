import asyncio
import json
import time
from dataclasses import dataclass

import httpx

from backend.app.config import Settings
from backend.app.core.errors import APIError


@dataclass
class _CacheEntry:
    value: bytes
    expires_at: float


class MTAClient:
    """Small async HTTP client with short-lived in-memory feed caching."""

    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ):
        """Store the dependencies and initialize the state required by this component."""
        self.settings = settings
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(15),
            follow_redirects=True,
            transport=transport,
            headers={"User-Agent": "NYC-Transit-Hub-Class-Project/0.1"},
        )
        self._cache: dict[str, _CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        """Close the shared HTTP client and release its network resources."""
        await self._client.aclose()

    async def get_stations_csv(self) -> str:
        """Download cached MTA station metadata as Unicode CSV text."""
        data = await self._get(self.settings.mta_stations_url, ttl_seconds=6 * 60 * 60)
        return data.decode("utf-8-sig")

    async def get_static_gtfs(self) -> bytes:
        """Download and cache the MTA static GTFS ZIP archive."""
        return await self._get(
            self.settings.mta_static_gtfs_url,
            ttl_seconds=6 * 60 * 60,
        )

    async def get_feed(self, feed_path: str) -> bytes:
        """Download a short-lived cached MTA real-time feed."""
        url = f"{self.settings.mta_feed_base_url}/{feed_path}"
        return await self._get(url, ttl_seconds=20)

    async def get_json_feed(self, feed_path: str, ttl_seconds: int = 20) -> list[dict]:
        """Download and validate an MTA equipment JSON feed."""
        payload = await self._get(
            f"{self.settings.mta_feed_base_url}/{feed_path}", ttl_seconds
        )
        try:
            rows = json.loads(payload)
            if not isinstance(rows, list) or not all(
                isinstance(row, dict) for row in rows
            ):
                raise ValueError("Expected a JSON array of objects")
            return rows
        except (ValueError, TypeError) as exc:
            raise APIError(502, "MTA returned invalid equipment data.") from exc

    async def _get(self, url: str, ttl_seconds: int) -> bytes:
        """Retrieve cached source bytes or fetch them under the shared download lock."""
        now = time.monotonic()
        cached = self._cache.get(url)
        if cached and cached.expires_at > now:
            return cached.value

        async with self._lock:
            cached = self._cache.get(url)
            if cached and cached.expires_at > time.monotonic():
                return cached.value
            response = await self._client.get(url)
            response.raise_for_status()
            value = response.content
            self._cache[url] = _CacheEntry(value, time.monotonic() + ttl_seconds)
            return value
