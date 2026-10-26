import asyncio
import time
from dataclasses import dataclass

import httpx

from app.config import Settings


@dataclass
class _CacheEntry:
    value: bytes
    expires_at: float


class MTAClient:
    """Small async HTTP client with short-lived in-memory feed caching."""

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
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
        await self._client.aclose()

    async def get_stations_csv(self) -> str:
        data = await self._get(self.settings.mta_stations_url, ttl_seconds=6 * 60 * 60)
        return data.decode("utf-8-sig")

    async def get_feed(self, feed_path: str) -> bytes:
        url = f"{self.settings.mta_feed_base_url}/{feed_path}"
        return await self._get(url, ttl_seconds=20)

    async def _get(self, url: str, ttl_seconds: int) -> bytes:
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
