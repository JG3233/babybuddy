from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.families.services import parse_uuid_or_none, require_family_write, user_families

from .models import Baby


@login_required
@require_http_methods(["GET", "POST"])
def baby_list_create_view(request):
    families = user_families(request.user)
    family_uuid = parse_uuid_or_none(request.GET.get("family") or request.session.get("active_family_id"))
    selected_family = families.filter(id=family_uuid).first() if family_uuid else families.first()

    if request.method == "POST":
        family_uuid = parse_uuid_or_none(request.POST.get("family_id"))
        name = request.POST.get("name", "").strip()
        birth_date = request.POST.get("birth_date") or None
        timezone = request.POST.get("timezone", "UTC").strip() or "UTC"

        family = families.filter(id=family_uuid).first() if family_uuid else None
        if family and name:
            require_family_write(request.user, family)
            Baby.objects.create(
                family=family,
                name=name,
                birth_date=birth_date,
                timezone=timezone,
                created_by=request.user,
            )
            request.session["active_family_id"] = str(family.id)
            return redirect("babies")

    babies = Baby.objects.none()
    if selected_family:
        babies = Baby.objects.filter(family=selected_family)

    return render(
        request,
        "babies/list.html",
        {
            "families": families,
            "selected_family": selected_family,
            "babies": babies,
        },
    )
