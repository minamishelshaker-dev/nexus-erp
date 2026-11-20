"""Regression checks for notification tenant boundaries and session lifecycle."""
import pytest
from sqlalchemy.dialects import postgresql

from app.services.notification_service import NotificationService
from app.models.notification import Notification, NotificationBatch
from app.models.user import User


class _Result:
    def scalar_one_or_none(self):
        return None


class _CaptureSession:
    def __init__(self):
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return _Result()


def _sql(statement):
    return str(statement.compile(dialect=postgresql.dialect()))


@pytest.mark.asyncio
async def test_notification_and_user_loaders_are_tenant_scoped():
    db = _CaptureSession()
    tenant_id = "00000000-0000-0000-0000-000000000001"
    service = NotificationService(db, tenant_id)

    await service._get_tenant_user("00000000-0000-0000-0000-000000000002")
    await service._get_tenant_notification("00000000-0000-0000-0000-000000000003")

    assert len(db.statements) == 2
    user_sql, notification_sql = map(_sql, db.statements)
    assert "users.tenant_id" in user_sql
    assert "users.is_deleted" in user_sql
    assert "notifications.tenant_id" in notification_sql


def test_notification_service_does_not_spawn_tasks_with_request_session():
    from importlib.util import find_spec
    from pathlib import Path

    module_spec = find_spec("app.services.notification_service")
    assert module_spec and module_spec.origin
    content = Path(module_spec.origin).read_text(encoding="utf-8")
    assert "self.db.get(" not in content
    assert "asyncio.create_task(" not in content


def test_notification_models_keep_tenant_ownership_on_primary_records():
    assert hasattr(Notification, "tenant_id")
    assert hasattr(NotificationBatch, "tenant_id")
    assert hasattr(User, "tenant_id")
