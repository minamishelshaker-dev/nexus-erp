# Tenant access review – Stage 9

## Scope
This pass verified that legacy PostgreSQL schema switching is disabled throughout the application and inventoried direct primary-key ORM reads for follow-up tenant-boundary review.

## Confirmed code changes
- `DatabaseManager` no longer stores a mutable tenant schema or changes a pooled connection's `search_path`.
- `set_tenant`, `create_tenant_schema`, and `drop_tenant_schema` now reject use explicitly.
- `init_models()` no longer runs `Base.metadata.create_all()` at runtime; Alembic is the only supported schema-change path.
- `AsyncTenantContextManager` no longer executes schema SQL.
- `TenantSchemaMiddleware` is retained as a no-op compatibility class and cannot mutate database state.

## Static verification
A recursive scan of `backend/app` and `backend/alembic` found no remaining occurrences of:
- `SET search_path`
- `CREATE SCHEMA`
- `DROP SCHEMA`
- `create_all()`

Runtime smoke checks confirmed the disabled APIs fail closed and that an async tenant context containing a hostile legacy `schema_name` does not execute SQL. This is not a PostgreSQL integration test.

## Direct ORM primary-key read inventory
AST scan identified 58 `db.get()` / `session.get()` call sites in service code. These are listed as review candidates, not all classified as vulnerabilities. A call may be safe if it targets global reference data or its parent record has already been tenant-scoped; that must be confirmed from the full call chain.

| Service | Candidate reads |
|---|---:|
| `manufacturing_service.py` | 4 |
| `workflow_service.py` | 13 |
| `notification_service.py` | 7 |
| `inventory_service.py` | 1 |
| `purchase_service.py` | 11 |
| `reporting_service.py` | 4 |
| `sales_service.py` | 4 |
| `ai/forecasting_service.py` | 3 |
| `ai/anomaly_service.py` | 11 |
| `ai/anomaly_detection.py` | 4 |
| **Total** | **58** |

## Required next steps
1. Classify every read by model ownership (tenant-owned vs global) and identify its caller/API/background task.
2. Add tenant-scoped loaders for tenant-owned records and validate foreign-key references against the same tenant.
3. Add two-tenant PostgreSQL tests that attempt cross-tenant reads and writes through HTTP endpoints and background jobs.
4. Complete the user-to-organization membership model before implementing shared Nexus SSO across ERP and Legal Nexus.
5. Validate tenant filters in raw SQL, reports, notifications, exports, and AI services; ORM primary-key scans alone are insufficient.

## Release status
Not production-ready. No live PostgreSQL migration, API isolation test, or cross-tenant concurrency test was executed in this stage.

## Stage 10 follow-up – workflow service
The 13 direct primary-key reads previously inventoried in `workflow_service.py` have been replaced by tenant-scoped loaders. Approval records are scoped through their tenant-owned execution parent because the approval model intentionally has no `tenant_id` field. A separate review found the model's pending-approval fields were incorrectly non-nullable despite service code creating pending approvals; ORM nullability has been corrected. See `WORKFLOW_TENANT_REVIEW_STAGE10.md`.

The remaining 45 direct primary-key read candidates in other services still require individual classification and repair. This number is a static inventory count, not a count of confirmed vulnerabilities.
