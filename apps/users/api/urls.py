from rest_framework.routers import SimpleRouter

from apps.users.api.views import UserViewSet


router = SimpleRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = router.urls
