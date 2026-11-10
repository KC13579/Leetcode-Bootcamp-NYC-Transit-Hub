from datetime import datetime

from pydantic import BaseModel, Field


class StationSummary(BaseModel):
    id: str = Field(description="Canonical ID in the form mta-complex:<complex id>")
    name: str
    latitude: float
    longitude: float
    routes: list[str]


class Station(StationSummary):
    borough: str
    stop_ids: list[str]
    north_direction_label: str | None = None
    south_direction_label: str | None = None
    ada_status: str = "unknown"


class Arrival(BaseModel):
    route: str
    direction: str
    destination: str | None = None
    arrival_time: datetime
    minutes_away: int
    trip_id: str


class ServiceAlert(BaseModel):
    id: str
    title: str
    description: str | None = None
    routes: list[str]
    station_ids: list[str]
    effect: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    cause: str | None = None
    direction_ids: list[str] = Field(default_factory=list)
    disruption_type: str = "other"
    updated_at: datetime | None = None
    is_stale: bool = False
    scope: str = "line"


class ServiceStatus(BaseModel):
    route: str
    status: str
    alert_count: int
    alerts: list[ServiceAlert]
    updated_at: datetime | None = None
    data_status: str = "unknown"


class MapLine(BaseModel):
    id: str
    route: str
    color: str
    coordinates: list[tuple[float, float]]


class MapNetwork(BaseModel):
    lines: list[MapLine]
