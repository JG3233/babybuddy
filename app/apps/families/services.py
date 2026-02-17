from __future__ import annotations

import uuid

from django.core.exceptions import PermissionDenied

from .models import Family, FamilyMembership

ALLOWED_WRITE_ROLES = {
    FamilyMembership.Role.OWNER,
    FamilyMembership.Role.CAREGIVER,
}


def user_families(user):
    return Family.objects.filter(memberships__user=user).distinct()


def parse_uuid_or_none(value):
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def require_family_membership(user, family: Family) -> FamilyMembership:
    membership = FamilyMembership.objects.filter(user=user, family=family).first()
    if membership is None:
        raise PermissionDenied("You do not have access to this family.")
    return membership


def require_family_write(user, family: Family) -> FamilyMembership:
    membership = require_family_membership(user, family)
    if membership.role not in ALLOWED_WRITE_ROLES:
        raise PermissionDenied("You do not have permission to modify this family.")
    return membership
