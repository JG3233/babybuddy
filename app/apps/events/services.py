from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.babies.models import Baby
from apps.families.services import require_family_membership, require_family_write

from .models import DiaperEvent, Event, FeedingEvent, IdempotencyRecord, PumpingEvent, SleepEvent


@dataclass
class SummaryWindow:
    total: int
    by_type: dict[str, int]


def _normalize_occurrence(occurred_local: datetime, timezone_name: str) -> datetime:
    try:
        tz = ZoneInfo(timezone_name)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise ValidationError("Invalid timezone") from exc

    if occurred_local.tzinfo is None:
        occurred_local = occurred_local.replace(tzinfo=tz)
    else:
        occurred_local = occurred_local.astimezone(tz)
    return occurred_local.astimezone(UTC)


def _normalize_local_to_utc(value: datetime | None, timezone_name: str) -> datetime | None:
    if value is None:
        return None
    return _normalize_occurrence(value, timezone_name)


def _apply_detail(event: Event, details: dict) -> None:
    EventType = Event.EventType
    if event.event_type == EventType.FEEDING:
        FeedingEvent.objects.update_or_create(
            event=event,
            defaults={
                "method": details.get("method", ""),
                "amount_ml": details.get("amount_ml"),
                "side": details.get("side", ""),
                "duration_min": details.get("duration_min"),
            },
        )
    elif event.event_type == EventType.DIAPER:
        diaper_type = details.get("diaper_type")
        if not diaper_type:
            raise ValidationError("diaper_type is required for diaper events")
        DiaperEvent.objects.update_or_create(
            event=event,
            defaults={
                "diaper_type": diaper_type,
                "color": details.get("color", ""),
                "consistency": details.get("consistency", ""),
            },
        )
    elif event.event_type == EventType.SLEEP:
        SleepEvent.objects.update_or_create(
            event=event,
            defaults={
                "start_at_utc": event.occurred_at_utc,
                "end_at_utc": _normalize_local_to_utc(details.get("sleep_end_local"), event.timezone),
                "quality": details.get("quality", SleepEvent.Quality.UNKNOWN),
            },
        )
    elif event.event_type == EventType.PUMPING:
        if not details.get("amount_ml") and not details.get("duration_min"):
            raise ValidationError("Pumping events require amount_ml or duration_min")
        PumpingEvent.objects.update_or_create(
            event=event,
            defaults={
                "amount_ml": details.get("amount_ml"),
                "duration_min": details.get("duration_min"),
                "side": details.get("side", ""),
            },
        )


def _clear_other_details(event: Event) -> None:
    FeedingEvent.objects.filter(event=event).delete()
    DiaperEvent.objects.filter(event=event).delete()
    SleepEvent.objects.filter(event=event).delete()
    PumpingEvent.objects.filter(event=event).delete()


@transaction.atomic
def create_event_for_baby(user, baby: Baby, payload: dict, *, idempotency_key: str | None = None) -> Event:
    require_family_write(user, baby.family)
    occurred_at_utc = _normalize_occurrence(payload["occurred_at_local"], payload["timezone"])

    idempotency_record = None
    if idempotency_key:
        idempotency_record, created = IdempotencyRecord.objects.select_for_update().get_or_create(
            user=user,
            key=idempotency_key,
            defaults={
                "family": baby.family,
                "baby": baby,
            },
        )
        if not created and idempotency_record.event_id:
            return idempotency_record.event
        if idempotency_record.family_id != baby.family_id or idempotency_record.baby_id != baby.id:
            raise ValidationError("Idempotency key has already been used with a different resource.")

    event = Event.objects.create(
        family=baby.family,
        baby=baby,
        event_type=payload["event_type"],
        occurred_at_utc=occurred_at_utc,
        timezone=payload["timezone"],
        notes=payload.get("notes", ""),
        created_by=user,
    )
    _apply_detail(event, payload.get("details", {}))

    if idempotency_record and not idempotency_record.event_id:
        idempotency_record.event = event
        idempotency_record.save(update_fields=["event"])

    return event


@transaction.atomic
def update_event(user, event: Event, payload: dict) -> Event:
    require_family_write(user, event.family)

    event.event_type = payload["event_type"]
    event.occurred_at_utc = _normalize_occurrence(payload["occurred_at_local"], payload["timezone"])
    event.timezone = payload["timezone"]
    event.notes = payload.get("notes", "")
    event.updated_by = user
    event.save()

    _clear_other_details(event)
    _apply_detail(event, payload.get("details", {}))
    return event


@transaction.atomic
def delete_event(user, event: Event) -> None:
    require_family_write(user, event.family)
    event.delete()


def event_queryset_for_user(user):
    return (
        Event.objects.filter(family__memberships__user=user)
        .select_related(
            "baby",
            "family",
            "created_by",
            "feeding_detail",
            "diaper_detail",
            "sleep_detail",
            "pumping_detail",
        )
        .distinct()
    )


def require_event_access(user, event_id):
    event = event_queryset_for_user(user).filter(id=event_id).first()
    if event is None:
        raise PermissionDenied("Event not found.")
    require_family_membership(user, event.family)
    return event


def require_baby_access(user, baby_id):
    baby = Baby.objects.select_related("family").filter(id=baby_id).first()
    if baby is None:
        raise PermissionDenied("Baby not found.")
    require_family_membership(user, baby.family)
    return baby


def serialize_event(event: Event) -> dict:
    details: dict[str, object] = {}
    if hasattr(event, "feeding_detail"):
        details = {
            "method": event.feeding_detail.method,
            "amount_ml": event.feeding_detail.amount_ml,
            "side": event.feeding_detail.side,
            "duration_min": event.feeding_detail.duration_min,
        }
    elif hasattr(event, "diaper_detail"):
        details = {
            "diaper_type": event.diaper_detail.diaper_type,
            "color": event.diaper_detail.color,
            "consistency": event.diaper_detail.consistency,
        }
    elif hasattr(event, "sleep_detail"):
        details = {
            "start_at_utc": event.sleep_detail.start_at_utc.isoformat(),
            "end_at_utc": event.sleep_detail.end_at_utc.isoformat() if event.sleep_detail.end_at_utc else None,
            "quality": event.sleep_detail.quality,
        }
    elif hasattr(event, "pumping_detail"):
        details = {
            "amount_ml": event.pumping_detail.amount_ml,
            "duration_min": event.pumping_detail.duration_min,
            "side": event.pumping_detail.side,
        }

    return {
        "id": str(event.id),
        "family_id": str(event.family_id),
        "baby_id": str(event.baby_id),
        "event_type": event.event_type,
        "occurred_at_utc": event.occurred_at_utc.isoformat(),
        "timezone": event.timezone,
        "notes": event.notes,
        "schema_version": event.schema_version,
        "created_by": event.created_by_id,
        "created_at": event.created_at.isoformat(),
        "updated_at": event.updated_at.isoformat(),
        "details": details,
    }


def summarize_baby_events(baby: Baby, start: datetime, end: datetime) -> SummaryWindow:
    aggregates = (
        Event.objects.filter(baby=baby, occurred_at_utc__gte=start, occurred_at_utc__lte=end)
        .values("event_type")
        .annotate(count=Count("id"))
    )
    by_type = {entry["event_type"]: entry["count"] for entry in aggregates}
    total = sum(by_type.values())
    return SummaryWindow(total=total, by_type=by_type)


def daily_summary(baby: Baby, local_day: date, timezone_name: str) -> SummaryWindow:
    tz = ZoneInfo(timezone_name)
    start_local = datetime.combine(local_day, time.min).replace(tzinfo=tz)
    end_local = datetime.combine(local_day, time.max).replace(tzinfo=tz)
    return summarize_baby_events(
        baby=baby,
        start=start_local.astimezone(UTC),
        end=end_local.astimezone(UTC),
    )


def range_summary(baby: Baby, start_day: date, end_day: date, timezone_name: str) -> SummaryWindow:
    tz = ZoneInfo(timezone_name)
    start_local = datetime.combine(start_day, time.min).replace(tzinfo=tz)
    end_local = datetime.combine(end_day, time.max).replace(tzinfo=tz)
    return summarize_baby_events(
        baby=baby,
        start=start_local.astimezone(UTC),
        end=end_local.astimezone(UTC),
    )


def recent_counts_for_family(family_id, hours: int = 24) -> dict[str, int]:
    cutoff = timezone.now() - timedelta(hours=hours)
    counts = (
        Event.objects.filter(family_id=family_id, occurred_at_utc__gte=cutoff)
        .values("event_type")
        .annotate(count=Count("id"))
    )
    return {row["event_type"]: row["count"] for row in counts}
