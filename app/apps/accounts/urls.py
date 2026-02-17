from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("export", views.account_export_view, name="account_export"),
    path("delete", views.account_delete_view, name="account_delete"),
]
