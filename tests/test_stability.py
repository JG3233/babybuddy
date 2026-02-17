from __future__ import annotations

from apps.babies.models import Baby
from apps.families.models import Family, FamilyMembership
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class NavigationStabilityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("stable", "stable@example.com", "pass1234")
        self.client = Client()
        self.client.login(username="stable", password="pass1234")

    def test_dashboard_and_babies_do_not_crash_with_invalid_active_family_session(self):
        session = self.client.session
        session["active_family_id"] = "not-a-uuid"
        session.save()

        dashboard = self.client.get(reverse("dashboard"))
        babies = self.client.get(reverse("babies"))

        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(babies.status_code, 200)

    def test_family_switch_invalid_id_does_not_persist_bad_value(self):
        response = self.client.get(reverse("family_switch"), {"family": "bad-value"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("active_family_id", self.client.session)

    def test_timeline_ignores_invalid_baby_filter(self):
        response = self.client.get(reverse("timeline"), {"baby": "bad-uuid"})
        self.assertEqual(response.status_code, 200)


class EventValidationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("eventstable", "eventstable@example.com", "pass1234")
        self.family = Family.objects.create(name="Stable Family", created_by=self.user)
        FamilyMembership.objects.create(
            family=self.family,
            user=self.user,
            role=FamilyMembership.Role.OWNER,
        )
        self.baby = Baby.objects.create(
            family=self.family,
            name="Stable Baby",
            timezone="UTC",
            created_by=self.user,
        )
        self.client = Client()
        self.client.login(username="eventstable", password="pass1234")

    def test_event_create_with_invalid_timezone_returns_form_error(self):
        response = self.client.post(
            reverse("event_create", kwargs={"baby_id": self.baby.id}),
            {
                "event_type": "feeding",
                "occurred_at_local": "2026-02-16T10:30",
                "timezone": "Mars/Phobos",
                "notes": "test",
                "feeding_method": "bottle",
                "feeding_amount_ml": "80",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Invalid timezone", status_code=400)

    def test_event_new_form_posts_to_create_endpoint(self):
        response = self.client.get(reverse("event_new", kwargs={"baby_id": self.baby.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'action="{reverse("event_create", kwargs={"baby_id": self.baby.id})}"',
        )

    def test_event_edit_form_posts_to_update_endpoint(self):
        create_response = self.client.post(
            reverse("event_create", kwargs={"baby_id": self.baby.id}),
            {
                "event_type": "feeding",
                "occurred_at_local": "2026-02-16T10:30",
                "timezone": "UTC",
                "notes": "edit-me",
                "feeding_method": "bottle",
                "feeding_amount_ml": "90",
            },
            follow=True,
        )
        self.assertEqual(create_response.status_code, 200)

        event = self.baby.events.order_by("-created_at").first()
        self.assertIsNotNone(event)

        response = self.client.get(reverse("event_edit", kwargs={"event_id": event.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'action="{reverse("event_update", kwargs={"event_id": event.id})}"',
        )


class NavigationVisibilityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("nav", "nav@example.com", "pass1234")
        self.client = Client()
        self.client.login(username="nav", password="pass1234")

    def test_nav_hides_baby_timeline_calendar_without_family(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/families/"')
        self.assertNotContains(response, 'href="/babies/"')
        self.assertNotContains(response, 'href="/timeline"')
        self.assertNotContains(response, 'href="/calendar"')

    def test_nav_shows_babies_with_family_and_timeline_with_baby(self):
        family = Family.objects.create(name="Nav Family", created_by=self.user)
        FamilyMembership.objects.create(
            family=family,
            user=self.user,
            role=FamilyMembership.Role.OWNER,
        )

        with_family = self.client.get(reverse("dashboard"))
        self.assertContains(with_family, 'href="/babies/"')
        self.assertNotContains(with_family, 'href="/timeline"')

        Baby.objects.create(
            family=family,
            name="Nav Baby",
            timezone="UTC",
            created_by=self.user,
        )

        with_baby = self.client.get(reverse("dashboard"))
        self.assertContains(with_baby, 'href="/timeline"')
        self.assertContains(with_baby, 'href="/calendar"')
