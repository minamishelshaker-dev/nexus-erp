# Nexus ERP — Full ORM / Alembic table inventory

Date: 2026-11-20
Branch: `integration/stage23-safety-patch`
Scope: offline source inspection only. No database was contacted or modified.

## Method

- Enumerated explicit `__tablename__` declarations in all 13 SQLAlchemy model modules under `backend/app/models`.
- Enumerated `op.create_table(...)` calls across all six Alembic revision files.
- Cross-checked the counts against `docs/DATABASE_SCHEMA_RECONCILIATION_BLOCKER_2026-11-20.md`, which records the ORM metadata count and offline Alembic SQL count.

## Result

| Inventory | Count |
|---|---:|
| ORM model tables | 102 |
| Tables explicitly created by the six Alembic revisions | 39 |
| Alembic offline SQL tables, including `alembic_version` | 40 |
| ORM tables absent from explicit migration create_table calls | 77 |
| SQL-only application tables absent from ORM declarations | 14 |
| Additional migration bookkeeping table | 1 (`alembic_version`) |

The 77 missing ORM tables are a confirmed migration-completeness blocker. The 14 SQL-only tables are not automatically errors: each needs a documented classification as legacy, deliberately SQL-managed, renamed, or a model omission.

## ORM tables missing from the current migration chain

- `accounts`
- `activity_comments`
- `activity_feeds`
- `activity_subscriptions`
- `adjustment_lines`
- `ai_model_configs`
- `analytic_accounts`
- `analytic_lines`
- `anomaly_detections`
- `bom_operations`
- `chat_messages`
- `chat_sessions`
- `companies`
- `company_branches`
- `consolidation_group_companies`
- `consolidation_groups`
- `contacts`
- `currencies`
- `customer_addresses`
- `customer_interactions`
- `customers`
- `entity_activities`
- `entity_versions`
- `fiscal_periods`
- `fiscal_years`
- `forecasts`
- `inter_company_transaction_items`
- `inter_company_transactions`
- `inventory_adjustments`
- `invoice_lines`
- `invoices`
- `journal_items`
- `journals`
- `mo_finishes`
- `mo_lines`
- `mo_operations`
- `notification_batches`
- `notification_preferences`
- `notification_subscriptions`
- `notification_templates`
- `notifications`
- `ocr_results`
- `payment_invoices`
- `payment_reconciliations`
- `payments`
- `permissions`
- `product_categories`
- `product_recommendations`
- `production_plan_lines`
- `production_plans`
- `purchase_invoice_lines`
- `purchase_invoices`
- `quotation_lines`
- `quotations`
- `receipt_lines`
- `receipts`
- `reconciliations`
- `role_permissions`
- `routing_steps`
- `routings`
- `sale_order_lines`
- `sale_orders`
- `sales_teams`
- `stock_locations`
- `stock_lots`
- `stock_quantities`
- `stock_valuations`
- `supplier_infos`
- `unit_of_measures`
- `user_activity_logs`
- `user_sessions`
- `workflow_approvals`
- `workflow_executions`
- `workflow_step_executions`
- `workflow_steps`
- `workflow_templates`
- `workflows`

## SQL-created tables without a matching ORM __tablename__

- `attendance_records`
- `categories`
- `chart_of_accounts`
- `employees`
- `journal_entry_lines`
- `partner_contacts`
- `project_tasks`
- `projects`
- `purchase_requisitions`
- `refresh_tokens`
- `sales_order_lines`
- `sales_orders`
- `sales_quotations`
- `timesheets`

## Required reconciliation decisions

For each of the 77 missing tables:
1. Confirm whether the model is active product scope, deprecated, or intentionally deferred.
2. Review every column, server default, enum, unique constraint, foreign key, index, and delete/update rule.
3. Confirm tenant ownership: direct `tenant_id`, inherited ownership through a parent, or explicitly global reference data.
4. Define cross-tenant integrity constraints for child and junction tables where appropriate.
5. Add additive Alembic revisions in dependency order; do not regenerate a blind one-shot schema.
6. Add migration tests against a disposable PostgreSQL database and compare the resulting catalog with ORM metadata.

For each SQL-only table:
1. Identify its consumers and whether it contains production/business data.
2. Decide whether to add an ORM model, preserve it as intentionally SQL-managed, or plan a separately reviewed deprecation.
3. Never drop or rename it solely because it is absent from ORM metadata.

## Release gate

**NO-GO for production migrations and backend deployment until the complete inventory has an approved disposition and a disposable-PostgreSQL migration test passes.** The active Supabase project remains untouched by this inspection.
