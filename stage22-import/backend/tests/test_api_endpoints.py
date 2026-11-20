"""
Nexus ERP - API Endpoints Tests
================================

This module contains tests for all API endpoints:
- Authentication endpoints
- CRUD operations for each module
- Authorization checks
- Error handling
"""

import pytest
from decimal import Decimal
from datetime import date
from uuid import UUID
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserStatus


# ========================================
# Health Check Tests
# ========================================

@pytest.mark.asyncio
class TestHealthEndpoints:
    """Tests for health check endpoints."""

    async def test_health_check(self, async_client: AsyncClient):
        """Test basic health check endpoint."""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data

    async def test_readiness_check(self, async_client: AsyncClient):
        """Test readiness check endpoint."""
        response = await async_client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "database" in data["services"]

    async def test_root_endpoint(self, async_client: AsyncClient):
        """Test root endpoint."""
        response = await async_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "docs" in data


# ========================================
# Authentication Endpoints Tests
# ========================================

@pytest.mark.asyncio
class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    async def test_login_success(
        self,
        async_client: AsyncClient,
        test_user: User
    ):
        """Test successful login."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "TestPassword123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert "access_token" in data["token"]
        assert "refresh_token" in data["token"]

    async def test_login_with_email(
        self,
        async_client: AsyncClient,
        test_user: User
    ):
        """Test login using email instead of username."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.email,
                "password": "TestPassword123!"
            }
        )
        
        assert response.status_code == 200

    async def test_login_invalid_password(
        self,
        async_client: AsyncClient,
        test_user: User
    ):
        """Test login with wrong password."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with non-existent user."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "SomePassword123!"
            }
        )
        
        assert response.status_code == 401

    async def test_token_refresh(
        self,
        async_client: AsyncClient,
        test_user: User
    ):
        """Test token refresh."""
        # First login
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "TestPassword123!"
            }
        )
        refresh_token = login_response.json()["token"]["refresh_token"]
        
        # Refresh
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_logout(self, async_client: AsyncClient, test_user: User):
        """Test logout endpoint."""
        # Login first
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "TestPassword123!"
            }
        )
        access_token = login_response.json()["token"]["access_token"]
        
        # Logout
        response = await async_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200


# ========================================
# Authorization Tests
# ========================================

@pytest.mark.asyncio
class TestAuthorization:
    """Tests for authorization and permissions."""

    async def test_protected_endpoint_without_token(
        self,
        async_client: AsyncClient
    ):
        """Test accessing protected endpoint without token."""
        response = await async_client.get("/api/v1/inventory/products")
        
        assert response.status_code == 401

    async def test_protected_endpoint_with_valid_token(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test accessing protected endpoint with valid token."""
        response = await async_client.get(
            "/api/v1/inventory/products",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_invalid_token(self, async_client: AsyncClient):
        """Test with invalid token format."""
        response = await async_client.get(
            "/api/v1/inventory/products",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401

    async def test_expired_token(self, async_client: AsyncClient):
        """Test with expired token (simulated)."""
        # In real scenario, would use an expired token
        # For now, just verify the endpoint exists
        response = await async_client.get(
            "/api/v1/inventory/products",
            headers={"Authorization": "Bearer expired.token.here"}
        )
        
        assert response.status_code in [401, 403]


# ========================================
# Inventory Endpoints Tests
# ========================================

@pytest.mark.asyncio
class TestInventoryEndpoints:
    """Tests for inventory module endpoints."""

    async def test_list_products(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test listing products."""
        response = await async_client.get(
            "/api/v1/inventory/products",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data or isinstance(data, list)

    async def test_create_product(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_accounts
    ):
        """Test creating a new product."""
        product_data = {
            "name": "New Test Product",
            "sku": "NEW-TEST-001",
            "cost_price": 75.00,
            "sale_price": 100.00,
            "is_stockable": True,
            "asset_account_id": str(test_accounts["inventory"].id),
            "expense_account_id": str(test_accounts["cogs"].id),
            "income_account_id": str(test_accounts["sales"].id)
        }
        
        response = await async_client.post(
            "/api/v1/inventory/products",
            json=product_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["name"] == "New Test Product"
        assert data["data"]["sku"] == "NEW-TEST-001"

    async def test_get_product(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_product
    ):
        """Test getting a specific product."""
        response = await async_client.get(
            f"/api/v1/inventory/products/{test_product.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == str(test_product.id)

    async def test_update_product(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_product
    ):
        """Test updating a product."""
        update_data = {
            "name": "Updated Product Name",
            "sale_price": 200.00
        }
        
        response = await async_client.put(
            f"/api/v1/inventory/products/{test_product.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Updated Product Name"

    async def test_create_stock_move(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_product
    ):
        """Test creating a stock movement."""
        move_data = {
            "product_id": str(test_product.id),
            "move_type": "in",
            "quantity": 50,
            "unit_cost": 100.00,
            "date": str(date.today())
        }
        
        response = await async_client.post(
            "/api/v1/inventory/stock-moves",
            json=move_data,
            headers=auth_headers
        )
        
        # Accept either 201 (created) or 200 (processed)
        assert response.status_code in [200, 201]


# ========================================
# Accounting Endpoints Tests
# ========================================

@pytest.mark.asyncio
class TestAccountingEndpoints:
    """Tests for accounting module endpoints."""

    async def test_list_accounts(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test listing chart of accounts."""
        response = await async_client.get(
            "/api/v1/accounts",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_create_account(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        tenant_id: UUID
    ):
        """Test creating a new account."""
        account_data = {
            "code": "9999",
            "name": "Test Account",
            "account_type": "expense",
            "category": "operating_expense"
        }
        
        response = await async_client.post(
            "/api/v1/accounts",
            json=account_data,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]

    async def test_create_journal_entry(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_accounts
    ):
        """Test creating a journal entry."""
        entry_data = {
            "date": str(date.today()),
            "description": "Test Journal Entry",
            "lines": [
                {
                    "account_id": str(test_accounts["cash"].id),
                    "debit": 1000,
                    "credit": 0,
                    "name": "Cash debit"
                },
                {
                    "account_id": str(test_accounts["sales"].id),
                    "debit": 0,
                    "credit": 1000,
                    "name": "Sales credit"
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/journal-entries",
            json=entry_data,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]

    async def test_trial_balance_report(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test trial balance report."""
        response = await async_client.get(
            "/api/v1/reports/trial-balance",
            params={"date": str(date.today())},
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_income_statement_report(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test income statement report."""
        response = await async_client.get(
            "/api/v1/reports/income-statement",
            params={
                "from": "2024-01-01",
                "to": "2024-12-31"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_balance_sheet_report(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test balance sheet report."""
        response = await async_client.get(
            "/api/v1/reports/balance-sheet",
            params={"date": str(date.today())},
            headers=auth_headers
        )
        
        assert response.status_code == 200


# ========================================
# Sales Endpoints Tests
# ========================================

@pytest.mark.asyncio
class TestSalesEndpoints:
    """Tests for sales module endpoints."""

    async def test_list_quotations(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test listing quotations."""
        response = await async_client.get(
            "/api/v1/sales/quotations",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_create_quotation(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_customer,
        test_product
    ):
        """Test creating a quotation."""
        quotation_data = {
            "partner_id": str(test_customer.id),
            "date_quotation": str(date.today()),
            "lines": [
                {
                    "product_id": str(test_product.id),
                    "quantity": 5,
                    "unit_price": float(test_product.sale_price)
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/sales/quotations",
            json=quotation_data,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]

    async def test_list_sale_orders(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test listing sale orders."""
        response = await async_client.get(
            "/api/v1/sales/orders",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_create_sale_order(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_customer,
        test_product
    ):
        """Test creating a sale order."""
        order_data = {
            "partner_id": str(test_customer.id),
            "date_order": str(date.today()),
            "lines": [
                {
                    "product_id": str(test_product.id),
                    "quantity": 3,
                    "unit_price": float(test_product.sale_price)
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/sales/orders",
            json=order_data,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]


# ========================================
# Purchase Endpoints Tests
# ========================================

@pytest.mark.asyncio
class TestPurchaseEndpoints:
    """Tests for purchase module endpoints."""

    async def test_list_purchase_orders(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test listing purchase orders."""
        response = await async_client.get(
            "/api/v1/purchase/orders",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_create_purchase_order(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_supplier,
        test_product
    ):
        """Test creating a purchase order."""
        po_data = {
            "partner_id": str(test_supplier.id),
            "date_order": str(date.today()),
            "lines": [
                {
                    "product_id": str(test_product.id),
                    "quantity": 20,
                    "unit_price": float(test_product.cost_price)
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/purchase/orders",
            json=po_data,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]


# ========================================
# Manufacturing Endpoints Tests
# ========================================

@pytest.mark.asyncio
class TestManufacturingEndpoints:
    """Tests for manufacturing module endpoints."""

    async def test_list_boms(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test listing bills of materials."""
        response = await async_client.get(
            "/api/v1/manufacturing/boms",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_create_bom(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_products
    ):
        """Test creating a bill of materials."""
        finished_product = test_products[0]
        raw_material = test_products[1]
        
        bom_data = {
            "code": f"BOM-{finished_product.sku}",
            "name": f"BOM for {finished_product.name}",
            "product_id": str(finished_product.id),
            "product_qty": 1,
            "bom_type": "manufacture",
            "lines": [
                {
                    "product_id": str(raw_material.id),
                    "product_qty": 2,
                    "unit_cost": float(raw_material.cost_price)
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/manufacturing/boms",
            json=bom_data,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]

    async def test_list_manufacturing_orders(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test listing manufacturing orders."""
        response = await async_client.get(
            "/api/v1/manufacturing/orders",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_create_manufacturing_order(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_bom
    ):
        """Test creating a manufacturing order."""
        mo_data = {
            "product_id": str(test_bom.product_id),
            "bom_id": str(test_bom.id),
            "product_qty": 5,
            "planned_date": str(date.today())
        }
        
        response = await async_client.post(
            "/api/v1/manufacturing/orders",
            json=mo_data,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]


# ========================================
# AI Endpoints Tests
# ========================================

@pytest.mark.asyncio
class TestAIEndpoints:
    """Tests for AI module endpoints."""

    async def test_forecast_endpoint(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_product
    ):
        """Test demand forecasting endpoint."""
        response = await async_client.post(
            "/api/v1/ai/forecast",
            json={
                "product_id": str(test_product.id),
                "periods": 6,
                "period_type": "monthly"
            },
            headers=auth_headers
        )
        
        # May fail if AI service not configured
        assert response.status_code in [200, 201, 503]

    async def test_chatbot_endpoint(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test chatbot endpoint."""
        response = await async_client.post(
            "/api/v1/ai/chat",
            json={
                "message": "What is the current stock of products?"
            },
            headers=auth_headers
        )
        
        # May fail if AI service not configured
        assert response.status_code in [200, 503]


# ========================================
# Error Response Tests
# ========================================

@pytest.mark.asyncio
class TestErrorResponses:
    """Tests for error response format."""

    async def test_404_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test 404 error response format."""
        response = await async_client.get(
            "/api/v1/inventory/products/00000000-0000-0000-0000-000000000000",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data or "detail" in data

    async def test_422_validation_error(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test 422 validation error response format."""
        response = await async_client.post(
            "/api/v1/inventory/products",
            json={
                "name": "",  # Empty name should fail
                "sku": "",   # Empty SKU should fail
            },
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data or "detail" in data

    async def test_method_not_allowed(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test 405 method not allowed."""
        response = await async_client.patch(
            "/api/v1/inventory/products",
            headers=auth_headers
        )
        
        assert response.status_code == 405


# ========================================
# Pagination Tests
# ========================================

@pytest.mark.asyncio
class TestPagination:
    """Tests for pagination functionality."""

    async def test_products_pagination(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test pagination for products list."""
        response = await async_client.get(
            "/api/v1/inventory/products",
            params={"page": 1, "page_size": 10},
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_journal_entries_pagination(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test pagination for journal entries."""
        response = await async_client.get(
            "/api/v1/journal-entries",
            params={"page": 1, "page_size": 20},
            headers=auth_headers
        )
        
        assert response.status_code == 200


# ========================================
# Filtering and Sorting Tests
# ========================================

@pytest.mark.asyncio
class TestFilteringSorting:
    """Tests for filtering and sorting functionality."""

    async def test_products_filter_by_name(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test filtering products by name."""
        response = await async_client.get(
            "/api/v1/inventory/products",
            params={"search": "Test"},
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_journal_entries_filter_by_date(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test filtering journal entries by date."""
        response = await async_client.get(
            "/api/v1/journal-entries",
            params={
                "from_date": "2024-01-01",
                "to_date": "2024-12-31"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_products_sort_by_name(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test sorting products by name."""
        response = await async_client.get(
            "/api/v1/inventory/products",
            params={"sort_by": "name", "sort_order": "asc"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
