from fastapi import APIRouter

from backend.app.controllers.HealthController import router as health_router
from backend.app.controllers.StationController import router as station_router
from backend.app.controllers.AlertController import router as alert_router
from backend.app.controllers.StatusController import router as status_router
from backend.app.controllers.MapController import router as map_router
from backend.app.controllers.TripController import router as trip_router
from backend.app.controllers.PlaceController import router as place_router
from backend.app.controllers.RerouteController import router as reroute_router
from backend.app.controllers.FavoriteController import router as favorite_router
from backend.app.controllers.NotificationController import router as notification_router

router = APIRouter()
router.include_router(health_router)
router.include_router(station_router)
router.include_router(alert_router)
router.include_router(status_router)
router.include_router(map_router)
router.include_router(trip_router)
router.include_router(place_router)
router.include_router(reroute_router)
router.include_router(favorite_router)
router.include_router(notification_router)
