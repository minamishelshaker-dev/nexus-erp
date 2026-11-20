"""Regression tests for tenant scoping in workflow and approval lookups."""
import pytest
from sqlalchemy.dialects import postgresql

from app.services.workflow_service import WorkflowService
from app.models.workflow import Workflow, WorkflowExecution, WorkflowApproval


class _Result:
    def scalar_one_or_none(self):
        return None


class _CaptureSession:
    def __init__(self):
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return _Result()


def _compiled(statement):
    return str(statement.compile(dialect=postgresql.dialect()))


@pytest.mark.asyncio
async def test_workflow_execution_and_approval_loaders_are_tenant_scoped():
    db = _CaptureSession()
    tenant_id = "00000000-0000-0000-0000-000000000001"
    service = WorkflowService(db, tenant_id)

    await service._get_tenant_workflow("00000000-0000-0000-0000-000000000002")
    await service._get_tenant_execution("00000000-0000-0000-0000-000000000003")
    await service._get_tenant_approval("00000000-0000-0000-0000-000000000004")

    assert len(db.statements) == 3
    compiled = [_compiled(statement) for statement in db.statements]
    for sql in compiled:
        assert "tenant_id" in sql
    assert "JOIN workflow_executions" in compiled[2]


def test_workflow_approval_is_scoped_through_execution_not_nonexistent_tenant_column():
    assert hasattr(Workflow, "tenant_id")
    assert hasattr(WorkflowExecution, "tenant_id")
    assert not hasattr(WorkflowApproval, "tenant_id")
    assert WorkflowApproval.__table__.c.decision.nullable is True
    assert WorkflowApproval.__table__.c.step_id.nullable is True
    assert WorkflowApproval.__table__.c.decided_at.nullable is True
    assert "self.db.get(" not in open(__file__.replace(
        "tests/test_workflow_tenant_scoping.py", "app/services/workflow_service.py"
    ), encoding="utf-8").read()
