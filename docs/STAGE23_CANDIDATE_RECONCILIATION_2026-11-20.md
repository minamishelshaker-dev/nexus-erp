# Stage 23 candidate reconciliation

Date: 2026-11-20

## Scope

This branch is an isolated candidate built from the imported Stage 22 source snapshot. It is not a claim that the complete Stage 23 application source was present in the repository. The Stage 23 artifact found on `main` was a 114-line patch file describing three intended production-safety changes.

## Defect found in the original patch artifact

The patch at `patches/Nexus_ERP_stage23_production_safety.patch` is malformed in its final `docker-compose.yml` hunk: the third service's old password line is marked as context rather than a deletion, and the hunk counts do not match the supplied lines. A local `patch --dry-run` therefore fails with a malformed-patch error. If interpreted manually, the final hunk would leave the weak fallback and add a second `DATABASE_URL` entry rather than replace the old one.

## Corrected changes applied in this candidate

1. `backend/app/main.py`
   - Uses SQLAlchemy `text("SELECT 1")` for the readiness query.
   - Logs the exception server-side and returns HTTP 503 when the database is unavailable.
2. `backend/app/core/tenant_middleware.py`
   - Only access tokens may establish tenant context.
   - Removes the unsafe fallback that trusted tenant data from a token when the database lookup failed.
   - Requires the tenant row to be active and not deleted.
3. `docker-compose.yml`
   - Removes the predictable password fallback from the Postgres service, backend, Celery worker, and Celery beat (four occurrences).
   - Compose now fails closed if `POSTGRES_PASSWORD` is missing.

## Verification

- Python `compileall` on the Stage 22 backend: PASS.
- Exact source-block checks for all three changes: PASS.
- All four weak Compose password fallbacks removed: PASS.
- No production database was modified.
- No deployment was triggered.
- Full dependency-based tests and disposable-PostgreSQL migration tests have not yet been run.

## Remaining release blockers

- `TenantMiddleware` is still not registered in `backend/app/main.py`. The tenant hardening in this candidate is therefore not active at runtime. Do not register it until the public/auth route allowlist, subdomain resolution, tenant scoping, and cross-tenant negative tests are reviewed.
- The previously identified ORM/migration mismatch (102 ORM tables versus 40 tables in the Alembic baseline) remains unresolved.
- Frontend dependency lockfile/build and backend dependency-based test suite remain unverified.
- This candidate must not be promoted to production or merged into `main` until the blockers above are closed.
