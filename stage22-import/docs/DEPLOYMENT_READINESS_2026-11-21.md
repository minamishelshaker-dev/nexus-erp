# Nexus ERP — Deployment Readiness and Environment Contract
Date: 2026-11-21
Branch: `integration/stage23-safety-patch`

## Current verified state

- Vercel project: `nexus-erp-api` (`fastapi` framework).
- Vercel project is not marked live. The latest production deployment is not a successful production release.
- Preview deployment `dpl_2Zir5TreJiHLZGNz8Mc88mgy2BuE` for commit `e85a2c6640aa454f677c45b881bd26709dc5acaf` reached `READY`.
- Newer preview deployment for commit `22b48404771aefeaac020e92aa4ae1bcc6bfff87` was still `QUEUED/BUILDING` at the last check; do not treat it as ready until Vercel reports `READY`.
- Vercel environment-variable inventory was empty at the time of review.
- Vercel SSO protection is enabled for deployments except custom domains. A successful build does not prove anonymous browser access.
- Supabase project `ewsfegpbqshtqexlwxrm` is `ACTIVE_HEALTHY`, PostgreSQL 17, region `eu-central-1`; its `public` schema currently has no application tables.
- No production database migration or production deployment was performed as part of this review.

## API runtime configuration contract

The backend settings module requires these two values at import/startup:

| Variable | Requirement | Notes |
|---|---|---|
| `DATABASE_URL` | Required secret | PostgreSQL connection URI for this Nexus ERP database only. Do not use a different application's database. |
| `SECRET_KEY` | Required secret | At least 32 characters; generate a unique high-entropy value per environment. Never commit it. |

Set these explicitly for production:

| Variable | Production value / guidance |
|---|---|
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `DATABASE_POOLER_MODE` | `transaction` when using Supabase transaction pooler; the code disables prepared statement caching and uses `NullPool` in this mode. |
| `CORS_ORIGINS` | JSON string array containing the exact deployed frontend origin(s), e.g. `["https://your-frontend-domain"]`; do not leave localhost as the only origin. |
| `ALLOWED_HOSTS` | Include the actual API custom domain and required Vercel hostname(s). |
| `LOG_LEVEL` | `INFO` or stricter. |

Optional integrations must be configured only when enabled:
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `OPENAI_API_KEY`, `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`

Do not add placeholder secrets or localhost service URLs to a production environment. Confirm the actual need and provider for each integration first.

## Frontend/API connection

The frontend reads `VITE_API_URL` at build time and otherwise falls back to the relative path `/api/v1`. If frontend and API are deployed on different origins, configure the frontend build variable `VITE_API_URL` to the API origin plus `/api/v1`, then include the frontend origin in backend `CORS_ORIGINS`.

The Vercel project reviewed here is the API project. A READY API preview is not evidence that the React frontend has been deployed or connected.

## Release gates — must pass before production

1. Complete legacy-to-current schema and data mapping; explicitly resolve every destructive or ambiguous mapping.
2. Run fresh-install migrations and legacy-upgrade tests on disposable PostgreSQL, including the synthetic preflight fixture.
3. Reconcile tenant ownership, users/roles, customer/supplier identities, products/UOM, stock ledgers, sales/purchase documents, payment allocations, and double-entry balances.
4. Perform backup and restore rehearsal for the target Supabase project.
5. Review migration SQL and verify no unapproved drops, truncations, tenant reassignment, or data-loss operations.
6. Configure and verify production environment variables and secrets without exposing values in logs or source control.
7. Deploy the API and frontend to preview; test `/health`, `/health/ready`, authentication, tenant isolation, and critical business workflows.
8. Obtain explicit approval before applying migrations to the live Supabase project, promoting a production deployment, or changing the production domain.

## Health endpoints

- `GET /` — application identity and documentation links.
- `GET /health` — process health.
- `GET /health/ready` — database-backed readiness; with valid runtime settings but an unavailable database, it returns HTTP 503. Because `DATABASE_URL` and `SECRET_KEY` are required settings, omitting either may prevent the application from starting before a health route can respond.

A Vercel deployment marked `READY` means its build/deployment process completed. It does not certify database readiness, working authentication, production data, or frontend integration.
