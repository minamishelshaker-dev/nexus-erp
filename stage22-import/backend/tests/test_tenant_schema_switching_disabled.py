"""Regression checks for the supported row-level tenant model."""
import pytest

from app.core.database import DatabaseManager, init_models
from app.core.tenant import AsyncTenantContextManager, TenantManager


def test_schema_switching_and_schema_lifecycle_are_disabled():
    manager = DatabaseManager()
    with pytest.raises(RuntimeError, match="Schema-based tenant switching is disabled"):
        manager.set_tenant("tenant_schema")

    with pytest.raises(RuntimeError, match="Per-tenant schema creation is disabled"):
        import asyncio
        asyncio.run(manager.create_tenant_schema("tenant_schema"))

    with pytest.raises(RuntimeError, match="Per-tenant schema deletion is disabled"):
        import asyncio
        asyncio.run(manager.drop_tenant_schema("tenant_schema"))

    with pytest.raises(RuntimeError, match="Runtime create_all is disabled"):
        import asyncio
        asyncio.run(init_models())


@pytest.mark.asyncio
async def test_async_tenant_context_never_executes_schema_sql():
    class FakeSession:
        def __init__(self):
            self.executed = []

        async def execute(self, statement):
            self.executed.append(str(statement))
            raise AssertionError("Tenant context must not issue schema SQL")

    session = FakeSession()
    previous = TenantManager.get_context()
    manager = AsyncTenantContextManager(
        tenant_id="00000000-0000-0000-0000-000000000001",
        tenant_slug="test-tenant",
        tenant_subdomain="test",
        db=session,
        schema_name='unsafe"; DROP SCHEMA public CASCADE; --',
    )

    async with manager:
        assert TenantManager.get_tenant_id() is not None

    assert session.executed == []
    assert TenantManager.get_context() == previous
