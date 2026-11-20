# Nexus ERP — Cloud bootstrap (2026-11-20)

## Supabase

- Organization: `xjhliuxikaeihzfawvsp`
- Project: `Nexus ERP`
- Project ref: `ewsfegpbqshtqexlwxrm`
- Region: `eu-central-1`
- Initial project quote returned by Supabase: `$0/month` (this is not a guarantee that future usage, add-ons, or plan upgrades are free)
- Project status at creation: `ACTIVE_HEALTHY`
- API URL: `https://ewsfegpbqshtqexlwxrm.supabase.co`
- Database: PostgreSQL 17

The project is isolated from Hayah, Legal Nexus, and the existing `mms-leads` project. No production data was copied. No application tables or migrations have yet been applied to this cloud database. The initial schema migration is staged under `supabase/migrations/` and must be tested against a disposable/staging database before production use.

## Vercel

- Team: `hayah7`
- Project: `nexus-erp-web`
- Project ID: `prj_gXLaplzHKVH9s5XD49bMasM3h0sv`
- Framework: Vite
- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Status: project shell created; no Git repository linked and no deployment created.

## Remaining deployment gate

The connected GitHub account currently exposes `hayah-mvp` and `legal-nexus`, but no dedicated Nexus ERP repository. Do not put ERP source into either existing repository. Create a separate repository named `nexus-erp`, then connect it to the Vercel project. Backend deployment and environment variables must be configured separately after runtime and migration tests.
