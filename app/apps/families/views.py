from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .models import Family, FamilyMembership
from .services import parse_uuid_or_none


@login_required
@require_http_methods(["GET", "POST"])
def family_list_create_view(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if name:
            family = Family.objects.create(name=name, created_by=request.user)
            FamilyMembership.objects.create(
                family=family,
                user=request.user,
                role=FamilyMembership.Role.OWNER,
            )
            return redirect("families")

    memberships = FamilyMembership.objects.select_related("family").filter(user=request.user)
    return render(
        request,
        "families/list.html",
        {
            "memberships": memberships,
        },
    )


@login_required
@require_GET
def family_switch_view(request):
    family_uuid = parse_uuid_or_none(request.GET.get("family"))
    if family_uuid and FamilyMembership.objects.filter(user=request.user, family_id=family_uuid).exists():
        request.session["active_family_id"] = str(family_uuid)
    else:
        request.session.pop("active_family_id", None)
        messages.warning(request, "Please choose a valid family.")
    return redirect("dashboard")
