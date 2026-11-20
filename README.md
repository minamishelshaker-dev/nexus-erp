# Nexus ERP

Nexus ERP is the standalone enterprise resource planning application in the Nexus product ecosystem.

## Architecture boundaries

- Nexus ERP has its own application, deployment, and PostgreSQL database.
- Legal Nexus remains an independent legal-management application with a separate database.
- Cross-product integration will use authenticated APIs and event-based synchronization; databases will not be merged.

## Application layout

The application source is organized as:

- `frontend/` — React + TypeScript + Vite web application.
- `backend/` — FastAPI + SQLAlchemy backend and Alembic migrations.
- `supabase/` — Supabase project configuration and SQL migrations.
- `docs/` — architecture, operations, and implementation notes.

## Current deployment status

Cloud resources have been provisioned separately for Nexus ERP. The application source and database migrations must be committed and tested before enabling an automatic production deployment. Do not deploy secrets or local `.env` files.

## Local development

See `README_PROD.md`, `MIGRATIONS.md`, and `DEPLOYMENT_CHECKLIST.md` after the application source has been added.