from django.contrib import admin

from .models import Baby


@admin.register(Baby)
class BabyAdmin(admin.ModelAdmin):
    list_display = ("name", "family", "birth_date", "timezone", "created_at")
    list_filter = ("timezone",)
    search_fields = ("name", "family__name")
