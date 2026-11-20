# Nexus ERP – Implementation Log (2026-11-19)

## Scope
This is a staged working copy of `nexus-erp-final.zip`. The original archives are preserved. No deployment, production database migration, or production data modification was performed.

## Stage 1 – syntax and import repairs
- Fixed malformed syntax in `backend/app/api/v1/endpoints/stock_moves.py`.
- Removed the malformed duplicate workflow approval function in `backend/app/api/v1/endpoints/workflows.py` while retaining the valid implementation.
- Reworked audit request context to use `ContextVar` in `backend/app/core/audit.py`.
- Fixed missing imports / incorrect model export references in the affected backend modules (`user.py`, `models/__init__.py`, `ai.py`, `manufacturing.py`).

## Stage 2 – authentication and permission contract
- `backend/app/core/security.py`: verify that the tenant ID embedded in an access token matches the tenant ID currently stored on the user record. A token carrying a different tenant ID is rejected.
- `backend/app/core/security.py`: made `require_permission` support both existing call styles:
  - FastAPI dependency: `Depends(require_permission("permission.code"))`.
  - Existing inline call: `await require_permission(current_user, "permission.code")`.
- Added a small explicit alias map for legacy singular/read permission names to the canonical permission codes already used by RBAC. Aliases translate names only; they do not grant new rights.
- Updated `PermissionChecker` to apply the same aliases as inline checks.

## Verification performed
- Python AST syntax parse: 74/74 backend application Python files passed.
- `py_compile` passed for the changed security module.
- Permission contract smoke test: 3 checks passed (authorized legacy alias, denied ungranted permission, dependency factory form).
- The earlier stage-1 import smoke test for the models package was recorded separately in the conversation.

## Not yet verified / known blockers
- Full application import and runtime tests remain blocked in this environment because `python-jose` is not installed, although it is declared in `backend/requirements.txt`.
- No PostgreSQL instance or production-like database was available; database integration, Alembic migrations, tenant isolation across two real tenants, and concurrency tests remain unverified.
- The permission alias list is intentionally limited to codes that map clearly to existing canonical permission names. Several endpoint permissions (notably AI, payments, purchase invoices, and some stock actions) still need a complete permission catalogue and seed/migration review. They must fail closed until explicitly configured.
- The current user model stores a single `tenant_id`; it does not yet implement the agreed multi-organization membership model for a user belonging to multiple tenants.
- Tenant middleware and schema switching were not enabled. The existing schema-based implementation is not safe to activate before the agreed row-level tenant model is fully implemented.
- Token revocation / refresh-token rotation and persistent session validation are not complete.

## Safety note
This archive is a development checkpoint only. Do not deploy it or replace a running instance until dependency installation, database migrations, security tests, business workflow tests, and frontend build checks pass in a controlled staging environment.

## Stage 3 – inventory tenant isolation (critical path)
- Added tenant-scoped stock quantity lookups and creation; missing tenant context now fails closed.
- Scoped stock move confirmation, processing, and cancellation to `(move_id, tenant_id)` rather than fetching by primary key alone.
- Scoped product reads used by stock move creation and product cost calculations.
- Validated tenant ownership of referenced products, warehouses, stock locations, partners, and lots when creating stock moves; validated the global unit-of-measure record separately.
- Scoped inventory adjustment lookup and its lines to the active tenant.
- Scoped product aggregate quantity recalculation to the active tenant.
- Made stock movement and adjustment number counts tenant-local.
- Updated API call sites and the four existing integration-test calls to pass the tenant context explicitly.

## Stage 3 limitations
- This is a targeted repair of the inventory service critical path, not a complete tenant-isolation guarantee for every service or table.
- Stock valuation, reservation, warehouse relation consistency, concurrent quantity updates, and accounting integration still need dedicated review and database-backed tests.
- The existing integration test module contains other known API/signature mismatches and has not been executed end-to-end.

## Stage 4 – accounting and module-integration tenant scoping
- Added a fail-closed tenant record loader to AccountingService and used it for parent accounts, journal accounts, journal posting, balance updates, reversal, and account-tree descendants.
- Scoped journal items and line-level partner/analytic-account references to the same tenant.
- Made journal entry numbering tenant-local.
- Updated journal API and module-integration call sites to pass tenant context when posting entries.
- Added tenant-scoped record loading for key integration flows: stock movement/product, sales invoice/partner, sales order/products, receipt/products/stock moves, purchase invoice/partner, and manufacturing order/products.
- Integration stock accounting now rejects a stock-move object whose tenant does not match the supplied tenant.

## Stage 4 limitations
- These changes reduce direct primary-key cross-tenant access in the reviewed accounting/integration paths; they do not establish complete tenant isolation across all services, endpoints, background jobs, or related ORM relationships.
- Accounting period/journal/source-document validation, integration transaction boundaries, idempotency, and database-backed cross-tenant tests still require review.
- The project has not been run against PostgreSQL; AST parsing is a static syntax check, not runtime or business-logic validation.

## Stage 5 – accounting posting integrity and concurrency guards
- Journal creation now normalizes incoming debit/credit values to `Decimal`, rejects non-finite or negative amounts, rejects a line containing both debit and credit, and requires exact equality of total debits and credits (matching the database check constraint).
- Journal posting now locks the tenant-scoped draft entry with `SELECT ... FOR UPDATE`, verifies that at least two tenant-scoped lines exist, recomputes line totals, and checks that the stored header totals still match before updating any account balances.
- Journal reversal now locks the tenant-scoped original entry and rejects a second reversal when an active reversal already references it.
- Re-import smoke test passed for AccountingService and IntegrationService with test-only environment variables and a Stripe stub. This confirms module import only; it does not exercise database behavior.
- Python AST syntax parse: 81/81 backend application and test Python files passed after these changes.

## Stage 5 limitations and migration blocker
- `SELECT ... FOR UPDATE` behavior, duplicate reversal prevention under concurrent transactions, and exact decimal behavior still require PostgreSQL-backed tests.
- The current Alembic directory has two independent root revisions (`001_initial_schema` and `add_tenant_billing`, both with `down_revision = None`). The initial migration creates 30 tables and the billing migration creates 5; this is not evidence of complete coverage for the ORM model set. Alembic upgrade behavior and migration completeness remain blockers and were not altered in this stage to avoid generating a potentially destructive schema migration without a database baseline.
- No live PostgreSQL database, migration upgrade/downgrade, API integration, or end-to-end business workflow test was run.

## Stage 6 – Alembic revision chain and async engine configuration
- Linked `add_tenant_billing` after `001_initial_schema`, removing the two-root Alembic graph. Static Alembic ScriptDirectory validation now reports one base (`001_initial_schema`) and one head (`add_tenant_billing`).
- Reworked `alembic/env.py` to use SQLAlchemy's async engine bridge, matching the application's `postgresql+asyncpg` configuration; retained offline rendering and externally supplied connection support.
- Escaped percent signs when passing the configured database URL through Alembic ConfigParser interpolation.
- Static Python AST parsing passed for all 84 backend application and test Python files.

## Stage 6 critical blocker – ORM models are not registered
- Runtime inspection found `app.core.database.Base.metadata` contains **0 tables** after importing the application's model package. A representative model (`User`) has no mapped `__table__` attribute because `BaseModel` is currently a plain mixin and does not inherit from the application's declarative Base.
- An attempted local conversion exposed additional mapping blockers (legacy typed Column declarations and reserved `metadata` model attributes across several model files). The partial conversion was reverted rather than leaving the working tree in a broken intermediate state.
- Consequently, `Base.metadata.create_all()` and Alembic autogenerate cannot currently provide complete schema creation/diff coverage. The two hand-written migrations create 35 tables in total, which is not equivalent to the current ORM model inventory.
- Alembic graph validation passed, but `alembic upgrade head --sql` fails in `add_tenant_billing.upgrade()` because its live `information_schema` inspection expects a database result and is not offline-safe. No PostgreSQL connection, online upgrade, downgrade, migration data-safety, or runtime migration test was performed.
- Required next repair: establish one declarative registry shared by all models and the DB layer; migrate model declarations consistently (including legacy annotations and reserved attribute names); add metadata/table-count assertions; then create and review a baseline migration against an empty disposable PostgreSQL database before touching any existing database.

## Stage 7 – shared ORM registry and model relationship repairs
- Replaced the separate, unused declarative base in `core/database.py` with the shared declarative `Base` in `models/base.py`; `BaseModel` now inherits that declarative base. The DB layer and Alembic import the complete model package before using metadata.
- Preserved legacy `Column` declarations with `__allow_unmapped__` and removed plain type annotations from shared mixin columns that SQLAlchemy incorrectly interpreted as unmapped attributes.
- Registered the previously omitted `activity`, `company`, `notification`, `workflow`, and `tenant` model modules.
- Corrected reserved `metadata` ORM attributes to `metadata_json` while preserving physical SQL column name `metadata`; updated `BaseModel.to_dict()` to map physical columns to ORM property keys.
- Resolved duplicate sales/billing `invoices` table naming by introducing `BillingInvoice` on `billing_invoices`, updating the billing API, tenant relationship, and billing migration.
- Repaired mapper configuration issues involving User–Role secondary joins, analytic account relations, self-referential Product variants and activity/comment trees, purchase-order invoices, and invalid cross-domain relationships lacking foreign keys.
- Added `backend/tests/test_model_registry.py` as a regression test for metadata count, mapper configuration, and tenant foreign keys.
- Updated the billing migration to avoid runtime `information_schema` inspection, enabling offline SQL rendering for the current linear revision chain.

## Stage 7 verification
- Direct runtime SQLAlchemy check: **98 tables** and **98 mapped classes** registered; `configure_mappers()` passed with **zero warnings**.
- Alembic reports one head: `add_tenant_billing`.
- `alembic upgrade head --sql` successfully rendered static PostgreSQL SQL (offline only; no DB connection).
- The focused pytest module did not start because the environment does not have `python-jose` installed; the existing global `tests/conftest.py` imports it through the application entrypoint.
- AST syntax parsing and bytecode compilation are being run for the full backend tree before packaging.

## Stage 7 remaining critical blocker – migration/schema divergence
- The ORM registry has 98 tables, but the existing hand-written migrations create only 35 tables (30 in `001_initial_schema` and 5 in `add_tenant_billing`).
- Name comparison: 77 ORM tables are missing from the migrations, 14 migration-only legacy table names are not present in current ORM metadata, and only 21 names overlap.
- Offline SQL generation is now possible, but it does not resolve the missing-table/legacy-schema mismatch. A reviewed migration strategy and disposable PostgreSQL validation are still mandatory before production use.
- See `docs/DATABASE_SCHEMA_GAP_2026-11-19.md` for the full discrepancy and next actions.
- Follow-up static column comparison found major drift in same-name tables too (e.g., `products`: 58 ORM columns missing from the legacy migration definition; `users`: 24; `purchase_orders`: 25; `stock_moves`: 23). This confirms the migration gap requires a deliberate baseline/data-mapping strategy rather than a simple missing-table migration.

## Stage 9 – disable every remaining schema-switching path
- Corrected the Stage 8 checkpoint after a fresh inspection found that the Stage 8 archive still contained active schema-switching code in `database.py`, `tenant.py`, and `tenant_middleware.py`. The earlier Stage 8 status description overstated what was present in that archive; Stage 9 records the actual applied repair.
- Removed mutable `_current_tenant` state from `DatabaseManager`; sessions no longer execute `SET search_path`.
- Disabled per-tenant schema creation/deletion and runtime `Base.metadata.create_all()` by making legacy entry points fail closed with explicit errors. Schema changes must go through reviewed Alembic migrations.
- Removed `SET search_path` from `AsyncTenantContextManager`; retained `schema_name` only as legacy tenant metadata.
- Converted `TenantSchemaMiddleware` to a deprecated no-op for import compatibility; it no longer changes global database state.
- Added `backend/tests/test_tenant_schema_switching_disabled.py` to guard these behaviors.

## Stage 9 verification
- Python AST parsing: 86/86 backend Python files passed.
- Runtime smoke checks: 5 passed using test-only environment values. Verified 98 ORM tables register, schema switching and schema lifecycle APIs fail closed, runtime `create_all` is disabled, and async tenant context does not issue schema SQL even when supplied a hostile schema name.
- Static search across `backend/app` and `backend/alembic` found no remaining `SET search_path`, `CREATE SCHEMA`, `DROP SCHEMA`, or `create_all()` calls.
- No PostgreSQL server was available; no live DB, cross-tenant HTTP, migration, or concurrency test was run.

## Stage 9 remaining tenant-isolation review
- AST inventory found 58 direct `db.get()` / `session.get()` call sites in services. These are candidates for tenant-scope review, not automatically confirmed vulnerabilities: some may load global reference data or may be protected by a previously scoped parent. Each tenant-owned model and call chain must be verified before patching.
- The current user/tenant membership model still supports a single `tenant_id` per user. This does not yet satisfy multi-organization membership/SSO for the broader Nexus ecosystem.
- Disabling schema switching removes an unsafe isolation mechanism; it does not itself prove complete row-level tenant isolation. Tenant filters and authorization must still be audited across endpoints, background jobs, reports, notifications, and AI services.

## Stage 10 – workflow and approval tenant-boundary repair
- Replaced all direct primary-key `db.get()` reads in `WorkflowService` with explicit tenant-scoped loaders for `Workflow` and `WorkflowExecution`.
- Added an approval loader that joins through its parent `WorkflowExecution`, because `WorkflowApproval` does not own a `tenant_id` column.
- Scoped approval listing, completion checks, approval/rejection, workflow execution, continuation, and history lookups through the active tenant's execution/workflow records.
- Fixed the invalid `WorkflowApproval.tenant_id` filter (the model has no such field) and removed unsupported `tenant_id` constructor arguments when creating approval rows.
- Corrected approval model semantics: pending approvals may have a null decision and decision timestamp; action-based approvals may have a null workflow step.
- Added regression tests for tenant-scoped workflow/approval query construction and approval model ownership semantics.

## Stage 10 verification
- WorkflowService import and SQLAlchemy mapper configuration passed with test-only stubs for dependencies missing from this environment (`stripe`, `croniter`).
- Focused workflow tenant-scope smoke checks: 2/2 passed, including compilation of the three tenant-scoped loader queries against PostgreSQL dialect.
- Direct unscoped `self.db.get()` calls in `WorkflowService`: 0 remaining.
- This remains query-construction/runtime-import verification only; no PostgreSQL-backed workflow execution or approval transaction was run.

## Stage 10 migration dependency
- The WorkflowApproval nullability changes require a reviewed Alembic migration for any database already created from an earlier schema. They are reflected in ORM metadata but must not be applied to a live database until the baseline/schema-drift strategy and migration tests are complete.


## Stage 11 – notification tenant boundary and async-session safety
- Added tenant-scoped user and notification loaders to `NotificationService`; recipient lookups now require an active user belonging to the service tenant.
- Scoped notification-batch retrieval by tenant and validated every batch recipient against the tenant before persisting the batch. Duplicate recipient IDs are normalized.
- Scoped email/SMS recipient lookups and push-subscription resolution through the tenant-owned user record. Notification preference and subscription APIs now validate user tenant membership before reading or mutating user-linked rows (these child tables are keyed by globally unique user IDs and do not carry their own tenant column).
- Replaced direct notification `db.get()` calls with tenant-scoped selects. User notification lists, unread counts, and history filters validate tenant membership.
- Removed fire-and-forget `asyncio.create_task()` calls that reused the request-scoped `AsyncSession` after the request could finish. Notifications and batches remain pending/queued until a durable post-commit outbox/worker is implemented; no false delivered count is recorded.
- Added `backend/tests/test_notification_tenant_scoping.py` for tenant-filter SQL construction, model ownership, and the no-request-session-background-task invariant.

## Stage 11 verification and limitations
- `notification_service.py` bytecode compilation passed.
- Full backend Python AST parse passed for 87/87 files before adding the new regression test; rerun after test addition is required.
- NotificationService import passed with test-only environment variables and a Stripe stub.
- Focused isolated pytest regression module: 3 passed with one Pydantic deprecation warning. The repository-wide suite was not run because its global test conftest imports unavailable `python-jose` through `app.main`. No live PostgreSQL, delivery provider, worker, or end-to-end notification test was run.
- Important behavior limitation: actual notification delivery is deliberately deferred. A durable outbox and worker with a fresh DB session per job are required before enabling delivery in production.

## Stage 12 — 2026-11-20

- Hardened purchase-service foreign-key lookups using tenant-scoped queries and soft-delete filters.
- Replaced the invalid `update_stock_quantity` call in receipt processing with the central InventoryService stock-move lifecycle (create → confirm → process).
- Added required receiving warehouse/location checks for stockable goods and receipt-line/order-line relationship validation.
- Fixed duplicate `tenant_id` parameter in `cancel_stock_move` discovered in Stage 11 source.
- Verification: 85/85 Python files parsed with AST; no direct `db.get()` remains in PurchaseService. Runtime import blocked by missing local `stripe` package; no PostgreSQL or end-to-end tests performed.
