import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    allowed_origins: tuple[str, ...]
    mta_stations_url: str
    mta_feed_base_url: str


@lru_cache
def get_settings() -> Settings:
    origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
    return Settings(
        allowed_origins=tuple(item.strip() for item in origins.split(",") if item.strip()),
        mta_stations_url=os.getenv(
            "MTA_STATIONS_URL",
            "https://web.mta.info/developers/data/nyct/subway/Stations.csv",
        ),
        mta_feed_base_url=os.getenv(
            "MTA_FEED_BASE_URL",
            "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds",
        ).rstrip("/"),
    )
