import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    allowed_origins: tuple[str, ...]
    mta_stations_url: str
    mta_feed_base_url: str
    mta_static_gtfs_url: str
    google_maps_api_key: str = ""
    firebase_project_id: str = ""
    firebase_credentials: str = ""
    notifications_enabled: bool = False
    notification_interval_seconds: int = 60
    feed_max_age_seconds: int = 180


@lru_cache
def get_settings() -> Settings:
    """Load backend environment settings without overriding process-level configuration."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
    return Settings(
        allowed_origins=tuple(
            item.strip() for item in origins.split(",") if item.strip()
        ),
        mta_stations_url=os.getenv(
            "MTA_STATIONS_URL",
            "https://web.mta.info/developers/data/nyct/subway/Stations.csv",
        ),
        mta_feed_base_url=os.getenv(
            "MTA_FEED_BASE_URL",
            "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds",
        ).rstrip("/"),
        mta_static_gtfs_url=os.getenv(
            "MTA_STATIC_GTFS_URL",
            "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip",
        ),
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", ""),
        firebase_project_id=os.getenv("FIREBASE_PROJECT_ID", ""),
        firebase_credentials=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
        notifications_enabled=os.getenv("NOTIFICATIONS_ENABLED", "false").lower()
        == "true",
        notification_interval_seconds=max(
            30, int(os.getenv("NOTIFICATION_INTERVAL_SECONDS", "60"))
        ),
        feed_max_age_seconds=max(30, int(os.getenv("FEED_MAX_AGE_SECONDS", "180"))),
    )
