from django.urls import path

from . import views

urlpatterns = [
    path("", views.baby_list_create_view, name="babies"),
]
