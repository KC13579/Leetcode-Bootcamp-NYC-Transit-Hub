from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.errors import APIError
from backend.app.service.StationService import StationService
from backend.app.service.ArrivalService import ArrivalService
from backend.app.service.AlertService import AlertService
from backend.app.service.StatusService import StatusService
from backend.app.service.MapService import MapService
from backend.app.service.AccessibilityService import AccessibilityService
from backend.app.service.PlaceService import PlaceService
from backend.app.service.TripService import TripService
from backend.app.service.RerouteService import RerouteService
from backend.app.service.FavoriteService import FavoriteService
from backend.app.service.NotificationService import NotificationService


def get_station_service(request: Request) -> StationService:
    """Return the shared station service for this request."""
    return request.app.state.services.station


StationDependency = Annotated[StationService, Depends(get_station_service)]


def get_arrival_service(request: Request) -> ArrivalService:
    """Return the shared arrival service for this request."""
    return request.app.state.services.arrival


ArrivalDependency = Annotated[ArrivalService, Depends(get_arrival_service)]


def get_alert_service(request: Request) -> AlertService:
    """Return the shared alert service for this request."""
    return request.app.state.services.alert


AlertDependency = Annotated[AlertService, Depends(get_alert_service)]


def get_status_service(request: Request) -> StatusService:
    """Return the shared status service for this request."""
    return request.app.state.services.status


StatusDependency = Annotated[StatusService, Depends(get_status_service)]


def get_map_service(request: Request) -> MapService:
    """Return the shared map service for this request."""
    return request.app.state.services.map


MapDependency = Annotated[MapService, Depends(get_map_service)]


def get_accessibility_service(request: Request) -> AccessibilityService:
    """Return the shared accessibility service for this request."""
    return request.app.state.services.accessibility


AccessibilityDependency = Annotated[
    AccessibilityService, Depends(get_accessibility_service)
]


def get_place_service(request: Request) -> PlaceService:
    """Return the shared place service for this request."""
    return request.app.state.services.place


PlaceDependency = Annotated[PlaceService, Depends(get_place_service)]


def get_trip_service(request: Request) -> TripService:
    """Return the shared trip service for this request."""
    return request.app.state.services.trip


TripDependency = Annotated[TripService, Depends(get_trip_service)]


def get_reroute_service(request: Request) -> RerouteService:
    """Return the shared reroute service for this request."""
    return request.app.state.services.reroute


RerouteDependency = Annotated[RerouteService, Depends(get_reroute_service)]


def get_favorite_service(request: Request) -> FavoriteService:
    """Return the shared favorite service for this request."""
    return request.app.state.services.favorite


FavoriteDependency = Annotated[FavoriteService, Depends(get_favorite_service)]


def get_notification_service(request: Request) -> NotificationService:
    """Return the shared notification service for this request."""
    return request.app.state.services.notification


NotificationDependency = Annotated[
    NotificationService, Depends(get_notification_service)
]


bearer = HTTPBearer(auto_error=False, scheme_name="FirebaseIDToken")


async def require_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    """Verify the Firebase Bearer token and return its trusted user ID."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise APIError(401, "A Firebase Bearer ID token is required.")
    return await request.app.state.firebase.verify_token(credentials.credentials)


CurrentUser = Annotated[str, Depends(require_current_user)]
