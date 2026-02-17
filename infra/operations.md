# Operations Checklist

## Runtime
- Deployment target: Render web service + managed Postgres.
- App health endpoint: `/healthz`.

## Baseline monitoring
- Enable Render uptime/availability alerts.
- Add app-level error tracking (Sentry or equivalent).
- Capture structured logs from app + request context.

## Backups and restore drill
1. Verify managed Postgres backup policy is enabled.
2. Weekly: restore latest backup to a temporary database.
3. Run smoke checks against restored DB:
   - login
   - timeline load
   - event create and query
4. Record restore time and issues.

## Incident response (v1)
- Trigger alert on sustained 5xx spike.
- Rollback to previous deploy if spike persists.
- Communicate incident summary in project notes.
