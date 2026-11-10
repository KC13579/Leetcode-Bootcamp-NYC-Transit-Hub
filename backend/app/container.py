from dataclasses import dataclass

from backend.app.sources.mta.client import MTAClient
from backend.app.sources.google.client import GoogleClient
from backend.app.sources.firebase.client import FirebaseClient
from backend.app.service.StationService import StationService
from backend.app.repository.StationRepository import StationRepository
from backend.app.service.ArrivalService import ArrivalService
from backend.app.repository.ArrivalRepository import ArrivalRepository
from backend.app.service.AlertService import AlertService
from backend.app.repository.AlertRepository import AlertRepository
from backend.app.service.StatusService import StatusService
from backend.app.service.MapService import MapService
from backend.app.repository.MapRepository import MapRepository
from backend.app.service.AccessibilityService import AccessibilityService
from backend.app.repository.AccessibilityRepository import AccessibilityRepository
from backend.app.service.PlaceService import PlaceService
from backend.app.repository.PlaceRepository import PlaceRepository
from backend.app.service.TripService import TripService
from backend.app.repository.TripRepository import TripRepository
from backend.app.service.RerouteService import RerouteService
from backend.app.repository.RerouteRepository import RerouteRepository
from backend.app.service.FavoriteService import FavoriteService
from backend.app.repository.FavoriteRepository import FavoriteRepository
from backend.app.service.NotificationService import NotificationService
from backend.app.repository.NotificationRepository import NotificationRepository


@dataclass
class Services:
    station: StationService
    arrival: ArrivalService
    alert: AlertService
    status: StatusService
    map: MapService
    accessibility: AccessibilityService
    place: PlaceService
    trip: TripService
    reroute: RerouteService
    favorite: FavoriteService
    notification: NotificationService


def build_services(
    client: MTAClient, google: GoogleClient, firebase: FirebaseClient
) -> Services:
    """Wire repositories and services around shared MTA, Google and Firebase clients."""
    stations = StationRepository(client)
    alerts = AlertService(AlertRepository(client), stations)
    accessibility = AccessibilityService(
        AccessibilityRepository(client, stations), stations
    )
    return Services(
        station=StationService(stations),
        arrival=ArrivalService(ArrivalRepository(client), stations),
        alert=alerts,
        status=StatusService(alerts),
        map=MapService(MapRepository(client)),
        accessibility=accessibility,
        place=PlaceService(PlaceRepository(google)),
        trip=TripService(TripRepository(google), stations, alerts),
        reroute=RerouteService(RerouteRepository(client), stations, alerts),
        favorite=FavoriteService(FavoriteRepository(firebase), stations),
        notification=NotificationService(
            NotificationRepository(firebase), stations, alerts, accessibility
        ),
    )
