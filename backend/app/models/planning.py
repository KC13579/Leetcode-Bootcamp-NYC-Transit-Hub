"""Request and response contracts for transit planning and user preferences."""

from datetime import datetime
from typing import Literal, Self

from pydantic import AwareDatetime, BaseModel, Field, model_validator

FavoriteKind = Literal["station", "route"]


class LocationInput(BaseModel):
    station_id: str | None = Field(default=None, min_length=1)
    place_id: str | None = Field(default=None, min_length=1)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_location(self) -> Self:
        """Require exactly one location representation and a complete coordinate pair."""
        coordinates = self.latitude is not None or self.longitude is not None
        if coordinates and (self.latitude is None or self.longitude is None):
            raise ValueError("Both latitude and longitude are required")
        if (
            sum((self.station_id is not None, self.place_id is not None, coordinates))
            != 1
        ):
            raise ValueError("Provide one station_id, place_id, or coordinate pair")
        return self


class TripPlanRequest(BaseModel):
    origin: LocationInput
    destination: LocationInput
    departure_time: AwareDatetime | None = None
    arrival_time: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_time(self) -> Self:
        """Reject requests that specify both arrival and departure times."""
        if self.departure_time is not None and self.arrival_time is not None:
            raise ValueError("Use departure_time or arrival_time, not both")
        return self


class TripSegment(BaseModel):
    mode: Literal["walking", "subway", "bus", "rail"]
    duration_seconds: int = Field(ge=0)
    departure_time: AwareDatetime | None = None
    arrival_time: AwareDatetime | None = None
    direction: str | None = None
    boarding_stop_name: str | None = None
    alighting_stop_name: str | None = None
    route_id: str | None = None
    boarding_station_id: str | None = None
    alighting_station_id: str | None = None
    polyline: str | None = None


class TripRoute(BaseModel):
    duration_seconds: int = Field(ge=0)
    transfer_count: int = Field(ge=0)
    segments: list[TripSegment]
    polyline: str | None = None


class TripPlanResponse(BaseModel):
    routes: list[TripRoute]


class PlaceSuggestion(BaseModel):
    place_id: str
    name: str
    address: str | None = None


class PlaceDetails(PlaceSuggestion):
    latitude: float
    longitude: float


class AccessibilityEquipment(BaseModel):
    equipment_id: str
    kind: Literal["elevator", "escalator"]
    status: Literal["operational", "out_of_service", "unknown"]
    location: str | None = None
    reason: str | None = None
    expected_restore_at: datetime | None = None
    outage_start: datetime | None = None
    upcoming: bool = False
    alternative_route: str | None = None


class StationAccessibility(BaseModel):
    station_id: str
    accessible: bool | None = None
    equipment: list[AccessibilityEquipment]
    updated_at: datetime | None = None
    equipment_status_complete: bool = False
    note: str | None = None


class ReroutePattern(BaseModel):
    route_id: str
    trip_id: str | None = None
    direction: str | None = None
    updated_at: datetime | None = None
    expected_station_ids: list[str] | None = None
    skipped_station_ids: list[str] | None = None
    added_station_ids: list[str] | None = None
    alert_ids: list[str]
    evidence_status: Literal["confirmed", "partial", "unknown"]


class Favorite(BaseModel):
    kind: FavoriteKind
    target_id: str


class SubscriptionSettings(BaseModel):
    enabled: bool = True


class Subscription(Favorite):
    enabled: bool


class TripImpactRequest(BaseModel):
    route: TripRoute
    departure_time: AwareDatetime


class TripImpact(BaseModel):
    segment_index: int = Field(ge=0)
    alert_ids: list[str]
    description: str
    scope: Literal["segment", "line", "unknown"] = "segment"


class DeviceRegistration(BaseModel):
    token: str = Field(min_length=10, max_length=4096)


class DeliverySummary(BaseModel):
    sent: int = 0
    failed: int = 0
    skipped: int = 0
