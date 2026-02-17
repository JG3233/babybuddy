# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BabyBuddy is a Python-first baby tracker with Django monolith architecture, focused on fast, reliable logging of diapers, feedings, sleep, and pumping events.

**Tech Stack:**
- Python 3.13+
- Django 5.x
- PostgreSQL 16
- Server-rendered UI (Django templates + vanilla JS)
- Internal JSON API (`/api/v1/...`)
- PWA baseline (manifest + service worker)

## Development Commands

**Environment Setup:**
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start local PostgreSQL (exposed on port 55432)
docker compose -f infra/docker-compose.yml up -d db
```

**Running the Application:**
```bash
# Run migrations (from app directory)
cd app && python manage.py migrate

# Create admin user (optional)
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

**Testing:**
```bash
# Run all tests (from app directory)
cd app && python manage.py test ../tests

# Run specific test file
python manage.py test ../tests/test_events.py

# Run specific test class or method
python manage.py test ../tests.test_events.EventTestCase.test_create_feeding
```

**Code Quality:**
```bash
# Linting with ruff (configured in pyproject.toml)
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

**Database Management:**
```bash
# Create new migration
cd app && python manage.py makemigrations

# Show migration SQL
python manage.py sqlmigrate <app_name> <migration_number>

# Access PostgreSQL shell
docker exec -it babybuddy-db psql -U babybuddy -d babybuddy
```

## Architecture

### Core Domain Model

**Multi-tenancy via Family:**
- `Family` - top-level tenant containing babies and caregivers
- `FamilyMembership` - links users to families with roles (owner/caregiver/viewer)
- `Baby` - belongs to a family, tracked by multiple caregivers
- `Event` - polymorphic event model with family/baby scoping

**Event System:**
- Base `Event` model with type discriminator (`event_type`)
- Type-specific detail models: `FeedingEvent`, `DiaperEvent`, `SleepEvent`, `PumpingEvent`
- One-to-one relationship between `Event` and detail models
- All events are family-scoped and require authorization checks

**Key Model Fields:**
- UUIDs used for all primary keys
- Timestamps: `occurred_at_utc` (for events), `created_at`, `updated_at`
- Timezone awareness: events store both UTC timestamp and timezone name
- Audit fields: `created_by`, `updated_by` track user who performed actions

### Service Layer Pattern

Business logic lives in `apps/<app>/services.py`, not in views or models:

- **`apps/events/services.py`** - Event creation, updates, deletion, summaries, authorization
- **`apps/families/services.py`** - Family membership and access control

**Authorization Pattern:**
```python
# Always use service-layer authorization functions
baby = require_baby_access(request.user, baby_id)  # raises PermissionDenied
require_family_write(request.user, family)  # raises PermissionDenied

# Query helpers that auto-filter by user permissions
event_queryset_for_user(request.user).filter(baby=baby)
```

### Security Architecture

**Family-scoped Authorization:**
- Every data access requires family membership check
- Service layer functions (`require_*`) enforce permissions
- Views must call authorization checks before accessing family/baby/event data

**Rate Limiting:**
- Custom rate limit decorator in `apps/common/security.py`
- Uses Django cache for token bucket implementation
- Configured per-view with different limits for GET/POST
- Example: `@rate_limit(limit=240, window_seconds=60, key_func=key_user_or_ip, methods={"GET"})`

**Security Headers:**
- Custom middleware: `apps/common/middleware.SecurityHeadersMiddleware`
- CSP, permissions policy, framing protection
- Production: HSTS, secure cookies, HTTPS redirect enforced

**Idempotency:**
- API supports idempotency keys via `IdempotencyRecord` model
- Prevents duplicate event creation from retries

### Settings Organization

Three-layer settings structure:
- `babybuddy/settings/base.py` - Shared configuration
- `babybuddy/settings/local.py` - Development (DEBUG=true, uses .env)
- `babybuddy/settings/production.py` - Production (strict SECRET_KEY validation, HSTS, secure cookies)

Environment variables loaded via `python-dotenv` from `.env` file.

### API Conventions

**Internal JSON API Endpoints:**
- `GET/POST /api/v1/babies/<baby_id>/events` - List/create events
- `PATCH/DELETE /api/v1/events/<event_id>` - Update/delete specific event
- `GET /api/v1/babies/<baby_id>/summary/daily?date=YYYY-MM-DD` - Daily summary
- `GET /api/v1/babies/<baby_id>/summary/range?from=YYYY-MM-DD&to=YYYY-MM-DD` - Range summary

**Error Handling:**
- Use `_json_error(message, status)` helper in API views
- Never leak raw exceptions to clients
- Return sanitized error messages

### Template Structure

- Base templates in `app/templates/`
- App-specific templates in `app/apps/<app>/templates/<app>/`
- Context processors in `apps/accounts/context_processors.py` provide nav state

### Static Assets

- Whitenoise serves static files with compression and caching
- `STATIC_URL = "/static/"` for development
- `STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"`
- Run `python manage.py collectstatic` before production deploy

## Testing Conventions

- Tests live in top-level `tests/` directory (outside `app/`)
- Test files: `test_*.py` format
- Django test runner configured in `pyproject.toml`
- Use `DJANGO_SETTINGS_MODULE = "babybuddy.settings.local"` for tests
- Tests should create test users and family memberships for authorization checks

## Deployment

**Target:** Render web service + managed PostgreSQL

**Configuration:** `infra/render.yaml`

**Build command:**
```bash
pip install -r ../requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

**Start command:**
```bash
gunicorn babybuddy.wsgi:application --bind 0.0.0.0:$PORT
```

**Required environment variables (set in Render):**
- `SECRET_KEY` - Auto-generated, must be >50 chars with >5 unique chars
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `CSRF_TRUSTED_ORIGINS` - Comma-separated list with protocol (https://...)
- Database credentials - Auto-wired from Render database

**Health endpoint:** `/healthz`

## Common Patterns

**Creating a new event type:**
1. Add new choice to `Event.EventType`
2. Create detail model (e.g., `NewEventType(models.Model)`) with `OneToOneField` to `Event`
3. Update `_apply_detail()` in `events/services.py`
4. Add serialization logic to `serialize_event()` in `events/services.py`
5. Create form/view for UI
6. Add API tests in `tests/test_events.py`

**Adding a new family-scoped resource:**
1. Add `family = ForeignKey(Family, on_delete=CASCADE)` to model
2. Create service functions with authorization checks
3. Use `require_family_membership()` or `require_family_write()` before access
4. Add family filter to all querysets
5. Test with multiple families to ensure isolation

**Adding rate limiting to a view:**
```python
from apps.common.security import rate_limit, key_user_or_ip

@rate_limit(limit=60, window_seconds=60, key_func=key_user_or_ip)
def my_view(request):
    ...
```

## Database Notes

- Local PostgreSQL exposed on port **55432** (not 5432) to avoid conflicts
- Always use timezone-aware datetimes
- UUIDs for PKs mean no sequential ID leakage
- Use `select_related()` and `prefetch_related()` for N+1 query prevention
