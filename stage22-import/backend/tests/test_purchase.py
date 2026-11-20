"""
Nexus ERP - Purchase Module Tests
==================================

Test cases for the Purchase module including orders, receipts, and invoices.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.purchase import (
    PurchaseOrder, PurchaseOrderLine, PurchaseOrderState,
    Receipt, ReceiptLine, ReceiptState,
    PurchaseInvoice, PurchaseInvoiceLine, PurchaseInvoiceState
)
from app.models.accounting import Partner, Account, AccountType
from app.models.inventory import (
    Product, UnitOfMeasure, UOMCategory, 
    Warehouse, StockLocation
)
from app.models.user import User
from app.services.purchase_service import PurchaseService


@pytest.fixture
async def test_supplier(db: AsyncSession, test_tenant_id) -> Partner:
    """Create a test supplier."""
    supplier = Partner(
        id=uuid4(),
        tenant_id=test_tenant_id,
        name="Test Supplier",
        partner_type="supplier",
        email="supplier@test.com",
        phone="+1234567890",
        receivable_balance=Decimal("0"),
        payable_balance=Decimal("0")
    )
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@pytest.fixture
async def test_purchase_product(db: AsyncSession, test_tenant_id) -> Product:
    """Create a test product for purchasing."""
    # Create UOM
    uom = UnitOfMeasure(
        id=uuid4(),
        code="PCS",
        name="Pieces",
        category=UOMCategory.UNIT,
        factor=Decimal("1"),
        is_base=True,
        is_active=True
    )
    db.add(uom)
    await db.flush()
    
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant_id,
        sku="PURCH-001",
        name="Purchase Test Product",
        uom_id=uom.id,
        cost_price=Decimal("25.00"),
        sale_price=Decimal("50.00"),
        quantity_on_hand=Decimal("50"),
        average_cost=Decimal("25.00"),
        is_stockable=True
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@pytest.fixture
async def test_warehouse(db: AsyncSession, test_tenant_id) -> Warehouse:
    """Create a test warehouse."""
    warehouse = Warehouse(
        id=uuid4(),
        tenant_id=test_tenant_id,
        code="WH01",
        name="Main Warehouse",
        is_default=True,
        is_active=True
    )
    db.add(warehouse)
    await db.commit()
    await db.refresh(warehouse)
    return warehouse


@pytest.fixture
async def test_location(db: AsyncSession, test_tenant_id, test_warehouse) -> StockLocation:
    """Create a test stock location."""
    location = StockLocation(
        id=uuid4(),
        tenant_id=test_tenant_id,
        warehouse_id=test_warehouse.id,
        code="LOC-01",
        name="Receiving Area",
        location_type="input",
        is_active=True
    )
    db.add(location)
    await db.commit()
    await db.refresh(location)
    return location


@pytest.fixture
async def test_expense_account(db: AsyncSession, test_tenant_id) -> Account:
    """Create a test expense account."""
    account = Account(
        id=uuid4(),
        tenant_id=test_tenant_id,
        code="5001",
        name="Purchases",
        account_type=AccountType.EXPENSE,
        is_active=True
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


class TestPurchaseOrderService:
    """Test cases for Purchase Order service."""
    
    @pytest.mark.asyncio
    async def test_create_purchase_order(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_supplier,
        test_purchase_product
    ):
        """Test creating a purchase order."""
        service = PurchaseService(db)
        
        data = {
            "name": "Test PO",
            "partner_id": test_supplier.id,
            "date_order": date.today(),
            "lines": [
                {
                    "product_id": test_purchase_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("20"),
                    "price_unit": Decimal("25.00"),
                    "tax_ids": []
                }
            ]
        }
        
        order = await service.create_purchase_order(
            tenant_id=test_tenant_id,
            data=data,
            user_id=test_user.id
        )
        
        assert order is not None
        assert order.partner_id == test_supplier.id
        assert order.state == PurchaseOrderState.DRAFT
        assert len(order.lines) == 1
        assert order.amount_untaxed == Decimal("500.00")
    
    @pytest.mark.asyncio
    async def test_confirm_purchase_order(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_supplier,
        test_purchase_product
    ):
        """Test confirming a purchase order."""
        service = PurchaseService(db)
        
        # Create order first
        data = {
            "name": "Test PO",
            "partner_id": test_supplier.id,
            "date_order": date.today(),
            "lines": [
                {
                    "product_id": test_purchase_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("10"),
                    "price_unit": Decimal("25.00"),
                    "tax_ids": []
                }
            ]
        }
        
        order = await service.create_purchase_order(
            tenant_id=test_tenant_id,
            data=data,
            user_id=test_user.id
        )
        
        # Confirm order
        confirmed = await service.confirm_purchase_order(
            order_id=order.id,
            tenant_id=test_tenant_id,
            user_id=test_user.id
        )
        
        assert confirmed.state == PurchaseOrderState.CONFIRMED
        assert confirmed.date_confirm == date.today()
    
    @pytest.mark.asyncio
    async def test_cancel_purchase_order(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_supplier,
        test_purchase_product
    ):
        """Test cancelling a purchase order."""
        service = PurchaseService(db)
        
        # Create order
        data = {
            "name": "Test PO",
            "partner_id": test_supplier.id,
            "date_order": date.today(),
            "lines": [
                {
                    "product_id": test_purchase_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("5"),
                    "price_unit": Decimal("25.00"),
                    "tax_ids": []
                }
            ]
        }
        
        order = await service.create_purchase_order(
            tenant_id=test_tenant_id,
            data=data,
            user_id=test_user.id
        )
        
        # Cancel order
        cancelled = await service.cancel_purchase_order(
            order_id=order.id,
            tenant_id=test_tenant_id,
            reason="Test cancellation",
            user_id=test_user.id
        )
        
        assert cancelled.state == PurchaseOrderState.CANCELLED


class TestReceiptService:
    """Test cases for Receipt service."""
    
    @pytest.mark.asyncio
    async def test_create_receipt(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_supplier,
        test_purchase_product,
        test_warehouse,
        test_location
    ):
        """Test creating a receipt."""
        service = PurchaseService(db)
        
        data = {
            "name": "Test Receipt",
            "partner_id": test_supplier.id,
            "date": date.today(),
            "warehouse_id": test_warehouse.id,
            "location_id": test_location.id,
            "lines": [
                {
                    "product_id": test_purchase_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("10"),
                    "uom_id": test_purchase_product.uom_id
                }
            ]
        }
        
        receipt = await service.create_receipt(
            tenant_id=test_tenant_id,
            data=data,
            user_id=test_user.id
        )
        
        assert receipt is not None
        assert receipt.state == ReceiptState.DRAFT
        assert len(receipt.lines) == 1
    
    @pytest.mark.asyncio
    async def test_create_receipt_from_order(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_supplier,
        test_purchase_product,
        test_warehouse,
        test_location
    ):
        """Test creating receipt from purchase order."""
        service = PurchaseService(db)
        
        # Create and confirm order
        order_data = {
            "name": "Test PO",
            "partner_id": test_supplier.id,
            "date_order": date.today(),
            "warehouse_id": test_warehouse.id,
            "lines": [
                {
                    "product_id": test_purchase_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("15"),
                    "price_unit": Decimal("25.00"),
                    "tax_ids": []
                }
            ]
        }
        
        order = await service.create_purchase_order(
            tenant_id=test_tenant_id,
            data=order_data,
            user_id=test_user.id
        )
        
        await service.confirm_purchase_order(
            order_id=order.id,
            tenant_id=test_tenant_id,
            user_id=test_user.id
        )
        
        # Create receipt from order
        receipt = await service.create_receipt_from_order(
            order_id=order.id,
            tenant_id=test_tenant_id,
            warehouse_id=test_warehouse.id,
            location_id=test_location.id,
            user_id=test_user.id
        )
        
        assert receipt is not None
        assert receipt.purchase_order_id == order.id
        assert len(receipt.lines) == 1
        assert receipt.lines[0].quantity == Decimal("15")


class TestPurchaseInvoiceService:
    """Test cases for Purchase Invoice service."""
    
    @pytest.mark.asyncio
    async def test_create_purchase_invoice(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_supplier,
        test_purchase_product,
        test_expense_account
    ):
        """Test creating a purchase invoice."""
        service = PurchaseService(db)
        
        data = {
            "name": "Test Vendor Bill",
            "partner_id": test_supplier.id,
            "date_invoice": date.today(),
            "lines": [
                {
                    "product_id": test_purchase_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("10"),
                    "price_unit": Decimal("25.00"),
                    "account_id": test_expense_account.id,
                    "tax_ids": []
                }
            ]
        }
        
        invoice = await service.create_purchase_invoice(
            tenant_id=test_tenant_id,
            data=data,
            user_id=test_user.id
        )
        
        assert invoice is not None
        assert invoice.state == PurchaseInvoiceState.DRAFT
        assert invoice.amount_untaxed == Decimal("250.00")
    
    @pytest.mark.asyncio
    async def test_post_purchase_invoice(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_supplier,
        test_purchase_product,
        test_expense_account
    ):
        """Test posting a purchase invoice."""
        service = PurchaseService(db)
        
        # Create invoice first
        data = {
            "name": "Test Vendor Bill",
            "partner_id": test_supplier.id,
            "date_invoice": date.today(),
            "lines": [
                {
                    "product_id": test_purchase_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("5"),
                    "price_unit": Decimal("25.00"),
                    "account_id": test_expense_account.id,
                    "tax_ids": []
                }
            ]
        }
        
        invoice = await service.create_purchase_invoice(
            tenant_id=test_tenant_id,
            data=data,
            user_id=test_user.id
        )
        
        # Post invoice
        posted = await service.post_purchase_invoice(
            invoice_id=invoice.id,
            tenant_id=test_tenant_id,
            user_id=test_user.id
        )
        
        assert posted.state == PurchaseInvoiceState.POSTED
        assert posted.date_posted == date.today()


class TestPurchaseOrderAPI:
    """Test cases for Purchase Order API endpoints."""
    
    @pytest.mark.asyncio
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
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_create_purchase_order_api(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_supplier,
        test_purchase_product
    ):
        """Test creating purchase order via API."""
        response = await async_client.post(
            "/api/v1/purchase/orders",
            headers=auth_headers,
            json={
                "name": "API Test PO",
                "partner_id": str(test_supplier.id),
                "date_order": str(date.today()),
                "lines": [
                    {
                        "product_id": str(test_purchase_product.id),
                        "description": "Test Product",
                        "quantity": 20,
                        "price_unit": 25.00,
                        "tax_ids": []
                    }
                ]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Test PO"
        assert data["state"] == "draft"


class TestReceiptAPI:
    """Test cases for Receipt API endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_receipts(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test listing receipts."""
        response = await async_client.get(
            "/api/v1/purchase/receipts",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_create_receipt_api(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_supplier,
        test_purchase_product,
        test_warehouse,
        test_location
    ):
        """Test creating receipt via API."""
        response = await async_client.post(
            "/api/v1/purchase/receipts",
            headers=auth_headers,
            json={
                "name": "API Test Receipt",
                "partner_id": str(test_supplier.id),
                "date": str(date.today()),
                "warehouse_id": str(test_warehouse.id),
                "location_id": str(test_location.id),
                "lines": [
                    {
                        "product_id": str(test_purchase_product.id),
                        "description": "Test Product",
                        "quantity": 10,
                        "uom_id": str(test_purchase_product.uom_id)
                    }
                ]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Test Receipt"
        assert data["state"] == "draft"


class TestPurchaseInvoiceAPI:
    """Test cases for Purchase Invoice API endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_purchase_invoices(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test listing purchase invoices."""
        response = await async_client.get(
            "/api/v1/purchase/invoices",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_create_purchase_invoice_api(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_supplier,
        test_purchase_product,
        test_expense_account
    ):
        """Test creating purchase invoice via API."""
        response = await async_client.post(
            "/api/v1/purchase/invoices",
            headers=auth_headers,
            json={
                "name": "API Test Vendor Bill",
                "partner_id": str(test_supplier.id),
                "date_invoice": str(date.today()),
                "lines": [
                    {
                        "product_id": str(test_purchase_product.id),
                        "description": "Test Product",
                        "quantity": 10,
                        "price_unit": 25.00,
                        "account_id": str(test_expense_account.id),
                        "tax_ids": []
                    }
                ]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Test Vendor Bill"
        assert data["state"] == "draft"


class TestPurchaseIntegration:
    """Test cases for Purchase integration with other modules."""
    
    @pytest.mark.asyncio
    async def test_full_purchase_cycle(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_supplier,
        test_purchase_product,
        test_warehouse,
        test_location,
        test_expense_account
    ):
        """Test complete purchase cycle: PO -> Receipt -> Invoice."""
        service = PurchaseService(db)
        
        # 1. Create Purchase Order
        order_data = {
            "name": "Full Cycle PO",
            "partner_id": test_supplier.id,
            "date_order": date.today(),
            "warehouse_id": test_warehouse.id,
            "lines": [
                {
                    "product_id": test_purchase_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("30"),
                    "price_unit": Decimal("25.00"),
                    "tax_ids": []
                }
            ]
        }
        
        order = await service.create_purchase_order(
            tenant_id=test_tenant_id,
            data=order_data,
            user_id=test_user.id
        )
        
        assert order.state == PurchaseOrderState.DRAFT
        
        # 2. Confirm Order
        order = await service.confirm_purchase_order(
            order_id=order.id,
            tenant_id=test_tenant_id,
            user_id=test_user.id
        )
        
        assert order.state == PurchaseOrderState.CONFIRMED
        
        # 3. Create Receipt from Order
        receipt = await service.create_receipt_from_order(
            order_id=order.id,
            tenant_id=test_tenant_id,
            warehouse_id=test_warehouse.id,
            location_id=test_location.id,
            user_id=test_user.id
        )
        
        assert receipt is not None
        
        # 4. Confirm Receipt
        receipt = await service.confirm_receipt(
            receipt_id=receipt.id,
            tenant_id=test_tenant_id,
            user_id=test_user.id
        )
        
        assert receipt.state == ReceiptState.DONE
        
        # 5. Verify order status updated
        await db.refresh(order)
        assert order.receipt_status == "done"
        assert order.state == PurchaseOrderState.DONE
