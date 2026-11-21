# Nexus ERP — Schema parity review (2026-11-21)

## Scope and evidence

This review is based on GitHub Actions run [44943198113](https://github.com/minamishelshaker-dev/nexus-erp/actions/runs/44943198113), PostgreSQL 16 disposable CI database, and commit `77766dffadfb1a1f8a0377bc48debeeaf970b5e5` on `integration/stage23-safety-patch`.

The run completed successfully:
- Billing authorization regression tests: passed.
- Frontend TypeScript/Vite build: passed.
- Fresh PostgreSQL migration smoke test: passed.
- Alembic revision graph diagnostics: completed.
- ORM inventory: 109 ORM tables; 124 public database tables after committed migrations; 0 ORM table names missing.

The successful table-name inventory is **not** full schema parity and is not a production-readiness approval.

## Full ORM parity diagnostic

A separate Alembic autogenerate comparison was run against the disposable database. Its generated draft was inspected only; it was not committed or applied to a live database.

Reported operation counts:
- add_column: 384
- drop_column: 384
- alter_column: 130
- create_foreign_key: 50
- create_index: 138
- drop_index: 138
- create_unique_constraint: 18
- drop_constraint: 68
- create_table: 14
- drop_table: 14

The comparison identifies these 14 database tables as absent from the current ORM metadata:
`sales_quotations`, `projects`, `purchase_requisitions`, `sales_order_lines`, `sales_orders`, `attendance_records`, `partner_contacts`, `refresh_tokens`, `categories`, `project_tasks`, `employees`, `chart_of_accounts`, `journal_entry_lines`, `timesheets`.

These may represent legacy schema, renamed/replaced models, or still-required functionality. They must be classified before any removal or data migration.

The diagnostic also reports substantial column-level differences across shared tables, including `users`, `roles`, `leads`, `opportunities`, `partners`, `products`, `purchase_orders`, `purchase_order_lines`, `journal_entries`, `bills_of_materials`, `bom_lines`, `manufacturing_orders`, `stock_moves`, and `warehouses`. Examples include old/new field-name pairs such as `users.is_active` vs `users.status`, `journal_entries.reference` vs `journal_entries.ref`, and `stock_moves.warehouse_id` vs `warehouse_from_id`/`warehouse_to_id`.

Alembic also warns that the ORM has a mutually dependent foreign-key cycle between `departments` and `users`; this needs explicit constraint-order handling rather than relying on autogenerate.

## Safety decisions

1. Do not run the full autogenerate draft against Supabase or any production database.
2. Do not drop the 14 database-only tables or the 384 database-only columns. Some may hold data or represent still-used modules.
3. Do not blindly add the 384 ORM-side columns or alter 130 columns. Many differences appear to be semantic renames or divergent model generations; adding both names could create inconsistent application behavior.
4. Do not treat the exported SQL artifact as a production migration approval. It represents the committed Alembic chain on a fresh disposable PostgreSQL database, not a verified transformation of an existing live database.

## Required next work

1. Establish the canonical model/schema version for each business domain.
2. Classify the 14 database-only tables as retained legacy, renamed/replaced, or obsolete; define explicit data-preserving migration paths where needed.
3. For each shared table, map old columns to canonical ORM fields, including types, nullability, defaults, enum values, constraints, indexes, and foreign keys.
4. Resolve the `users`/`departments` FK cycle with staged constraint creation.
5. Generate small, reviewed migrations by domain; test fresh-install and upgrade-from-legacy paths independently.
6. Add a CI gate that fails on unresolved destructive parity operations and unresolved column mismatches.
7. Only after those checks, prepare a reviewed Supabase backup/restore and migration rehearsal.

## Current deployment/database boundary

The Vercel deployment for the integration branch is a READY preview, not a production deployment. The project currently has no environment variables configured for the integration branch or project-wide listing, so the preview cannot yet be considered connected to a live application database. No Supabase live schema changes were made by this work.

**Conclusion:** Fresh migrations now execute successfully on disposable PostgreSQL and every ORM table name is present, but full schema parity is still materially incomplete. Production database rollout remains blocked pending domain-by-domain reconciliation.
