# Identity & Access Schema Reconciliation — 2026-11-21

## Scope and evidence

This review compares the current SQLAlchemy identity models with the committed initial migration on branch `integration/stage23-safety-patch`.

Reviewed files:
- `stage22-import/backend/app/models/base.py`
- `stage22-import/backend/app/models/user.py`
- `stage22-import/backend/alembic/versions/001_initial_schema.py`
- `stage22-import/backend/alembic/versions/add_missing_orm_tables_68.py`

This is a source-level reconciliation, not a live-database inspection and not approval to mutate production.

## Executive finding

The initial migration's identity schema is a legacy design and is materially different from the current ORM model. The most important differences are semantic, not merely missing columns:

1. User activation and verification are represented differently.
2. Tenant ownership changes from nullable/global uniqueness to mandatory tenant-scoped identity.
3. Role permissions move from a JSON array on `roles` to normalized `permissions` and `role_permissions` relations.
4. User-role assignment gains its own identity, audit, assignment actor, and expiry metadata.
5. The current user model introduces department linkage, account security state, localization, OAuth, and login telemetry.

A blind Alembic autogenerate migration is unsafe here. In particular, dropping `roles.permissions`, changing tenant nullability, or changing uniqueness before data mapping could cause irreversible access-control or tenant-isolation failures.

## Detailed mapping

### 1. users

| Legacy initial migration | Current ORM | Reconciliation |
|---|---|---|
| `email` unique globally | `email` plus unique `(email, tenant_id)` | Preserve values; assess duplicate emails across tenants before changing uniqueness |
| `username` varchar(100), globally unique | varchar(50), unique `(username, tenant_id)` | Check values longer than 50 and tenant-local duplicates first |
| `first_name`, `last_name` nullable | both non-null | Backfill nulls before enforcing NOT NULL; do not invent names silently |
| `is_active` boolean | `status` enum | Map true → active; false → inactive, after confirming existing application semantics |
| `is_verified` boolean | `email_verified` | Candidate mapping; validate whether legacy verification meant email verification |
| `last_login` | `last_login_at` | Rename/copy after checking timestamp type and application references |
| `tenant_id` nullable | inherited `tenant_id` NOT NULL with FK to tenants | Critical: every existing user needs an explicit tenant assignment before enforcement |
| no `full_name` | `full_name` nullable | Add nullable; optional backfill from first/last name |
| no `mobile`, `job_title`, `department_id` | current fields | Add only after department table and FK lifecycle are resolved |
| no `is_staff` | current boolean | Add with reviewed default |
| no phone verification / 2FA fields | `phone_verified`, `two_factor_enabled`, `two_factor_secret` | Add with secure defaults; never fabricate secrets |
| no locale fields | `language`, `timezone` | Add with defaults only after confirming product defaults |
| `preferences` JSONB | `preferences` JSONB | Retain and validate shape; do not overwrite |
| no OAuth fields | `oauth_provider`, `oauth_provider_id` | Add nullable |
| no login telemetry | `last_login_ip`, `login_count`, `failed_login_count`, `locked_until` | Add with safe defaults/nullability |
| no password lifecycle fields | `password_changed_at`, `must_change_password` | Add with reviewed security policy |
| no `password_hash` length constraint | current check requires length >= 60 | Validate existing hashes before adding; legacy non-bcrypt hashes may be shorter or use other formats |

Important model detail: current `User.is_active` is a Python property derived from `status == ACTIVE` and `is_deleted == false`; it is not a mapped database column. Do not recreate the legacy `is_active` column as the current canonical field.

### 2. roles

| Legacy initial migration | Current ORM | Reconciliation |
|---|---|---|
| globally unique `name` and `code` | tenant-scoped unique `code`; `name` not declared unique | Check cross-tenant duplicates and decide system-role treatment |
| `permissions` JSONB array | normalized `permissions` and `role_permissions` | Requires explicit JSON-to-permission catalog mapping; preserve source JSON until every entry is mapped and verified |
| no `is_active` | `is_active` boolean | Add with reviewed default |
| no `parent_id` | self-referential `parent_id` | Add nullable; validate no cycles |
| no `priority` | `priority` integer | Add with default after policy confirmation |
| `tenant_id` nullable | inherited NOT NULL tenant FK | Assign tenant or explicitly classify global/system roles before enforcement |

### 3. user_roles

Legacy table:
- composite primary key `(user_id, role_id)`
- `assigned_at`
- no assignment actor or expiry

Current ORM association model:
- inherited UUID `id`, timestamps, soft-delete and audit columns
- `user_id`, `role_id`, `assigned_by_id`, `assigned_at`, `expires_at`
- unique constraint on `(user_id, role_id)`

Reconciliation:
- preserve every existing assignment;
- introduce UUID IDs deterministically or via generated UUIDs;
- preserve the old composite uniqueness invariant;
- add nullable `assigned_by_id` and `expires_at`;
- ensure the two FKs and the actor FK are valid;
- avoid duplicate active assignments before creating the unique constraint.

### 4. permissions and role_permissions

The current ORM defines a normalized permission catalog with:
- globally unique `code`;
- `name`, `description`, `module`, `action`, `resource`;
- enum `scope` and JSONB `conditions`.

Role grants are stored through `role_permissions`, unique by `(role_id, permission_id)`.

The migration chain creates `permissions` in the later ORM inventory migration, but this alone does not migrate the legacy `roles.permissions` JSON array. A data migration must:
1. inventory all distinct legacy permission strings and JSON shapes;
2. map them to a reviewed canonical permission catalog;
3. report unknown/unmapped values and stop if any remain;
4. insert role-permission links idempotently;
5. compare effective grants before/after for every role;
6. retain the legacy JSON field until verification and an explicit deprecation decision.

## Tenant isolation and data integrity blockers

- Legacy `users.tenant_id` and `roles.tenant_id` are nullable; current TenantMixin declares them non-null and references `tenants.id`.
- The initial migration makes email, username, role name, and role code globally unique; current models use tenant-aware uniqueness for user email/username and role code.
- The current `User.department_id` references `departments.id`; the reviewed initial migration excerpt does not create a departments table. The full migration chain and the actual department model must be reconciled before introducing this FK.
- The current `User` model's password length check may reject existing legacy credentials. Verify hash algorithms and lengths; do not force password resets or rewrite hashes without a tested authentication compatibility plan.
- The initial `user_roles` table is a pure association table; current ORM treats it as a full entity. ORM metadata parity alone does not migrate its existing records safely.

## Safe migration sequence (not yet executed)

1. Take and verify a restorable backup of the target database.
2. Inventory real row counts, nulls, duplicate keys, tenant assignments, hash formats, role permission JSON shapes, and existing FK dependencies.
3. Create a compatibility migration that is additive only: introduce new nullable columns/tables/indexes without dropping or renaming legacy data.
4. Backfill user status and verification fields with explicit mapping rules; produce exception reports for null names, tenantless users, overlength usernames, and duplicate tenant-scoped keys.
5. Assign tenants using an authoritative mapping. Stop if any account or role remains tenant-ambiguous.
6. Normalize role permissions into the permission catalog and join table; compare effective access grants.
7. Expand user-role rows to the current association entity shape while preserving assignment semantics.
8. Add constraints and NOT NULL only after preflight queries prove all rows comply.
9. Deploy application code that reads the new canonical fields; retain compatibility reads during a controlled transition if rolling deployments require them.
10. Only in a later, separately reviewed migration remove legacy columns/tables after production verification and backup-retention requirements are met.

## Required tests before any production migration

- Fresh install from an empty PostgreSQL database.
- Upgrade from the exact legacy schema with representative data.
- Cross-tenant duplicate email/username and role-code cases.
- Tenantless user/role handling (must fail closed, not silently attach to an arbitrary tenant).
- Legacy `is_active` / `is_verified` / `last_login` mapping.
- Role JSON permission normalization with unknown permissions causing a hard stop.
- Effective permission equivalence before/after migration.
- User-role assignment preservation and uniqueness.
- Password hash compatibility and login verification.
- Department FK creation and the users/departments FK-cycle handling.
- Upgrade idempotency and backup restore rehearsal.

## Decision

**Do not apply an identity migration to the live Supabase project yet.** The safe next engineering task is to inspect the complete legacy schema and actual tenant/user/role data on an isolated disposable PostgreSQL instance, then build an additive, reversible data migration with preflight assertions. No production database was changed as part of this review.


## Follow-up inspection: departments

The current department model was located in `stage22-import/backend/app/models/reference.py` (not a standalone `department.py`). It inherits `BaseModel` and `TenantMixin`, has a tenant/code unique constraint, and defines a self-referencing parent FK plus `manager_id → users.id`. The user model separately defines `department_id → departments.id`. This confirms a bidirectional table dependency. The migration must create both tables first and add one side of the FK cycle in a later ALTER step; do not rely on automatic FK ordering alone.
