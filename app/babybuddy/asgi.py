"""ASGI config for BabyBuddy."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babybuddy.settings.production")

application = get_asgi_application()
