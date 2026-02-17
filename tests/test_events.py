from __future__ import annotations

from datetime import datetime

from apps.babies.models import Baby
from apps.events.models import DiaperEvent, Event, IdempotencyRecord
from apps.events.services import create_event_for_baby
from apps.families.models import Family, FamilyMembership
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone


class EventServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("caregiver", "caregiver@example.com", "pass1234")
        self.family = Family.objects.create(name="A Family", created_by=self.user)
        FamilyMembership.objects.create(
            family=self.family,
            user=self.user,
            role=FamilyMembership.Role.OWNER,
        )
        self.baby = Baby.objects.create(
            family=self.family,
            name="Ava",
            timezone="UTC",
            created_by=self.user,
        )

    def test_create_diaper_event_creates_core_and_detail(self):
        payload = {
            "event_type": Event.EventType.DIAPER,
            "occurred_at_local": datetime(2026, 2, 15, 10, 30),
            "timezone": "UTC",
            "notes": "Quick change",
            "details": {"diaper_type": "wet", "color": "yellow", "consistency": "thin"},
        }

        event = create_event_for_baby(self.user, self.baby, payload)

        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(event.family, self.family)
        self.assertEqual(event.baby, self.baby)
        self.assertEqual(event.event_type, Event.EventType.DIAPER)

        detail = DiaperEvent.objects.get(event=event)
        self.assertEqual(detail.diaper_type, "wet")
        self.assertEqual(detail.color, "yellow")


class EventPermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", "owner@example.com", "pass1234")
        self.other = User.objects.create_user("other", "other@example.com", "pass1234")

        self.family = Family.objects.create(name="Family One", created_by=self.owner)
        FamilyMembership.objects.create(
            family=self.family,
            user=self.owner,
            role=FamilyMembership.Role.OWNER,
        )

        self.other_family = Family.objects.create(name="Family Two", created_by=self.other)
        FamilyMembership.objects.create(
            family=self.other_family,
            user=self.other,
            role=FamilyMembership.Role.OWNER,
        )

        self.baby = Baby.objects.create(
            family=self.family,
            name="June",
            timezone="UTC",
            created_by=self.owner,
        )

        self.client = Client()

    def test_user_cannot_query_other_family_baby_events(self):
        self.client.login(username="other", password="pass1234")
        response = self.client.get(reverse("api_baby_events", kwargs={"baby_id": self.baby.id}))
        self.assertEqual(response.status_code, 403)


class SummaryApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("summary", "summary@example.com", "pass1234")

        self.family = Family.objects.create(name="Summary Family", created_by=self.user)
        FamilyMembership.objects.create(
            family=self.family,
            user=self.user,
            role=FamilyMembership.Role.OWNER,
        )

        self.baby = Baby.objects.create(
            family=self.family,
            name="Noah",
            timezone="UTC",
            created_by=self.user,
        )

        create_event_for_baby(
            self.user,
            self.baby,
            {
                "event_type": Event.EventType.FEEDING,
                "occurred_at_local": timezone.datetime(2026, 2, 10, 8, 0),
                "timezone": "UTC",
                "details": {"method": "bottle", "amount_ml": 120},
            },
        )
        create_event_for_baby(
            self.user,
            self.baby,
            {
                "event_type": Event.EventType.DIAPER,
                "occurred_at_local": timezone.datetime(2026, 2, 10, 9, 0),
                "timezone": "UTC",
                "details": {"diaper_type": "wet"},
            },
        )

        self.client = Client()
        self.client.login(username="summary", password="pass1234")

    def test_daily_summary_endpoint(self):
        response = self.client.get(
            reverse("api_daily_summary", kwargs={"baby_id": self.baby.id}),
            {"date": "2026-02-10", "timezone": "UTC"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["by_type"]["feeding"], 1)
        self.assertEqual(body["by_type"]["diaper"], 1)

    def test_post_events_respects_idempotency_key(self):
        payload = {
            "event_type": "feeding",
            "occurred_at_local": "2026-02-10T12:00:00",
            "timezone": "UTC",
            "details": {"method": "bottle", "amount_ml": 90},
        }
        url = reverse("api_baby_events", kwargs={"baby_id": self.baby.id})

        first = self.client.post(
            url,
            data=payload,
            content_type="application/json",
            headers={"Idempotency-Key": "same-key"},
        )
        second = self.client.post(
            url,
            data=payload,
            content_type="application/json",
            headers={"Idempotency-Key": "same-key"},
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(IdempotencyRecord.objects.filter(user=self.user, key="same-key").count(), 1)

    def test_post_events_returns_sanitized_error_message(self):
        payload = {
            "event_type": "feeding",
            "occurred_at_local": "2026-02-10T12:00:00",
            "timezone": "Invalid/Timezone",
            "details": {"method": "bottle", "amount_ml": 90},
        }
        url = reverse("api_baby_events", kwargs={"baby_id": self.baby.id})

        response = self.client.post(
            url,
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Invalid request payload.")
