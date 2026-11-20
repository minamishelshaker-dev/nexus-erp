# Workflow tenant-boundary review – Stage 10

## Changes
- Tenant-owned workflow definitions are loaded by `(workflow_id, tenant_id, is_deleted=false)`.
- Tenant-owned workflow executions are loaded by `(execution_id, tenant_id, is_deleted=false)`.
- Workflow approvals are child records without their own `tenant_id`; every approval lookup is therefore scoped by joining to its `WorkflowExecution` parent and filtering the parent's `tenant_id`.
- Pending approval listing and approval-completion checks now use the same parent join.
- Workflow execution, exception recovery, continuation, history enrichment, and deactivate/update/activate paths use tenant-scoped loaders.
- Removed the invalid `WorkflowApproval.tenant_id` expression and removed unsupported `tenant_id` constructor values for approval objects.
- `WorkflowApproval.decision`, `step_id`, and `decided_at` now support the actual pending/action approval lifecycle represented by service code.

## Verification
- Query compilation against PostgreSQL dialect passed for workflow, execution, and approval tenant-scoped loaders.
- Mapper configuration passed.
- No direct `self.db.get()` remains in `WorkflowService`.
- No live database transaction or end-to-end workflow was executed.

## Migration note
The approval column nullability changes require an explicit Alembic migration when the schema baseline is established. Do not apply ORM metadata changes directly to a production database.
