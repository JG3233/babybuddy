from django.urls import path

from . import views

urlpatterns = [
    path("", views.family_list_create_view, name="families"),
    path("switch", views.family_switch_view, name="family_switch"),
]
