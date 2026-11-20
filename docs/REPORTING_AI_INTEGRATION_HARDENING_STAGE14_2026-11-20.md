# Nexus ERP – Stage 14: Reporting, AI Session Isolation & Accounting Integration

Date: 2026-11-20

## Scope

This stage hardens reporting and AI conversation boundaries, corrects warehouse movement calculations, and adds duplicate-posting guards to accounting integrations. It is a local working-copy change only; no production deployment or database mutation was performed.

## Reporting changes

- `ReportingService` now rejects a missing tenant ID and provides tenant-scoped record resolution for referenced records.
- Account, customer, sales-order, product, warehouse, and product-category lookups used by reports are resolved within the active tenant rather than using unscoped `db.get()` calls.
- Invoice, invoice-line, and stock-move reporting queries exclude soft-deleted records and constrain the relevant tenant.
- Warehouse/category/product report filters are checked against the active tenant; foreign or missing IDs fail rather than silently returning misleading data.
- Stock valuation and slow-moving queries eagerly load product categories to avoid implicit async lazy-loading.
- Stock quantity valuation now treats inbound/outbound movements, adjustments, and inter-warehouse transfers according to source/destination warehouse semantics. Internal transfers are neutral in company-wide stock totals.
- Stock movement analysis no longer counts internal transfers as company-wide stock-outs; warehouse-specific transfers are classified by direction.
- Custom report builder now rejects unsupported multi-source, filter, grouping, and sorting requests instead of silently ignoring them. It enforces an allowlist of reportable fields, a bounded row limit, and scalar ORM result projection.
- The low-stock endpoint no longer silently ignores a supplied warehouse filter; it validates the warehouse and clearly reports that warehouse-specific low-stock calculation is not implemented.
- Reports API now requires explicit `reports.all.view`, `reports.all.export`, or `reports.all.schedule` permissions according to operation.

## AI changes

- Chatbot session retrieval now requires matching session ID, owner user ID, and tenant ID, and excludes soft-deleted sessions.
- Message processing and streaming validate the session against the active tenant before reading history or storing messages.
- Chat session listing excludes soft-deleted sessions.
- The chatbot service imports `selectinload` explicitly; previously the session query referenced it without importing it.
- The parallel AssistantService session APIs now also require tenant scope for retrieval, history, and session deactivation.
- Chatbot-generated data actions are now allowlisted by the caller using the user’s underlying inventory, sales, purchase, or accounting read permission; an AI chat permission alone does not authorize access to every module.
- Quick-query endpoints now enforce the relevant report/inventory/sales/purchase permissions before returning their data.

## Accounting integration changes

- Added tenant-scoped lookup for existing source journal entries.
- Stock-move and manufacturing accounting integrations return an existing source entry instead of creating another entry on repeated invocation.
- Sales invoice, sale-order COGS, goods receipt, and vendor-bill integrations now also check for an existing source entry before attempting creation.
- Stock movement accounting reloads the source move inside tenant scope and requires it to be completed.
- Manufacturing accounting loads material and finished lines explicitly and checks that the generated journal lines balance before posting.
- Stock movement accounting also refuses unbalanced generated journal lines.

## Important limitations / follow-up

- The source-entry lookup is an application-level idempotency guard, not a concurrency-proof guarantee. A database uniqueness constraint on `(tenant_id, source_model, source_id)` (with appropriate nullable semantics) and transaction-level concurrency tests are still required.
- The custom report builder intentionally exposes only three primary sources and a narrow field allowlist. Filters, grouping, sorting, and cross-source joins remain unimplemented and are now rejected explicitly.
- Warehouse-specific low-stock calculation remains unimplemented and is now rejected explicitly rather than returning a misleading global result.
- FIFO/LIFO valuation still falls back to average cost in the existing implementation and must not be represented as a fully implemented FIFO/LIFO valuation method.
- Several cash-flow report sections remain placeholders/simplifications in the existing service.
- Streaming chat currently returns model-generated text only; it does not execute the structured read actions. This distinction should remain explicit until streaming actions receive the same permission gate and audit trail.
- No live PostgreSQL, migration, concurrency, or end-to-end workflow tests were run in this stage.

## Validation performed

- Python AST parsing across backend source files: 88/88 passed.
- Python bytecode compilation across `backend/app`: passed.
- Integration service import smoke test: passed.
- Import smoke tests for reporting/AI modules and API routers were blocked by environment setup: missing `stripe` dependency and required `DATABASE_URL` / `SECRET_KEY` settings. This is an environment limitation, not a passed runtime test.
- No production database or deployment was touched.
