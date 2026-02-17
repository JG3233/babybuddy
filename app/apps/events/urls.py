from django.urls import path

from . import views

urlpatterns = [
    path("timeline", views.timeline_view, name="timeline"),
    path("calendar", views.calendar_view, name="calendar"),
    path("babies/<uuid:baby_id>/events/new", views.event_new_view, name="event_new"),
    path("babies/<uuid:baby_id>/events", views.event_create_view, name="event_create"),
    path("events/<uuid:event_id>/edit", views.event_edit_view, name="event_edit"),
    path("events/<uuid:event_id>", views.event_update_view, name="event_update"),
    path("events/<uuid:event_id>/delete", views.event_delete_view, name="event_delete"),
]
