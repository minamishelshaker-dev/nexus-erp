"""Security regression tests for tenant-scoped billing endpoints."""

import inspect
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.params import Depends

from app.api.v1.endpoints import billing
from app.core.security import get_current_superuser


TENANT_A = UUID("00000000-0000-0000-0000-000000000001")
TENANT_B = UUID("00000000-0000-0000-0000-000000000002")


def test_billing_tenant_guard_allows_the_authenticated_tenant():
    user = SimpleNamespace(tenant_id=TENANT_A, is_superuser=False)
    assert billing._ensure_current_tenant(user, TENANT_A) is None


def test_billing_tenant_guard_hides_other_tenants():
    user = SimpleNamespace(tenant_id=TENANT_A, is_superuser=False)
    with pytest.raises(HTTPException) as exc:
        billing._ensure_current_tenant(user, TENANT_B)

    assert exc.value.status_code == 404


def test_platform_superuser_can_cross_tenant_for_administration():
    user = SimpleNamespace(tenant_id=TENANT_A, is_superuser=True)
    assert billing._ensure_current_tenant(user, TENANT_B) is None


@pytest.mark.parametrize(
    "endpoint_name",
    [
        "create_subscription",
        "get_subscription",
        "cancel_subscription",
        "reactivate_subscription",
        "create_checkout_session",
        "create_portal_session",
        "list_invoices",
        "get_invoice",
        "list_payment_methods",
        "attach_payment_method",
    ],
)
def test_tenant_billing_routes_require_billing_permission(endpoint_name):
    endpoint = getattr(billing, endpoint_name)
    parameter = inspect.signature(endpoint).parameters["current_user"]
    assert isinstance(parameter.default, Depends)
    assert parameter.default.dependency is not None
    assert parameter.default.dependency.__class__.__name__ == "PermissionChecker"
    assert parameter.default.dependency.permission == "admin.billing.manage"


@pytest.mark.parametrize(
    "endpoint_name",
    ["detach_payment_method", "start_trial", "extend_trial"],
)
def test_platform_billing_operations_require_superuser(endpoint_name):
    endpoint = getattr(billing, endpoint_name)
    parameter = inspect.signature(endpoint).parameters["current_user"]
    assert isinstance(parameter.default, Depends)
    assert parameter.default.dependency is get_current_superuser
