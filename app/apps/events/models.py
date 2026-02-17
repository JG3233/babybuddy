from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.babies.models import Baby
from apps.families.models import Family


class Event(models.Model):
    class EventType(models.TextChoices):
        FEEDING = "feeding", "Feeding"
        DIAPER = "diaper", "Diaper"
        SLEEP = "sleep", "Sleep"
        PUMPING = "pumping", "Pumping"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="events")
    baby = models.ForeignKey(Baby, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=16, choices=EventType.choices)
    occurred_at_utc = models.DateTimeField()
    timezone = models.CharField(max_length=64)
    notes = models.TextField(blank=True)
    schema_version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="events_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="events_updated",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurred_at_utc", "-created_at"]
        indexes = [
            models.Index(fields=["family", "baby", "-occurred_at_utc"]),
            models.Index(fields=["event_type", "-occurred_at_utc"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} for {self.baby.name}"


class FeedingEvent(models.Model):
    class Method(models.TextChoices):
        BREAST = "breast", "Breast"
        BOTTLE = "bottle", "Bottle"
        FORMULA = "formula", "Formula"
        SOLIDS = "solids", "Solids"
        OTHER = "other", "Other"

    class Side(models.TextChoices):
        LEFT = "left", "Left"
        RIGHT = "right", "Right"
        BOTH = "both", "Both"

    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="feeding_detail")
    method = models.CharField(max_length=16, choices=Method.choices, blank=True)
    amount_ml = models.PositiveIntegerField(null=True, blank=True)
    side = models.CharField(max_length=8, choices=Side.choices, blank=True)
    duration_min = models.PositiveIntegerField(null=True, blank=True)


class DiaperEvent(models.Model):
    class DiaperType(models.TextChoices):
        WET = "wet", "Wet"
        DIRTY = "dirty", "Dirty"
        MIXED = "mixed", "Mixed"
        DRY = "dry", "Dry"

    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="diaper_detail")
    diaper_type = models.CharField(max_length=16, choices=DiaperType.choices)
    color = models.CharField(max_length=64, blank=True)
    consistency = models.CharField(max_length=64, blank=True)


class SleepEvent(models.Model):
    class Quality(models.TextChoices):
        GOOD = "good", "Good"
        OK = "ok", "OK"
        ROUGH = "rough", "Rough"
        UNKNOWN = "unknown", "Unknown"

    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="sleep_detail")
    start_at_utc = models.DateTimeField()
    end_at_utc = models.DateTimeField(null=True, blank=True)
    quality = models.CharField(max_length=16, choices=Quality.choices, default=Quality.UNKNOWN)


class PumpingEvent(models.Model):
    class Side(models.TextChoices):
        LEFT = "left", "Left"
        RIGHT = "right", "Right"
        BOTH = "both", "Both"

    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="pumping_detail")
    amount_ml = models.PositiveIntegerField(null=True, blank=True)
    duration_min = models.PositiveIntegerField(null=True, blank=True)
    side = models.CharField(max_length=8, choices=Side.choices, blank=True)


class IdempotencyRecord(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_idempotency_records",
    )
    key = models.CharField(max_length=128)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="idempotency_records")
    baby = models.ForeignKey(Baby, on_delete=models.CASCADE, related_name="idempotency_records")
    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
        related_name="idempotency_record",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "key"],
                name="uniq_user_idempotency_key",
            )
        ]
