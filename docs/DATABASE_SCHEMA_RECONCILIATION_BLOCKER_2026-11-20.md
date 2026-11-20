# Nexus ERP — Stage 22 database schema reconciliation addendum
Date: 2026-11-20

## Result: critical schema mismatch confirmed

The previous review correctly flagged schema drift as unresolved. A deeper offline comparison now quantifies it.

### Method
- Loaded the SQLAlchemy model registry from `backend/app/models` with placeholder local-only environment variables (no network connection).
- Counted actual `Base.metadata.tables`.
- Generated the complete Alembic offline upgrade script with `alembic upgrade head --sql`; this did not connect to or modify any database.
- Parsed the table names from both the generated Alembic SQL and the Supabase snapshot.

### Findings

| Source | Tables |
|---|---:|
| SQLAlchemy ORM metadata | 102 |
| Alembic offline upgrade output | 40 (including `alembic_version`) |
| Supabase Stage 21 SQL snapshot | 40 (including migration-managed tables) |

The Alembic output and Supabase snapshot are effectively the same 40-table baseline. Comparing the 102 ORM tables with the 40 SQL tables yields:
- **77 ORM tables missing** from the migration output.
- **15 SQL tables** not represented by the current ORM metadata (some may be legacy or deliberately separate, but each requires an explicit disposition).

Examples of ORM tables absent from the migration output include `accounts`, `companies`, `customers`, `invoices`, `journal_items`, `notifications`, `purchase_invoices`, `stock_quantities`, `workflows`, and `user_sessions`.

### Consequence

**Do not apply the current migration chain to the Nexus ERP Supabase project and do not deploy the backend against a fresh database yet.** A successful Alembic offline generation and a single migration head do not mean the ERP schema is complete. Large portions of the application's mapped data model would not be created.

The current cloud project remains untouched: no application migration was applied.

### Required correction path

1. Establish a canonical schema inventory: ORM tables, migration-created tables, and any intentional legacy/managed tables.
2. Determine whether the 77 missing tables are still required, deprecated, or intentionally out of scope. Do not blindly generate tables from ORM metadata without reviewing dependencies, indexes, constraints, defaults, and tenant ownership.
3. Build additive Alembic revisions for approved missing tables and constraints; explicitly document legacy SQL-only tables.
4. Re-run offline SQL generation and compare table/column/index/foreign-key definitions against ORM metadata.
5. Apply the corrected chain only to a disposable PostgreSQL database first, then verify all expected tables and tenant isolation before touching the cloud project.

This is a production-blocking issue, not a cosmetic documentation gap.
