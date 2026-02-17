# BabyBuddy

BabyBuddy is a Python-first baby tracker focused on fast, reliable logging of:

- Diapers
- Feedings
- Sleep
- Pumping

This repository implements a Django monolith architecture with:

- Server-rendered UI (`Django templates + local vanilla JS`)
- Internal JSON API (`/api/v1/...`) for charts and future native clients
- Family-scoped authorization (multiple caregivers and babies)
- PostgreSQL for local and production environments
- PWA baseline (manifest + service worker)

## Tech stack

- Python 3.13+
- Django 5.x
- PostgreSQL 16

## Quick start

1. Create and activate a virtual environment:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy env file:
   - `cp .env.example .env`
4. Start local Postgres:
   - `docker compose -f infra/docker-compose.yml up -d db`
5. Run migrations:
   - `cd app && python manage.py migrate`
6. (Optional) Create an admin user:
   - `python manage.py createsuperuser`
7. Run the app:
   - `python manage.py runserver`

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/accounts/register/`

## Local database note

- Docker Postgres is exposed on host port `55432` to avoid conflict with local Postgres on `5432`.
- Default local env values in `.env.example` already match this.

## Testing

Run all tests:

- `cd app && python manage.py test ../tests`

## Project layout

- `app/` Django project and apps
- `infra/` Local and deploy infrastructure config
- `tests/` Test suites

## Security posture

- Family-scoped authorization checks on event/baby/family data access
- CSRF protection on form endpoints
- Session and cookie hardening defaults
- Security headers middleware (CSP, permissions policy, framing protection)
- Auth/API rate limiting (login/register and API reads/writes)
- API error sanitization (no raw exception leakage to clients)
- Production hardening (HSTS, secure cookies, HTTPS redirect, strict secret key validation)
- No HIPAA claim in v1

## API summary

Core internal API endpoints:

- `GET/POST /api/v1/babies/<baby_id>/events`
- `PATCH/DELETE /api/v1/events/<event_id>`
- `GET /api/v1/babies/<baby_id>/summary/daily?date=YYYY-MM-DD`
- `GET /api/v1/babies/<baby_id>/summary/range?from=YYYY-MM-DD&to=YYYY-MM-DD`

## Deploy target

- Render web service + managed Postgres (see `infra/render.yaml`)
- Production settings module: `babybuddy.settings.production`
- Ensure these env vars are set securely in Render:
  - `SECRET_KEY`
  - `ALLOWED_HOSTS`
  - `CSRF_TRUSTED_ORIGINS`
  - database credentials (wired from Render database in `infra/render.yaml`)
