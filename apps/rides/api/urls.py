from rest_framework.routers import SimpleRouter

from apps.rides.api.views import RideEventViewSet, RideViewSet


router = SimpleRouter()
router.register("rides", RideViewSet, basename="ride")
router.register("ride-events", RideEventViewSet, basename="ride-event")

urlpatterns = router.urls
