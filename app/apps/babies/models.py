from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.families.models import Family


class Baby(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="babies")
    name = models.CharField(max_length=120)
    birth_date = models.DateField(blank=True, null=True)
    timezone = models.CharField(max_length=64, default="UTC")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="babies_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["family", "name", "birth_date"],
                name="uniq_family_baby_name_birthdate",
            )
        ]

    def __str__(self) -> str:
        return self.name
