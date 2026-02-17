from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Family(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="families_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class FamilyMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        CAREGIVER = "caregiver", "Caregiver"
        VIEWER = "viewer", "Viewer"

    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="family_memberships",
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.CAREGIVER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["family", "user"],
                name="uniq_family_membership",
            )
        ]
        indexes = [models.Index(fields=["user", "role"])]

    def __str__(self) -> str:
        return f"{self.user} -> {self.family} ({self.role})"
