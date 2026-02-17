from __future__ import annotations

import hashlib
import ipaddress
import os
import time
from collections.abc import Callable
from functools import wraps

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse


def get_client_ip(request: HttpRequest) -> str:
    """
    Get the client's IP address for rate limiting and logging.

    SECURITY WARNING: Only set TRUST_X_FORWARDED_FOR=true when running behind
    a trusted reverse proxy (e.g., Render, Heroku, nginx, CloudFlare) that:
    1. Strips existing X-Forwarded-For headers from client requests
    2. Sets X-Forwarded-For to the actual client IP

    If TRUST_X_FORWARDED_FOR is enabled, validates the IP address format
    to prevent header injection attacks.

    Returns:
        str: Client IP address or "unknown" if not available
    """
    trust_forwarded = os.getenv("TRUST_X_FORWARDED_FOR", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if trust_forwarded:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").strip()
        if forwarded:
            # X-Forwarded-For format: "client, proxy1, proxy2"
            # Take the leftmost (client) IP
            client_ip = forwarded.split(",")[0].strip()

            # Validate IP address format to prevent injection
            try:
                ipaddress.ip_address(client_ip)
                return client_ip
            except ValueError:
                # Invalid IP format - fall back to REMOTE_ADDR
                # Log this for security monitoring
                pass

    # Use direct connection IP (most secure, works without reverse proxy)
    return request.META.get("REMOTE_ADDR", "unknown")


def key_ip(request: HttpRequest) -> str:
    return f"ip:{get_client_ip(request)}"


def key_user_or_ip(request: HttpRequest) -> str:
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return f"user:{user.id}"
    return key_ip(request)


def default_rate_limit_response(request: HttpRequest, retry_after: int) -> HttpResponse:
    if request.path.startswith("/api/"):
        response = JsonResponse(
            {"error": "Rate limit exceeded. Please retry shortly."},
            status=429,
        )
    else:
        response = HttpResponse("Too many requests. Please retry shortly.", status=429)

    response["Retry-After"] = str(max(retry_after, 1))
    return response


def rate_limit(
    *,
    limit: int,
    window_seconds: int,
    key_func: Callable[[HttpRequest], str] = key_ip,
    methods: set[str] | None = None,
    response_factory: Callable[[HttpRequest, int], HttpResponse] = default_rate_limit_response,
):
    methods_upper = {method.upper() for method in methods} if methods else None

    def decorator(view):
        @wraps(view)
        def wrapped(request: HttpRequest, *args, **kwargs):
            if methods_upper and request.method.upper() not in methods_upper:
                return view(request, *args, **kwargs)

            now = int(time.time())
            bucket = now // window_seconds
            retry_after = window_seconds - (now % window_seconds)

            # Build unique cache key for this view, user/IP, and time bucket
            view_name = f"{view.__module__}.{view.__name__}"
            key_identifier = key_func(request)
            key_source = f"{view_name}:{key_identifier}:{bucket}:{window_seconds}"
            key_hash = hashlib.sha256(key_source.encode("utf-8")).hexdigest()
            cache_key = f"rate-limit:{key_hash}"

            count = cache.get(cache_key)
            if count is None:
                cache.set(cache_key, 1, timeout=window_seconds + 1)
                count = 1
            else:
                try:
                    count = cache.incr(cache_key)
                except ValueError:
                    cache.set(cache_key, 1, timeout=window_seconds + 1)
                    count = 1

            if int(count) > limit:
                return response_factory(request, retry_after)
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
