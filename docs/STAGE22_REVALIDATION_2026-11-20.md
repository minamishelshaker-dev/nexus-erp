# Nexus ERP — Stage 22 revalidation (2026-11-20)

## Scope and method

This is a revalidation of the extracted Stage 22 source tree at `/mnt/data/nexus_stage22_extract/nexus-erp`. It is not a production certification. No live database was modified and no deployment was triggered.

## Verified results

| Check | Result | Evidence |
|---|---|---|
| Python bytecode compilation | PASS | `python -m compileall -q backend` |
| Python AST parsing | PASS | 94 Python files parsed |
| Alembic migration graph | PASS | `alembic heads` reports one head: `add_bank_reconciliation_stage20` |
| Frontend dependency installation | BLOCKED | Offline npm cache does not contain all dependencies; network install was not attempted |
| Frontend production build | NOT RUN | Dependencies are not installed |
| Backend pytest suite | BLOCKED | First run lacked `PYTHONPATH`; corrected run then stopped during import because `python-jose` is not installed |
| PostgreSQL migration execution | NOT RUN | No disposable/live PostgreSQL server is available in this execution environment |

## Important cloud database finding

The staged Supabase SQL file `supabase/migrations/20261120073951_initial_schema_stage21.sql` is approximately 41 KB and contains 40 `CREATE TABLE` statements, 2 `ALTER TABLE` statements, and **zero** `ENABLE ROW LEVEL SECURITY`, `CREATE POLICY`, trigger, or function statements.

This does not prove that RLS is required for every backend access path: the FastAPI service may connect using a privileged server-side database role and enforce tenant isolation in application code. It does mean this file must not be described as a complete Supabase security configuration or exposed as a client-accessible schema. Do not apply it to the cloud project until it has been reconciled against the full Alembic schema, tenant isolation model, and intended database role.

## Code-level observations requiring follow-up

1. `backend/app/main.py` currently registers CORS, conditional TrustedHost, and request-timing middleware. It does not register `TenantMiddleware` from `backend/app/core/tenant_middleware.py`. Tenant context therefore must not be assumed to be populated globally by middleware in the current app.
2. `TenantMiddleware._resolve_from_token` currently accepts a signed token's `tenant_id` claim without checking that it is an access token. If tenant lookup fails, it falls back to minimal tenant information derived from that claim. This should be hardened before registering the middleware.
3. `get_current_user` in `backend/app/core/security.py` does compare the token tenant ID to the current user's database tenant ID. This is a useful guard, but it does not automatically protect routes that omit the authentication dependency.
4. The project has six Alembic version files and one reported head. The single-head result does not establish that the migrations create every ORM model/table; schema-drift reconciliation remains required.

## Deployment decision

**NO-GO for production deployment at this point.** The repository currently contains only bootstrap documentation and ignore rules; the full 288-file Stage 22 application source has not yet been transferred into it. The Vercel project is a shell with no deployment. The Supabase project is active but has no application tables or migrations applied.

## Next engineering gates

1. Transfer the complete source tree to the dedicated `nexus-erp` repository, excluding caches, local environments, and secrets.
2. Reconcile Alembic migrations against all ORM models and the Supabase SQL snapshot; decide whether Supabase is only the managed PostgreSQL host or also a direct client-facing API.
3. Harden tenant resolution and audit every protected route for authentication and tenant authorization before enabling tenant middleware.
4. Install pinned dependencies in CI, run frontend build and backend tests, then apply migrations to a disposable PostgreSQL database and verify the resulting schema.
5. Only after those gates pass, configure deployment environment variables and deploy a preview build. No production secrets belong in Git.
