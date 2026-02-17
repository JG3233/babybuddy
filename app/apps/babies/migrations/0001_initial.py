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
    ]

    operations = [
        migrations.CreateModel(
            name="Baby",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("birth_date", models.DateField(blank=True, null=True)),
                ("timezone", models.CharField(default="UTC", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="babies_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "family",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="babies",
                        to="families.family",
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="baby",
            constraint=models.UniqueConstraint(
                fields=("family", "name", "birth_date"),
                name="uniq_family_baby_name_birthdate",
            ),
        ),
    ]
