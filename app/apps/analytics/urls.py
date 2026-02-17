from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("healthz", views.health_view, name="healthz"),
    path("manifest.webmanifest", views.manifest_view, name="manifest"),
    path("service-worker.js", views.service_worker_view, name="service_worker"),
]
