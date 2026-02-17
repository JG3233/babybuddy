from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.babies.models import Baby
from apps.events.models import Event
from apps.events.services import recent_counts_for_family
from apps.families.services import parse_uuid_or_none, user_families


@login_required
@require_GET
def dashboard_view(request: HttpRequest):
    families = user_families(request.user)
    active_family_uuid = parse_uuid_or_none(request.session.get("active_family_id"))

    if active_family_uuid:
        active_family = families.filter(id=active_family_uuid).first()
    else:
        active_family = families.first()

    if active_family:
        request.session["active_family_id"] = str(active_family.id)
    elif "active_family_id" in request.session:
        request.session.pop("active_family_id", None)

    babies = Baby.objects.filter(family=active_family).order_by("name") if active_family else Baby.objects.none()
    active_baby_uuid = parse_uuid_or_none(request.GET.get("baby"))
    active_baby = babies.filter(id=active_baby_uuid).first() if active_baby_uuid else babies.first()

    stats = {
        "feeding": 0,
        "diaper": 0,
        "sleep": 0,
        "pumping": 0,
        "last_24h": 0,
        "last_7d": 0,
        "last_30d": 0,
    }

    if active_family:
        by_type = recent_counts_for_family(active_family.id, hours=24)
        stats.update(by_type)
        stats["last_24h"] = sum(by_type.values())

    if active_baby:
        now = timezone.now()
        stats["last_7d"] = Event.objects.filter(
            baby=active_baby,
            occurred_at_utc__gte=now - timedelta(days=7),
            occurred_at_utc__lte=now,
        ).count()
        stats["last_30d"] = Event.objects.filter(
            baby=active_baby,
            occurred_at_utc__gte=now - timedelta(days=30),
            occurred_at_utc__lte=now,
        ).count()

    return render(
        request,
        "analytics/dashboard.html",
        {
            "families": families,
            "active_family": active_family,
            "babies": babies,
            "active_baby": active_baby,
            "stats": stats,
        },
    )


@require_GET
def health_view(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@require_GET
def manifest_view(request: HttpRequest) -> JsonResponse:
    data = {
        "name": "BabyBuddy",
        "short_name": "BabyBuddy",
        "description": "Track diapers, feedings, sleep, and pumping.",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f4f7fb",
        "theme_color": "#0f172a",
        "icons": [
            {
                "src": "/static/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": "/static/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
            },
        ],
    }
    return JsonResponse(data)


@require_GET
def service_worker_view(request: HttpRequest) -> HttpResponse:
    content = """
const CACHE_NAME = 'babybuddy-static-v2';
const STATIC_URLS = [
  '/static/css/app.css',
  '/static/js/app.js',
  '/manifest.webmanifest',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_URLS)));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') {
    return;
  }

  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  const isStatic = url.pathname.startsWith('/static/') || url.pathname === '/manifest.webmanifest';
  if (isStatic) {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
    return;
  }

  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request));
  }
});
""".strip()
    response = HttpResponse(content, content_type="application/javascript")
    response["Cache-Control"] = "no-cache"
    return response
