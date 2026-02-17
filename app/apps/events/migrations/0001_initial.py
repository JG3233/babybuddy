# Generated manually for project bootstrap.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("families", "0001_initial"),
        ("babies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("feeding", "Feeding"),
                            ("diaper", "Diaper"),
                            ("sleep", "Sleep"),
                            ("pumping", "Pumping"),
                        ],
                        max_length=16,
                    ),
                ),
                ("occurred_at_utc", models.DateTimeField()),
                ("timezone", models.CharField(max_length=64)),
                ("notes", models.TextField(blank=True)),
                ("schema_version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "baby",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="babies.baby",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="events_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "family",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="families.family",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="events_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-occurred_at_utc", "-created_at"],
                "indexes": [
                    models.Index(fields=["family", "baby", "-occurred_at_utc"], name="events_event_family__b55af7_idx"),
                    models.Index(fields=["event_type", "-occurred_at_utc"], name="events_event_event_ty_d0fe1a_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="DiaperEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "diaper_type",
                    models.CharField(
                        choices=[("wet", "Wet"), ("dirty", "Dirty"), ("mixed", "Mixed"), ("dry", "Dry")],
                        max_length=16,
                    ),
                ),
                ("color", models.CharField(blank=True, max_length=64)),
                ("consistency", models.CharField(blank=True, max_length=64)),
                (
                    "event",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="diaper_detail",
                        to="events.event",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="FeedingEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "method",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("breast", "Breast"),
                            ("bottle", "Bottle"),
                            ("formula", "Formula"),
                            ("solids", "Solids"),
                            ("other", "Other"),
                        ],
                        max_length=16,
                    ),
                ),
                ("amount_ml", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "side",
                    models.CharField(
                        blank=True,
                        choices=[("left", "Left"), ("right", "Right"), ("both", "Both")],
                        max_length=8,
                    ),
                ),
                ("duration_min", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "event",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feeding_detail",
                        to="events.event",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PumpingEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount_ml", models.PositiveIntegerField(blank=True, null=True)),
                ("duration_min", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "side",
                    models.CharField(
                        blank=True,
                        choices=[("left", "Left"), ("right", "Right"), ("both", "Both")],
                        max_length=8,
                    ),
                ),
                (
                    "event",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pumping_detail",
                        to="events.event",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SleepEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_at_utc", models.DateTimeField()),
                ("end_at_utc", models.DateTimeField(blank=True, null=True)),
                (
                    "quality",
                    models.CharField(
                        choices=[("good", "Good"), ("ok", "OK"), ("rough", "Rough"), ("unknown", "Unknown")],
                        default="unknown",
                        max_length=16,
                    ),
                ),
                (
                    "event",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sleep_detail",
                        to="events.event",
                    ),
                ),
            ],
        ),
    ]
