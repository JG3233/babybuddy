"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("families/", include("apps.families.urls")),
    path("babies/", include("apps.babies.urls")),
    path("api/v1/", include("apps.api.urls")),
    path("", include("apps.events.urls")),
    path("", include("apps.analytics.urls")),
]
