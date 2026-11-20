# Nexus ERP — Runtime and deployment configuration blockers
Date: 2026-11-20

This note records additional code-level issues found during Stage 22 inspection. No deployment or database changes were made.

## 1. Readiness endpoint uses a raw SQL string (high priority)

File: `backend/app/main.py`, `readiness_check()`

Current code calls:

```python
await session.execute("SELECT 1")
```

SQLAlchemy 2.x requires an executable SQL expression, normally:

```python
from sqlalchemy import text
await session.execute(text("SELECT 1"))
```

As written, the readiness probe can report the database as unhealthy even when the connection itself is available. In addition, the endpoint currently returns HTTP 200 even when its JSON body says `not_ready`; container orchestrators and uptime probes generally rely on the HTTP status. It should return a non-2xx status such as 503 when a required dependency is unavailable.

## 2. Docker Compose contains weak fallback database credentials (high priority)

File: `docker-compose.yml`

The Postgres service has fallback values:

- `POSTGRES_USER` defaults to `nexus_user`
- `POSTGRES_PASSWORD` defaults to `nexus_password`
- `POSTGRES_DB` defaults to `nexus_erp`

A production operator who forgets to supply the environment variables could unintentionally start a database with a predictable password. Production compose should fail closed when required secrets are absent rather than silently use a known password.

## 3. Frontend dependency reproducibility is incomplete

File: `frontend/package.json`

No npm lockfile is present in the Stage 22 source tree. The frontend therefore does not have a reproducible, pinned transitive dependency graph. The package manifest also combines React 19 with React type packages declared as React 18; this may cause TypeScript compatibility errors and must be confirmed by a clean install/build.

## 4. Startup and readiness are not deployment proof

The FastAPI lifespan initializes an engine/session factory but does not verify that migrations have been applied or that all expected tables exist. This is appropriate only if deployment has a separate migration gate. The application should not silently attempt runtime `create_all`; migrations must be applied by a controlled release step.

## Required actions before preview deployment

1. Correct the readiness SQL expression and return HTTP 503 on failure.
2. Remove insecure Compose credential defaults and validate mandatory production secrets at startup.
3. Generate and commit a frontend lockfile; align React and React type package major versions.
4. Add CI that installs locked dependencies, runs frontend typecheck/build and backend tests, and generates offline Alembic SQL.
5. Gate deployment on successful disposable-PostgreSQL migration and schema reconciliation.

These are release blockers. The active Nexus ERP Supabase project remains unchanged.
