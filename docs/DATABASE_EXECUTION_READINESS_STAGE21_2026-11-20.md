# Stage 21 — Database execution readiness and migration repair

## Scope

This stage deliberately prepares an isolated development/verification database path. It does not create, connect to, or modify a production database. Production provisioning requires the owner's chosen hosting account, credentials, backup/restore plan, and an approved maintenance window.

## Changes

- Repaired the `add_journal_source_idempotency` Alembic migration so offline SQL generation no longer calls `.fetchall()` on Alembic's offline mock result.
- Kept the duplicate-source preflight in online mode. Online upgrades still stop before creating the unique index if active duplicate journal sources are found; no historical entries are auto-deleted or merged.
- Added `docker-compose.dev-db.yml`, a PostgreSQL 15 development-only service with a dedicated named volume, localhost-only port binding, health check, isolated internal network, and mandatory password supplied through the environment.
- Kept the production `docker-compose.yml`, `.env`, database URLs, and existing deployment untouched.

## Local development database startup

Set a strong throwaway password in the shell or a local, untracked `.env.dev` file:

```bash
export NEXUS_DEV_POSTGRES_PASSWORD='replace-with-a-long-random-development-secret'
docker compose -f docker-compose.dev-db.yml up -d
```

Use this URL from a host-side backend process:

```text
postgresql+asyncpg://nexus_dev:<password>@127.0.0.1:55432/nexus_erp_dev
```

For Alembic commands, run from `backend/` with the project's required environment variables configured. First inspect the migration plan/history, then run `alembic upgrade head` against this isolated database. Never point this development configuration at a production URL.

## Validation and limits

- Python `compileall` completed successfully; all 94 backend Python files also passed AST parsing.
- `alembic upgrade head --sql` completed successfully and generated SQL for the full chain from `001_initial_schema` through `add_bank_reconciliation_stage20`. The journal-source unique index and both supplier-payment and bank-reconciliation table groups appear in the generated SQL.
- `alembic heads` reports one head: `add_bank_reconciliation_stage20`.
- Docker/Podman and PostgreSQL server binaries are not available in the current execution environment, so the database container cannot be started here.
- Therefore no claim is made that migrations have successfully executed against PostgreSQL, nor that the full schema matches all ORM models. That requires a live PostgreSQL integration run.
- Offline SQL output does not perform the duplicate-data preflight. Before production migration, run the online upgrade against a restored production backup/staging clone; the migration itself performs the preflight before creating the unique index.
