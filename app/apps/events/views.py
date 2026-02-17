from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.families.services import parse_uuid_or_none

from .forms import EventForm
from .services import (
    create_event_for_baby,
    delete_event,
    event_queryset_for_user,
    require_baby_access,
    require_event_access,
    update_event,
)


def _safe_tz_name(raw: str | None, fallback: str = "UTC") -> str:
    candidate = raw or fallback
    try:
        ZoneInfo(candidate)
        return candidate
    except Exception:
        return fallback


def _safe_int(value: str | None, fallback: int) -> int:
    try:
        return int(value) if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


@login_required
@require_GET
def timeline_view(request):
    queryset = event_queryset_for_user(request.user)
    baby_uuid = parse_uuid_or_none(request.GET.get("baby"))
    event_type = request.GET.get("type")

    if baby_uuid:
        queryset = queryset.filter(baby_id=baby_uuid)

    if event_type:
        queryset = queryset.filter(event_type=event_type)

    paginator = Paginator(queryset, 25)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "events/timeline.html",
        {
            "page": page,
            "event_types": [choice[0] for choice in page.object_list.model.EventType.choices],
            "active_event_type": event_type,
            "active_baby_id": str(baby_uuid) if baby_uuid else "",
        },
    )


@login_required
@require_GET
def calendar_view(request):
    tz_name = _safe_tz_name(request.GET.get("timezone") or request.GET.get("tz"), fallback="UTC")
    year = _safe_int(request.GET.get("year"), timezone.localdate().year)
    month = _safe_int(request.GET.get("month"), timezone.localdate().month)
    if month < 1 or month > 12:
        month = timezone.localdate().month

    queryset = event_queryset_for_user(request.user)
    baby_uuid = parse_uuid_or_none(request.GET.get("baby"))
    if baby_uuid:
        queryset = queryset.filter(baby_id=baby_uuid)

    _, month_days = calendar.monthrange(year, month)
    start_local = datetime(year, month, 1, tzinfo=ZoneInfo(tz_name))
    end_local = datetime(year, month, month_days, 23, 59, tzinfo=ZoneInfo(tz_name))
    start_utc = start_local.astimezone(UTC)
    end_utc = end_local.astimezone(UTC)

    events = queryset.filter(occurred_at_utc__gte=start_utc, occurred_at_utc__lte=end_utc)
    grouped = defaultdict(list)
    for event in events:
        local_day = event.occurred_at_utc.astimezone(ZoneInfo(tz_name)).date()
        grouped[local_day].append(event)

    day_rows = []
    for day in range(1, month_days + 1):
        current_date = date(year, month, day)
        day_rows.append({"date": current_date, "events": grouped.get(current_date, [])})

    return render(
        request,
        "events/calendar.html",
        {
            "day_rows": day_rows,
            "year": year,
            "month": month,
            "timezone": tz_name,
            "active_baby_id": str(baby_uuid) if baby_uuid else "",
        },
    )


@login_required
@require_GET
def event_new_view(request, baby_id):
    baby = require_baby_access(request.user, baby_id)
    timezone_name = _safe_tz_name(request.GET.get("timezone"), fallback=baby.timezone)
    form = EventForm(initial=EventForm.initial_for_new(timezone_name))
    return render(
        request,
        "events/form.html",
        {
            "form": form,
            "baby": baby,
            "mode": "create",
        },
    )


@login_required
@require_POST
def event_create_view(request, baby_id):
    baby = require_baby_access(request.user, baby_id)
    form = EventForm(request.POST)

    if form.is_valid():
        try:
            create_event_for_baby(request.user, baby, form.to_payload())
            messages.success(request, "Event logged.")
            return redirect("timeline")
        except ValidationError as exc:
            form.add_error(None, str(exc))

    return render(
        request,
        "events/form.html",
        {
            "form": form,
            "baby": baby,
            "mode": "create",
        },
        status=400,
    )


@login_required
@require_GET
def event_edit_view(request, event_id):
    event = require_event_access(request.user, event_id)
    timezone_name = _safe_tz_name(request.GET.get("timezone"), fallback=event.timezone)
    form = EventForm(initial=EventForm.initial_for_event(event, timezone_name))

    return render(
        request,
        "events/form.html",
        {
            "form": form,
            "event": event,
            "baby": event.baby,
            "mode": "edit",
        },
    )


@login_required
@require_POST
def event_update_view(request, event_id):
    event = require_event_access(request.user, event_id)
    form = EventForm(request.POST)

    if form.is_valid():
        try:
            update_event(request.user, event, form.to_payload())
            messages.success(request, "Event updated.")
            return redirect("timeline")
        except ValidationError as exc:
            form.add_error(None, str(exc))

    return render(
        request,
        "events/form.html",
        {
            "form": form,
            "event": event,
            "baby": event.baby,
            "mode": "edit",
        },
        status=400,
    )


@login_required
@require_http_methods(["POST"])
def event_delete_view(request, event_id):
    event = require_event_access(request.user, event_id)
    delete_event(request.user, event)
    messages.success(request, "Event deleted.")
    return redirect("timeline")
