# Nexus ERP — Tenant ownership review of mapped tables
Date: 2026-11-20

## Purpose

A table without a direct `tenant_id` column is not automatically a vulnerability: child and junction tables may inherit ownership through a parent row. However, every such relationship must be enforced in queries and database constraints. This inventory is a review queue, not a claim that all listed tables are exploitable.

## Current ORM metadata finding

The SQLAlchemy metadata contains 102 tables. **20 tables do not declare a direct `tenant_id` column.** They need an explicit ownership classification before enabling tenant middleware or considering production readiness.

| Table | Candidate ownership path / classification to verify |
|---|---|
| `activity_subscriptions` | user_id and subscribed entity reference; enforce tenant ownership of both |
| `chat_messages` | session_id → chat_sessions; verify session tenant and message access |
| `company_branches` | company_id → companies; verify company tenant |
| `consolidation_group_companies` | group_id and company_id; both parents must belong to the same tenant |
| `currencies` | likely global reference data; confirm global read-only policy |
| `inter_company_transaction_items` | transaction_id → inter-company transaction; verify parent tenant |
| `notification_preferences` | user_id → users; verify user tenant |
| `notification_subscriptions` | user_id → users; verify user tenant |
| `permissions` | likely global RBAC catalog; restrict writes to platform administration |
| `plans` | likely global SaaS catalog; restrict writes to platform administration |
| `role_permissions` | role_id → roles and permission_id → permissions; verify role tenant and global permission semantics |
| `supplier_infos` | product_id and partner_id; verify both belong to the same tenant |
| `tenants` | tenant root; global administration only |
| `unit_of_measures` | likely global or tenant-customizable reference data; decide and enforce one model |
| `user_activity_logs` | user_id → users; verify user tenant and access controls |
| `user_roles` | user_id and role_id; verify both belong to same tenant |
| `user_sessions` | user_id → users; verify user tenant and session revocation |
| `workflow_approvals` | execution_id / step_id / approver_id; verify all related records share tenant |
| `workflow_step_executions` | execution_id / step_id; verify parent workflow execution and step tenant |
| `workflow_steps` | workflow_id; verify workflow tenant and all referenced approval/execution relationships |

## Required controls

1. Add tenant-consistency validation to every create/update path for child and junction rows.
2. Prefer composite foreign keys where practical (for example, `(tenant_id, parent_id)`) so cross-tenant parent references cannot be stored.
3. Ensure every read/update/delete path scopes through the owning tenant, not only the child table's ID.
4. Decide whether currencies, permissions, plans, and units of measure are global reference catalogs or tenant-managed data. Document who may mutate them.
5. Add cross-tenant negative tests for every child/junction relationship, including attempts to attach a row to a parent from another tenant.
6. Only then decide whether PostgreSQL RLS is part of the defense-in-depth design. If the backend uses a privileged server-side role, application-level checks remain mandatory and direct client access must not bypass them.

## Status

No production migration or database write was performed during this review. The Supabase Nexus ERP project remains untouched.
