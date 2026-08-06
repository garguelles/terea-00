from django.contrib import admin
from django.urls import include, path

from config.health import health_check


urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.users.api.urls")),
    path("api/v1/", include("apps.rides.api.urls")),
    path("api/v1/", include("apps.reporting.api.urls")),
]
