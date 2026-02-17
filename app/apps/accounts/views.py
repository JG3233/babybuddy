from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.common.security import key_ip, rate_limit
from apps.events.services import serialize_event
from apps.families.models import FamilyMembership

from .forms import UserRegistrationForm


@rate_limit(limit=30, window_seconds=900, key_func=key_ip, methods={"POST"})
def login_view(request: HttpRequest, *args, **kwargs):
    return auth_views.LoginView.as_view(
        template_name="accounts/login.html",
        redirect_authenticated_user=True,
    )(request, *args, **kwargs)


@rate_limit(limit=20, window_seconds=3600, key_func=key_ip, methods={"POST"})
@require_http_methods(["GET", "POST"])
def register_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to BabyBuddy.")
            return redirect("dashboard")
    else:
        form = UserRegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
@require_GET
def account_export_view(request: HttpRequest) -> JsonResponse:
    memberships = FamilyMembership.objects.select_related("family", "user").filter(user=request.user)
    family_ids = [membership.family_id for membership in memberships]
    from apps.events.models import Event

    events = Event.objects.filter(family_id__in=family_ids).select_related("baby", "family")
    data = {
        "user": {
            "id": request.user.id,
            "username": request.user.get_username(),
            "email": request.user.email,
        },
        "families": [
            {
                "id": str(membership.family.id),
                "name": membership.family.name,
                "role": membership.role,
            }
            for membership in memberships
        ],
        "events": [serialize_event(event) for event in events],
    }
    return JsonResponse(data)


@login_required
@require_POST
def account_delete_view(request: HttpRequest) -> JsonResponse:
    user = request.user
    user.is_active = False
    user.save(update_fields=["is_active"])
    return JsonResponse({"status": "ok"})
