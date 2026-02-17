from __future__ import annotations

from apps.babies.models import Baby
from apps.families.models import FamilyMembership


def nav_state(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {
            "nav_has_family": False,
            "nav_has_baby": False,
        }

    family_ids = FamilyMembership.objects.filter(user=user).values_list("family_id", flat=True)
    has_family = bool(family_ids)
    has_baby = Baby.objects.filter(family_id__in=family_ids).exists() if has_family else False

    return {
        "nav_has_family": has_family,
        "nav_has_baby": has_baby,
    }
