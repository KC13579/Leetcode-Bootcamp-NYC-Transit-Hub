from datetime import UTC, datetime, timedelta
import math

from backend.app.core.constants import ROUTE_ALIASES
from backend.app.core.errors import APIError
from backend.app.models.planning import (
    LocationInput,
    TripImpact,
    TripImpactRequest,
    TripPlanRequest,
    TripPlanResponse,
    TripRoute,
    TripSegment,
)
from backend.app.repository.TripRepository import TripRepository
from backend.app.repository.StationRepository import StationRepository
from backend.app.service.AlertService import AlertService


class TripService:
    def __init__(
        self,
        repository: TripRepository,
        stations: StationRepository,
        alerts: AlertService,
    ):
        """Store the dependencies and initialize the state required by this component."""
        self.repository = repository
        self.stations = stations
        self.alerts = alerts

    async def compute_routes(self, request: TripPlanRequest) -> TripPlanResponse:
        """Compute transit alternatives using resolved locations and normalized provider responses."""
        when = request.departure_time or request.arrival_time
        if when:
            difference = when - datetime.now(UTC)
            if difference < timedelta(days=-7) or difference > timedelta(days=100):
                raise APIError(
                    422, "Transit time must be within the previous 7 or next 100 days."
                )
        # Resolve project station IDs before building Google-specific waypoints.
        await self.stations.ensure_loaded()
        origin = self._resolve_location(request.origin)
        destination = self._resolve_location(request.destination)
        if origin == destination:
            raise APIError(422, "Origin and destination must be different.")
        resolved = request.model_copy(
            update={"origin": origin, "destination": destination}
        )
        payload = await self.repository.compute_routes(resolved)
        try:
            return TripPlanResponse(
                routes=[self._normalize_route(row) for row in payload.get("routes", [])]
            )
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise APIError(
                502, "Google Maps returned incomplete transit route data."
            ) from exc

    def _resolve_location(self, location: LocationInput) -> LocationInput:
        """Resolve a canonical station ID to coordinates or retain a supplied place or coordinate pair."""
        if not location.station_id:
            return location
        station = self.stations.get(location.station_id)
        if station is None:
            raise APIError(404, "Station not found")
        return LocationInput(latitude=station.latitude, longitude=station.longitude)

    def _normalize_route(self, row: dict) -> TripRoute:
        """Convert Google walking and transit steps into the public route response."""
        segments = []
        for leg in row.get("legs", []):
            for step in leg.get("steps", []):
                details = step.get("transitDetails", {})
                line = details.get("transitLine", {})
                vehicle = line.get("vehicle", {}).get("type", "")
                walking = step.get("travelMode") == "WALK"
                mode = (
                    "walking"
                    if walking
                    else (
                        "bus"
                        if vehicle in {"BUS", "INTERCITY_BUS", "TROLLEYBUS"}
                        else "subway" if vehicle == "SUBWAY" else "rail"
                    )
                )
                raw_route = line.get("nameShort") or line.get("name")
                route = ROUTE_ALIASES.get(raw_route, raw_route) if raw_route else None
                stops = details.get("stopDetails", {})
                boarding = stops.get("departureStop", {})
                alighting = stops.get("arrivalStop", {})
                departure = self._time(stops.get("departureTime"))
                arrival = self._time(stops.get("arrivalTime"))
                duration = step.get("staticDuration") or step.get("duration")
                if duration is None and departure and arrival:
                    seconds = max(0, math.ceil((arrival - departure).total_seconds()))
                elif duration is not None:
                    seconds = self._seconds(duration)
                else:
                    raise ValueError("Missing step duration")
                segments.append(
                    TripSegment(
                        mode=mode,
                        duration_seconds=seconds,
                        route_id=None if walking else route,
                        departure_time=departure,
                        arrival_time=arrival,
                        direction=details.get("headsign"),
                        boarding_stop_name=boarding.get("name"),
                        alighting_stop_name=alighting.get("name"),
                        boarding_station_id=(
                            self.stations.match_stop(
                                boarding.get("name", ""),
                                boarding.get("location", {}),
                                route,
                            )
                            if mode == "subway"
                            else None
                        ),
                        alighting_station_id=(
                            self.stations.match_stop(
                                alighting.get("name", ""),
                                alighting.get("location", {}),
                                route,
                            )
                            if mode == "subway"
                            else None
                        ),
                        polyline=step.get("polyline", {}).get("encodedPolyline"),
                    )
                )
        if not segments:
            raise ValueError("Route has no steps")
        return TripRoute(
            duration_seconds=self._seconds(row["duration"]),
            transfer_count=max(0, sum(s.mode != "walking" for s in segments) - 1),
            segments=segments,
            polyline=row.get("polyline", {}).get("encodedPolyline"),
        )

    @staticmethod
    def _seconds(value: str) -> int:
        """Convert a finite nonnegative provider duration into whole seconds."""
        seconds = float(value.removesuffix("s"))
        if seconds < 0 or not math.isfinite(seconds):
            raise ValueError("Invalid duration")
        return math.ceil(seconds)

    @staticmethod
    def _time(value: str | None) -> datetime | None:
        """Parse a provider timestamp into a timezone-aware datetime when available."""
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None

    async def analyze_impacts(self, request: TripImpactRequest) -> list[TripImpact]:
        """Compare each transit segment with alerts by line, station, direction and overlapping times."""
        end = request.departure_time + timedelta(seconds=request.route.duration_seconds)
        alerts = await self.alerts.get_alerts(at=request.departure_time, window_end=end)
        impacts = []
        cursor = request.departure_time
        for index, segment in enumerate(request.route.segments):
            start = segment.departure_time or cursor
            finish = segment.arrival_time or start + timedelta(
                seconds=segment.duration_seconds
            )
            cursor = finish
            if segment.mode == "walking" or not segment.route_id:
                continue
            station_ids = {
                segment.boarding_station_id,
                segment.alighting_station_id,
            } - {None}
            for alert in alerts:
                if alert.routes and segment.route_id not in alert.routes:
                    continue
                if (
                    alert.starts_at
                    and alert.starts_at > finish
                    or alert.ends_at
                    and alert.ends_at <= start
                ):
                    continue
                # Human-readable Google headsigns are not GTFS direction IDs.
                if (
                    alert.direction_ids
                    and segment.direction in {"0", "1"}
                    and segment.direction not in alert.direction_ids
                ):
                    continue
                scope = (
                    "segment"
                    if station_ids & set(alert.station_ids)
                    else "line" if alert.scope == "line" else "unknown"
                )
                message = (
                    alert.title
                    if scope != "unknown"
                    else f"Possible impact on this line; affected intermediate stops are not confirmed: {alert.title}"
                )
                if alert.is_stale:
                    message = f"Unverified or stale alert: {message}"
                impacts.append(
                    TripImpact(
                        segment_index=index,
                        alert_ids=[alert.id],
                        description=message,
                        scope=scope,
                    )
                )
        return impacts
