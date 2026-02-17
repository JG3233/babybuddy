from django.contrib import admin

from .models import DiaperEvent, Event, FeedingEvent, IdempotencyRecord, PumpingEvent, SleepEvent


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "baby", "family", "occurred_at_utc", "created_by")
    list_filter = ("event_type", "timezone")
    search_fields = ("baby__name", "family__name", "notes")


@admin.register(FeedingEvent)
class FeedingEventAdmin(admin.ModelAdmin):
    list_display = ("event", "method", "amount_ml", "side", "duration_min")


@admin.register(DiaperEvent)
class DiaperEventAdmin(admin.ModelAdmin):
    list_display = ("event", "diaper_type", "color", "consistency")


@admin.register(SleepEvent)
class SleepEventAdmin(admin.ModelAdmin):
    list_display = ("event", "start_at_utc", "end_at_utc", "quality")


@admin.register(PumpingEvent)
class PumpingEventAdmin(admin.ModelAdmin):
    list_display = ("event", "amount_ml", "duration_min", "side")


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "key", "family", "baby", "event", "created_at")
    search_fields = ("user__username", "key")
