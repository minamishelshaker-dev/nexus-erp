# Stage 15 — Accounting Source Idempotency and Receipt Integrity

## Scope

This stage hardens the accounting boundary between operational documents and journal entries. It does not deploy changes or execute database migrations.

## Changes

1. `AccountingService.create_journal_entry` now requires `source_model` and `source_id` together, checks for an existing active source entry, and validates every account, partner, and analytic account before flushing the parent journal entry.
2. Journal-entry model metadata defines a PostgreSQL partial unique index on `(tenant_id, source_model, source_id)` for active rows with a non-null source. This is the final concurrency guard; the service-level duplicate lookup alone is not concurrency-safe.
3. Added Alembic migration `add_journal_source_idempotency`, chained after `add_tenant_billing`. It checks for existing duplicate active source entries and aborts with a diagnostic instead of modifying historical accounting records, then creates the unique partial index.
4. Purchase-receipt accounting now requires a completed receipt, validates the supplied purchase order against the receipt's actual tenant-scoped relation, and fetches receipt lines explicitly with tenant and soft-delete filters.

## Validation performed

- Python compileall completed successfully.
- AST parsing passed for 89 backend Python files.
- Eight focused static assertions passed, covering source-pair validation, duplicate precheck, validation-before-flush, unique-index metadata, migration duplicate preflight, receipt state, tenant-scoped receipt lines, and purchase-order matching.
- No live PostgreSQL migration, duplicate-race test, journal posting transaction test, or end-to-end purchase receipt test was run.

## Operational cautions

- Before applying the migration to any database, inspect and reconcile duplicate active `(tenant_id, source_model, source_id)` groups. The migration intentionally stops if any exist.
- The unique index enforces source idempotency under concurrent requests, but integration handlers should still be exercised with transaction/savepoint tests. Do not treat service-level prechecks as a substitute for the database constraint.
- The migration has not been applied to production or any connected database.
