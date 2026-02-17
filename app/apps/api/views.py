from __future__ import annotations

import json
import logging
from datetime import date
from zoneinfo import ZoneInfo

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from apps.common.security import key_user_or_ip, rate_limit
from apps.events.services import (
    create_event_for_baby,
    daily_summary,
    delete_event,
    event_queryset_for_user,
    range_summary,
    require_baby_access,
    require_event_access,
    serialize_event,
    update_event,
)

logger = logging.getLogger(__name__)

# Pagination constants
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


def _paginate_queryset(request: HttpRequest, queryset, default_size: int = DEFAULT_PAGE_SIZE):
    """
    Paginate a queryset with cursor-based pagination.

    Query params:
    - limit: Number of items per page (default 25, max 100)
    - offset: Number of items to skip (default 0)

    Returns tuple: (paginated_queryset, pagination_metadata)
    """
    try:
        limit = int(request.GET.get("limit", default_size))
        limit = min(max(1, limit), MAX_PAGE_SIZE)  # Clamp between 1 and MAX_PAGE_SIZE
    except (ValueError, TypeError):
        limit = default_size

    try:
        offset = int(request.GET.get("offset", 0))
        offset = max(0, offset)  # Can't be negative
    except (ValueError, TypeError):
        offset = 0

    total_count = queryset.count()
    paginated = queryset[offset : offset + limit]

    metadata = {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total_count,
    }

    return paginated, metadata


def _load_json_body(request: HttpRequest) -> dict:
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


def _payload_from_json(body: dict) -> dict:
    from django.utils.dateparse import parse_datetime

    occurred_raw = body.get("occurred_at_local") or body.get("occurred_at")
    occurred_at_local = parse_datetime(occurred_raw) if isinstance(occurred_raw, str) else None
    details = body.get("details") if isinstance(body.get("details"), dict) else {}
    return {
        "event_type": body.get("event_type"),
        "occurred_at_local": occurred_at_local,
        "timezone": body.get("timezone", "UTC"),
        "notes": body.get("notes", ""),
        "details": details,
    }


def _safe_timezone_name_or_none(value: str | None) -> str | None:
    if not value:
        return None
    try:
        ZoneInfo(value)
        return value
    except Exception:
        return None


@login_required
@rate_limit(limit=240, window_seconds=60, key_func=key_user_or_ip, methods={"GET"})
@rate_limit(limit=60, window_seconds=60, key_func=key_user_or_ip, methods={"POST"})
@require_http_methods(["GET", "POST"])
def baby_events_view(request: HttpRequest, baby_id):
    try:
        baby = require_baby_access(request.user, baby_id)
    except PermissionDenied:
        return _json_error("Not found or not authorized.", status=403)

    if request.method == "GET":
        queryset = event_queryset_for_user(request.user).filter(baby=baby)
        event_type = request.GET.get("type")
        from_raw = request.GET.get("from")
        to_raw = request.GET.get("to")

        if event_type:
            queryset = queryset.filter(event_type=event_type)

        from django.utils.dateparse import parse_datetime

        if from_raw:
            parsed_from = parse_datetime(from_raw)
            if parsed_from:
                queryset = queryset.filter(occurred_at_utc__gte=parsed_from)
        if to_raw:
            parsed_to = parse_datetime(to_raw)
            if parsed_to:
                queryset = queryset.filter(occurred_at_utc__lte=parsed_to)

        # Apply pagination (default 25, max 100)
        paginated_events, pagination = _paginate_queryset(request, queryset)

        return JsonResponse(
            {
                "results": [serialize_event(event) for event in paginated_events],
                "pagination": pagination,
            }
        )

    body = _load_json_body(request)
    payload = _payload_from_json(body)

    if not payload.get("event_type") or not payload.get("occurred_at_local"):
        return _json_error("event_type and occurred_at_local are required")

    idempotency_key = request.headers.get("Idempotency-Key") or body.get("idempotency_key")

    try:
        event = create_event_for_baby(
            request.user,
            baby,
            payload,
            idempotency_key=idempotency_key,
        )
    except ValidationError:
        return _json_error("Invalid request payload.")
    except PermissionDenied:
        return _json_error("Not authorized.", status=403)
    except Exception:
        logger.exception("Unexpected error creating event")
        return _json_error("Unable to process request.", status=500)
    return JsonResponse(serialize_event(event), status=201)


@login_required
@rate_limit(limit=60, window_seconds=60, key_func=key_user_or_ip, methods={"PATCH", "DELETE"})
@require_http_methods(["PATCH", "DELETE"])
def event_detail_view(request: HttpRequest, event_id):
    try:
        event = require_event_access(request.user, event_id)
    except PermissionDenied:
        return _json_error("Not found or not authorized.", status=403)

    if request.method == "DELETE":
        try:
            delete_event(request.user, event)
        except PermissionDenied:
            return _json_error("Not authorized.", status=403)
        return HttpResponse(status=204)

    body = _load_json_body(request)
    payload = _payload_from_json(body)

    if not payload.get("event_type") or not payload.get("occurred_at_local"):
        return _json_error("event_type and occurred_at_local are required")

    try:
        updated = update_event(request.user, event, payload)
    except ValidationError:
        return _json_error("Invalid request payload.")
    except PermissionDenied:
        return _json_error("Not authorized.", status=403)
    except Exception:
        logger.exception("Unexpected error updating event")
        return _json_error("Unable to process request.", status=500)
    return JsonResponse(serialize_event(updated), status=200)


@login_required
@rate_limit(limit=240, window_seconds=60, key_func=key_user_or_ip, methods={"GET"})
@require_http_methods(["GET"])
def daily_summary_view(request: HttpRequest, baby_id):
    try:
        baby = require_baby_access(request.user, baby_id)
    except PermissionDenied:
        return _json_error("Not found or not authorized.", status=403)
    day_raw = request.GET.get("date")
    timezone_name = request.GET.get("timezone", baby.timezone)
    timezone_name = _safe_timezone_name_or_none(timezone_name)
    if not timezone_name:
        return _json_error("Invalid timezone.")
    if not day_raw:
        return _json_error("date query param is required")

    try:
        day = date.fromisoformat(day_raw)
    except ValueError:
        return _json_error("date must be YYYY-MM-DD")

    try:
        summary = daily_summary(baby, day, timezone_name)
    except Exception:
        logger.exception("Unexpected error computing daily summary")
        return _json_error("Unable to process request.", status=500)
    return JsonResponse(
        {
            "date": day.isoformat(),
            "timezone": timezone_name,
            "total": summary.total,
            "by_type": summary.by_type,
        }
    )


@login_required
@rate_limit(limit=240, window_seconds=60, key_func=key_user_or_ip, methods={"GET"})
@require_http_methods(["GET"])
def range_summary_view(request: HttpRequest, baby_id):
    try:
        baby = require_baby_access(request.user, baby_id)
    except PermissionDenied:
        return _json_error("Not found or not authorized.", status=403)
    from_raw = request.GET.get("from")
    to_raw = request.GET.get("to")
    timezone_name = request.GET.get("timezone", baby.timezone)
    timezone_name = _safe_timezone_name_or_none(timezone_name)
    if not timezone_name:
        return _json_error("Invalid timezone.")

    if not from_raw or not to_raw:
        return _json_error("from and to query params are required")

    try:
        start = date.fromisoformat(from_raw)
        end = date.fromisoformat(to_raw)
    except ValueError:
        return _json_error("from and to must be YYYY-MM-DD")

    if end < start:
        return _json_error("to must be >= from")

    try:
        summary = range_summary(baby, start, end, timezone_name)
    except Exception:
        logger.exception("Unexpected error computing range summary")
        return _json_error("Unable to process request.", status=500)
    return JsonResponse(
        {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "timezone": timezone_name,
            "total": summary.total,
            "by_type": summary.by_type,
        }
    )
