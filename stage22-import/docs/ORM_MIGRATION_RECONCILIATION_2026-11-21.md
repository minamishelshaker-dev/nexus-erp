# Nexus ERP — ORM / Migration Reconciliation (2026-11-21)

Branch: `integration/stage23-safety-patch`  
Scope: static comparison of the 13 SQLAlchemy model modules under `stage22-import/backend/app/models/` against all current Alembic revision files under `stage22-import/backend/alembic/versions/`.

## Findings

- SQLAlchemy ORM tables declared: **102**
- Tables explicitly created by current Alembic revisions (unique names): **48**
- ORM tables with no matching `op.create_table()` in current revisions: **68**
- Migration-created names not declared as ORM tables: **14**

This is a static name-level inventory. It does not certify column, type, nullability, default, index, foreign-key, check-constraint, enum, RLS, or tenant-isolation parity.

## ORM tables missing from current migrations (68)

```text
activity_comments
activity_feeds
activity_subscriptions
adjustment_lines
ai_model_configs
anomaly_detections
bom_operations
chat_messages
chat_sessions
companies
company_branches
consolidation_group_companies
consolidation_groups
contacts
customer_addresses
customer_interactions
customers
entity_activities
entity_versions
fiscal_periods
fiscal_years
forecasts
inter_company_transaction_items
inter_company_transactions
inventory_adjustments
invoice_lines
invoices
mo_finishes
mo_lines
mo_operations
notification_batches
notification_preferences
notification_subscriptions
notification_templates
notifications
ocr_results
payment_invoices
payment_reconciliations
payments
permissions
product_categories
product_recommendations
production_plan_lines
production_plans
quotation_lines
quotations
receipt_lines
receipts
role_permissions
routing_steps
routings
sale_order_lines
sale_orders
sales_teams
stock_locations
stock_lots
stock_quantities
stock_valuations
supplier_infos
unit_of_measures
user_activity_logs
user_sessions
workflow_approvals
workflow_executions
workflow_step_executions
workflow_steps
workflow_templates
workflows
```

## Migration-created names requiring explicit disposition (14)

These are present in migration code but are not declared under the same table name in the current ORM metadata. Do not drop or rename them automatically; determine whether each is legacy, intentionally SQL-only, or a naming mismatch requiring a controlled data-preserving migration.

```text
attendance_records
categories
chart_of_accounts
employees
journal_entry_lines
partner_contacts
project_tasks
projects
purchase_requisitions
sales_order_lines
sales_orders
sales_quotations
timesheets
```

## Important naming collisions / likely legacy mappings

Several names look semantically related but are not equivalent by name alone (for example `categories` vs `product_categories`, `partner_contacts` vs `contacts`, `sales_orders` vs `sale_orders`, and `sales_quotations` vs `quotations`). These require a column-level and foreign-key comparison before any migration is authored.

## Deployment and database safety gate

- The connected Supabase project `Nexus ERP` is healthy, but the `public` schema currently reports no tables and no recorded migrations.
- The API Vercel project currently has no environment variables configured. The backend settings require `DATABASE_URL` and `SECRET_KEY`.
- Therefore, do not apply the existing migration chain to the live Supabase project and do not claim the API is operational.
- Do not rotate database credentials merely to unblock deployment. Obtain a secure connection credential through the project's supported secret-management path, then configure it as a Vercel secret without exposing it in source control or chat.

## Next engineering steps

1. Compare every ORM table's columns and constraints against the legacy migration-created schema.
2. Resolve the 14 SQL-only/legacy names and any same-domain naming collisions.
3. Generate explicit, ordered, reviewable Alembic revisions; do not use an unreviewed blanket `metadata.create_all()` migration.
4. Extend CI to fail on missing ORM tables **and** missing/incorrect columns, constraints, indexes, enum definitions, and tenant scoping.
5. Re-run the disposable PostgreSQL migration test and ORM inventory.
6. Only after the full parity gate passes, review and apply migrations to the dedicated Nexus ERP Supabase project.
