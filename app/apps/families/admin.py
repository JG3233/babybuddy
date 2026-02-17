from django.contrib import admin

from .models import Family, FamilyMembership


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "created_at")
    search_fields = ("name", "created_by__username")


@admin.register(FamilyMembership)
class FamilyMembershipAdmin(admin.ModelAdmin):
    list_display = ("family", "user", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("family__name", "user__username")
