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


class ServiceStatus(BaseModel):
    route: str
    status: str
    alert_count: int
    alerts: list[ServiceAlert]
