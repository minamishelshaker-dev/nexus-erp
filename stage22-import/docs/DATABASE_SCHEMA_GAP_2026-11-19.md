# Nexus ERP – Database Schema Gap Report (2026-11-19)

## Current verified ORM registry

- All model modules are now imported into one declarative registry (`app.models.base.Base`).
- `Base.metadata` contains **98 tables**.
- SQLAlchemy configures **98 mapped classes** successfully.
- `configure_mappers()` completes without warnings in the current environment.
- The sales invoice table (`invoices`) and SaaS billing invoice table (`billing_invoices`) are now distinct, avoiding the previous duplicate-table declaration.
- Tenant-scoped models inherit a `tenant_id` foreign key to `tenants.id` through `TenantMixin`.

## Alembic migration coverage

The hand-written migration chain currently contains:

- `001_initial_schema`: 30 `create_table` calls.
- `add_tenant_billing`: 5 `create_table` calls.
- Total: **35 table creation calls**.

A name comparison against the 98-table ORM metadata shows:

- **77 ORM tables are not created by the current migrations.**
- **14 tables created by migrations do not exist in the current ORM metadata under those names.**
- Only 21 table names overlap.

This is a schema-history mismatch, not a small missing-index issue. The offline SQL renderer now completes after removing the migration's runtime `information_schema` loop, but successful SQL rendering does **not** mean the generated migration chain builds the complete current ORM schema.

## Additional schema/domain corrections in this stage

- Renamed the SaaS billing invoice ORM model/table to `BillingInvoice` / `billing_invoices`; the sales invoice remains `Invoice` / `invoices`.
- Updated the billing API and billing migration to use `billing_invoices`.
- Updated accounting indexes that referred to a non-existent `company_id` field to use the existing tenant key. This expresses tenant-level uniqueness in the current model; company-level accounting separation still needs an explicit company model/key design.
- Corrected the anomaly detection date index to use the inherited `created_at` field.
- Corrected the User–Role association joins to disambiguate the additional `assigned_by_id` foreign key.
- Corrected analytic line relationships to point to `AnalyticAccount` rather than `Account`.
- Corrected self-referential product variant and activity/comment relationships.
- Added missing explicit purchase-order ↔ purchase-invoice linkage; receipt stock moves remain linked through receipt lines because no direct receipt foreign key exists on `StockMove`.
- Removed invalid CRM customer relationships to sales documents because those documents currently reference `Partner`, not `Customer`.
- Removed the invalid sale-order ↔ stock-move relationship because the current stock-move model has no `sale_order_id` foreign key.
- Updated `BaseModel.to_dict()` to resolve ORM property names separately from physical database column names, including the reserved SQL column `metadata` exposed as `metadata_json` on models.

## Required next database work

1. Decide whether this repository should retain its legacy migration history or establish a clean baseline for a new development database.
2. Compare every existing database table, column, index, enum, constraint, and foreign key against the current 98-table metadata.
3. Build a reviewed forward migration plan for the 77 missing model tables and the 14 legacy-only tables. Do not blindly drop or rename legacy tables; preserve data or provide explicit migration mappings.
4. Test fresh install and upgrade-from-existing against disposable PostgreSQL databases, including downgrade/rollback where safe.
5. Add data backfills and `NOT NULL` / tenant foreign-key enforcement only after tenant ownership of existing rows is deterministically assigned.

## Verification limits

- No PostgreSQL server was available; no live database upgrade, downgrade, data migration, or runtime SQL query was run.
- `alembic upgrade head --sql` generated static PostgreSQL SQL successfully; this is an offline render only.
- The focused pytest module could not start because the environment lacks the declared `python-jose` dependency, imported by the existing global `tests/conftest.py`. Direct SQLAlchemy registry and mapper checks passed.
- No deployment or production database change was performed.

## Column-level drift in same-name tables

A static comparison of `op.create_table()` columns with current ORM columns also found substantial drift in the overlapping table names. Representative results:

| Table | ORM columns missing from migration | Legacy migration columns absent from ORM |
|---|---:|---:|
| `users` | 24 | 3 |
| `products` | 58 | 6 |
| `stock_moves` | 23 | 7 |
| `purchase_orders` | 25 | 3 |
| `journal_entries` | 20 | 3 |
| `leads` | 24 | 4 |
| `opportunities` | 23 | 4 |
| `manufacturing_orders` | 22 | 4 |
| `warehouses` | 16 | 1 |
| `work_centers` | 17 | 2 |
| `bills_of_materials` | 17 | 3 |
| `purchase_order_lines` | 17 | 2 |
| `partners` | 8 | 13 |
| `roles` | 8 | 1 |
| `bom_lines` | 16 | 1 |
| `audit_logs` | 5 | 0 |

The migration history is therefore not just missing 77 tables: many of the 21 same-name tables have materially different columns. For example, the legacy `products` migration contains generic flags and a single `uom_name`, while the current ORM includes detailed sale/purchase/stock settings, multiple UOM references, variants, valuation fields, and accounting links. A safe upgrade requires explicit data mapping and cannot be generated as a blind `create_all()` call or a simple add-column script.
