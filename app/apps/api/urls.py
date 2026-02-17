from django.urls import path

from . import views

urlpatterns = [
    path("babies/<uuid:baby_id>/events", views.baby_events_view, name="api_baby_events"),
    path("events/<uuid:event_id>", views.event_detail_view, name="api_event_detail"),
    path("babies/<uuid:baby_id>/summary/daily", views.daily_summary_view, name="api_daily_summary"),
    path("babies/<uuid:baby_id>/summary/range", views.range_summary_view, name="api_range_summary"),
]
