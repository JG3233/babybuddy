from __future__ import annotations

from django import forms
from django.utils import timezone

from .models import DiaperEvent, Event, FeedingEvent, PumpingEvent, SleepEvent

DATETIME_INPUT_FORMAT = "%Y-%m-%dT%H:%M"


class EventForm(forms.Form):
    event_type = forms.ChoiceField(choices=Event.EventType.choices)
    occurred_at_local = forms.DateTimeField(
        input_formats=[DATETIME_INPUT_FORMAT],
        widget=forms.DateTimeInput(format=DATETIME_INPUT_FORMAT, attrs={"type": "datetime-local"}),
    )
    timezone = forms.CharField(max_length=64, initial="UTC")
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    feeding_method = forms.ChoiceField(choices=FeedingEvent.Method.choices, required=False)
    feeding_amount_ml = forms.IntegerField(min_value=0, required=False)
    feeding_side = forms.ChoiceField(choices=FeedingEvent.Side.choices, required=False)
    feeding_duration_min = forms.IntegerField(min_value=0, required=False)

    diaper_type = forms.ChoiceField(choices=DiaperEvent.DiaperType.choices, required=False)
    diaper_color = forms.CharField(max_length=64, required=False)
    diaper_consistency = forms.CharField(max_length=64, required=False)

    sleep_end_local = forms.DateTimeField(
        required=False,
        input_formats=[DATETIME_INPUT_FORMAT],
        widget=forms.DateTimeInput(format=DATETIME_INPUT_FORMAT, attrs={"type": "datetime-local"}),
    )
    sleep_quality = forms.ChoiceField(choices=SleepEvent.Quality.choices, required=False)

    pumping_amount_ml = forms.IntegerField(min_value=0, required=False)
    pumping_duration_min = forms.IntegerField(min_value=0, required=False)
    pumping_side = forms.ChoiceField(choices=PumpingEvent.Side.choices, required=False)

    def clean(self):
        cleaned = super().clean()
        event_type = cleaned.get("event_type")

        if event_type == Event.EventType.DIAPER and not cleaned.get("diaper_type"):
            self.add_error("diaper_type", "Diaper type is required for diaper events.")

        if event_type == Event.EventType.SLEEP:
            occurred = cleaned.get("occurred_at_local")
            sleep_end = cleaned.get("sleep_end_local")
            if occurred and sleep_end and sleep_end < occurred:
                self.add_error("sleep_end_local", "Sleep end time must be after start time.")

        if event_type == Event.EventType.PUMPING:
            if not cleaned.get("pumping_amount_ml") and not cleaned.get("pumping_duration_min"):
                self.add_error(
                    "pumping_amount_ml",
                    "Provide amount or duration for pumping events.",
                )

        return cleaned

    def to_payload(self) -> dict:
        cleaned = self.cleaned_data
        event_type = cleaned["event_type"]

        details: dict[str, object] = {}
        if event_type == Event.EventType.FEEDING:
            details = {
                "method": cleaned.get("feeding_method") or "",
                "amount_ml": cleaned.get("feeding_amount_ml"),
                "side": cleaned.get("feeding_side") or "",
                "duration_min": cleaned.get("feeding_duration_min"),
            }
        elif event_type == Event.EventType.DIAPER:
            details = {
                "diaper_type": cleaned.get("diaper_type"),
                "color": cleaned.get("diaper_color") or "",
                "consistency": cleaned.get("diaper_consistency") or "",
            }
        elif event_type == Event.EventType.SLEEP:
            details = {
                "sleep_end_local": cleaned.get("sleep_end_local"),
                "quality": cleaned.get("sleep_quality") or SleepEvent.Quality.UNKNOWN,
            }
        elif event_type == Event.EventType.PUMPING:
            details = {
                "amount_ml": cleaned.get("pumping_amount_ml"),
                "duration_min": cleaned.get("pumping_duration_min"),
                "side": cleaned.get("pumping_side") or "",
            }

        return {
            "event_type": event_type,
            "occurred_at_local": cleaned["occurred_at_local"],
            "timezone": cleaned["timezone"],
            "notes": cleaned.get("notes") or "",
            "details": details,
        }

    @classmethod
    def initial_for_new(cls, timezone_name: str = "UTC") -> dict:
        now = timezone.localtime()
        return {
            "occurred_at_local": now.strftime(DATETIME_INPUT_FORMAT),
            "timezone": timezone_name,
            "event_type": Event.EventType.FEEDING,
        }

    @classmethod
    def initial_for_event(cls, event: Event, timezone_name: str) -> dict:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(timezone_name)
        initial = {
            "event_type": event.event_type,
            "occurred_at_local": event.occurred_at_utc.astimezone(tz).strftime(DATETIME_INPUT_FORMAT),
            "timezone": timezone_name,
            "notes": event.notes,
        }

        if hasattr(event, "feeding_detail"):
            detail = event.feeding_detail
            initial.update(
                {
                    "feeding_method": detail.method,
                    "feeding_amount_ml": detail.amount_ml,
                    "feeding_side": detail.side,
                    "feeding_duration_min": detail.duration_min,
                }
            )

        if hasattr(event, "diaper_detail"):
            detail = event.diaper_detail
            initial.update(
                {
                    "diaper_type": detail.diaper_type,
                    "diaper_color": detail.color,
                    "diaper_consistency": detail.consistency,
                }
            )

        if hasattr(event, "sleep_detail"):
            detail = event.sleep_detail
            initial.update(
                {
                    "sleep_quality": detail.quality,
                    "sleep_end_local": detail.end_at_utc.astimezone(tz).strftime(DATETIME_INPUT_FORMAT)
                    if detail.end_at_utc
                    else None,
                }
            )

        if hasattr(event, "pumping_detail"):
            detail = event.pumping_detail
            initial.update(
                {
                    "pumping_amount_ml": detail.amount_ml,
                    "pumping_duration_min": detail.duration_min,
                    "pumping_side": detail.side,
                }
            )

        return initial
