"""
Nexus ERP - Sales Module Tests
===============================

Test cases for the Sales module including quotations, orders, invoices, and payments.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sales import (
    Quotation, QuotationLine, QuotationState,
    SaleOrder, SaleOrderLine, SaleOrderState,
    Invoice, InvoiceLine, InvoiceType, InvoiceState,
    Payment, PaymentType, PaymentState
)
from app.models.accounting import Partner, Account, AccountType
from app.models.inventory import Product, UnitOfMeasure, UOMCategory
from app.models.user import User
from app.services.sales_service import SalesService


@pytest.fixture
async def test_partner(db: AsyncSession, test_tenant_id) -> Partner:
    """Create a test partner (customer)."""
    partner = Partner(
        id=uuid4(),
        tenant_id=test_tenant_id,
        name="Test Customer",
        partner_type="customer",
        email="customer@test.com",
        phone="+1234567890",
        receivable_balance=Decimal("0"),
        payable_balance=Decimal("0")
    )
    db.add(partner)
    await db.commit()
    await db.refresh(partner)
    return partner


@pytest.fixture
async def test_product(db: AsyncSession, test_tenant_id) -> Product:
    """Create a test product."""
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
        sku="TEST-001",
        name="Test Product",
        uom_id=uom.id,
        cost_price=Decimal("50.00"),
        sale_price=Decimal("100.00"),
        quantity_on_hand=Decimal("100"),
        average_cost=Decimal("50.00"),
        is_stockable=True
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@pytest.fixture
async def test_revenue_account(db: AsyncSession, test_tenant_id) -> Account:
    """Create a test revenue account."""
    account = Account(
        id=uuid4(),
        tenant_id=test_tenant_id,
        code="4001",
        name="Sales Revenue",
        account_type=AccountType.REVENUE,
        is_active=True
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


class TestQuotationService:
    """Test cases for Quotation service."""
    
    @pytest.mark.asyncio
    async def test_create_quotation(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_partner,
        test_product
    ):
        """Test creating a quotation."""
        service = SalesService(db)
        
        data = {
            "name": "Test Quotation",
            "partner_id": test_partner.id,
            "date": date.today(),
            "valid_until": date.today() + timedelta(days=30),
            "lines": [
                {
                    "product_id": test_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("10"),
                    "price_unit": Decimal("100.00"),
                    "discount": Decimal("0"),
                    "tax_ids": []
                }
            ]
        }
        
        quotation = await service.create_quotation(
            tenant_id=test_tenant_id,
            data=data,
            user_id=test_user.id
        )
        
        assert quotation is not None
        assert quotation.partner_id == test_partner.id
        assert quotation.state == QuotationState.DRAFT
        assert len(quotation.lines) == 1
        assert quotation.amount_untaxed == Decimal("1000.00")
    
    @pytest.mark.asyncio
    async def test_send_quotation(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_partner,
        test_product
    ):
        """Test sending a quotation."""
        service = SalesService(db)
        
        # Create quotation first
        data = {
            "name": "Test Quotation",
            "partner_id": test_partner.id,
            "date": date.today(),
            "lines": [
                {
                    "product_id": test_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("5"),
                    "price_unit": Decimal("100.00"),
                    "tax_ids": []
                }
            ]
        }
        
        quotation = await service.create_quotation(
            tenant_id=test_tenant_id,
            data=data,
            user_id=test_user.id
        )
        
        # Send quotation
        sent = await service.send_quotation(
            quotation_id=quotation.id,
            tenant_id=test_tenant_id,
            user_id=test_user.id
        )
        
        assert sent.state == QuotationState.SENT
        assert sent.sent_at is not None
    
    @pytest.mark.asyncio
    async def test_confirm_quotation_creates_order(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_partner,
        test_product
    ):
        """Test confirming quotation creates sale order."""
        service = SalesService(db)
        
        # Create and send quotation
        data = {
            "name": "Test Quotation",
            "partner_id": test_partner.id,
            "date": date.today(),
            "lines": [
                {
                    "product_id": test_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("3"),
                    "price_unit": Decimal("100.00"),
                    "tax_ids": []
                }
            ]
        }
        
        quotation = await service.create_quotation(
            tenant_id=test_tenant_id,
            data=data,
            user_id=test_user.id
        )
        
        await service.send_quotation(
            quotation_id=quotation.id,
            tenant_id=test_tenant_id,
            user_id=test_user.id
        )
        
        # Confirm quotation
        order = await service.confirm_quotation(
            quotation_id=quotation.id,
            tenant_id=test_tenant_id,
            create_order=True,
            user_id=test_user.id
        )
        
        assert order is not None
        assert order.quotation_id == quotation.id
        assert len(order.lines) == 1
        assert order.state == SaleOrderState.DRAFT


class TestSaleOrderService:
    """Test cases for Sale Order service."""
    
    @pytest.mark.asyncio
    async def test_create_sale_order(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_partner,
        test_product
    ):
        """Test creating a sale order."""
        service = SalesService(db)
        
        data = {
            "name": "Test Order",
            "partner_id": test_partner.id,
            "date_order": date.today(),
            "lines": [
                {
                    "product_id": test_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("10"),
                    "price_unit": Decimal("100.00"),
                    "tax_ids": []
                }
            ]
        }
        
        order = await service.create_sale_order(
            tenant_id=test_tenant_id,
            data=data,
            user_id=test_user.id
        )
        
        assert order is not None
        assert order.state == SaleOrderState.DRAFT
        assert order.amount_total == Decimal("1000.00")
    
    @pytest.mark.asyncio
    async def test_confirm_sale_order(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_partner,
        test_product
    ):
        """Test confirming a sale order."""
        service = SalesService(db)
        
        # Create order
        data = {
            "name": "Test Order",
            "partner_id": test_partner.id,
            "date_order": date.today(),
            "lines": [
                {
                    "product_id": test_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("5"),
                    "price_unit": Decimal("100.00"),
                    "tax_ids": []
                }
            ]
        }
        
        order = await service.create_sale_order(
            tenant_id=test_tenant_id,
            data=data,
            user_id=test_user.id
        )
        
        # Confirm order
        confirmed = await service.confirm_sale_order(
            order_id=order.id,
            tenant_id=test_tenant_id,
            create_delivery=True,
            create_invoice=False,
            user_id=test_user.id
        )
        
        assert confirmed.state == SaleOrderState.CONFIRMED
        assert confirmed.date_confirm == date.today()


class TestInvoiceService:
    """Test cases for Invoice service."""
    
    @pytest.mark.asyncio
    async def test_create_invoice(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_partner,
        test_product,
        test_revenue_account
    ):
        """Test creating an invoice."""
        service = SalesService(db)
        
        data = {
            "name": "Test Invoice",
            "invoice_type": InvoiceType.OUT_INVOICE.value,
            "partner_id": test_partner.id,
            "date_invoice": date.today(),
            "lines": [
                {
                    "product_id": test_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("10"),
                    "price_unit": Decimal("100.00"),
                    "account_id": test_revenue_account.id,
                    "tax_ids": []
                }
            ]
        }
        
        invoice = await service.create_invoice(
            tenant_id=test_tenant_id,
            data=data,
            user_id=test_user.id
        )
        
        assert invoice is not None
        assert invoice.state == InvoiceState.DRAFT
        assert invoice.amount_untaxed == Decimal("1000.00")
    
    @pytest.mark.asyncio
    async def test_post_invoice(
        self,
        db: AsyncSession,
        test_tenant_id,
        test_user,
        test_partner,
        test_product,
        test_revenue_account
    ):
        """Test posting an invoice."""
        service = SalesService(db)
        
        # Create invoice first
        data = {
            "name": "Test Invoice",
            "invoice_type": InvoiceType.OUT_INVOICE.value,
            "partner_id": test_partner.id,
            "date_invoice": date.today(),
            "lines": [
                {
                    "product_id": test_product.id,
                    "description": "Test Product",
                    "quantity": Decimal("5"),
                    "price_unit": Decimal("100.00"),
                    "account_id": test_revenue_account.id,
                    "tax_ids": []
                }
            ]
        }
        
        invoice = await service.create_invoice(
            tenant_id=test_tenant_id,
            data=data,
            user_id=test_user.id
        )
        
        # Post invoice
        posted = await service.post_invoice(
            invoice_id=invoice.id,
            tenant_id=test_tenant_id,
            user_id=test_user.id
        )
        
        assert posted.state == InvoiceState.POSTED
        assert posted.date_posted == date.today()


class TestQuotationAPI:
    """Test cases for Quotation API endpoints."""
    
    @pytest.mark.asyncio
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
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_create_quotation_api(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_partner,
        test_product
    ):
        """Test creating quotation via API."""
        response = await async_client.post(
            "/api/v1/sales/quotations",
            headers=auth_headers,
            json={
                "name": "API Test Quotation",
                "partner_id": str(test_partner.id),
                "date": str(date.today()),
                "lines": [
                    {
                        "product_id": str(test_product.id),
                        "description": "Test Product",
                        "quantity": 5,
                        "price_unit": 100.00,
                        "tax_ids": []
                    }
                ]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Test Quotation"
        assert data["state"] == "draft"


class TestSaleOrderAPI:
    """Test cases for Sale Order API endpoints."""
    
    @pytest.mark.asyncio
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
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_create_sale_order_api(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_partner,
        test_product
    ):
        """Test creating sale order via API."""
        response = await async_client.post(
            "/api/v1/sales/orders",
            headers=auth_headers,
            json={
                "name": "API Test Order",
                "partner_id": str(test_partner.id),
                "date_order": str(date.today()),
                "lines": [
                    {
                        "product_id": str(test_product.id),
                        "description": "Test Product",
                        "quantity": 10,
                        "price_unit": 100.00,
                        "tax_ids": []
                    }
                ]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Test Order"
        assert data["state"] == "draft"


class TestInvoiceAPI:
    """Test cases for Invoice API endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_invoices(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test listing invoices."""
        response = await async_client.get(
            "/api/v1/sales/invoices",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_create_invoice_api(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_partner,
        test_product,
        test_revenue_account
    ):
        """Test creating invoice via API."""
        response = await async_client.post(
            "/api/v1/sales/invoices",
            headers=auth_headers,
            json={
                "name": "API Test Invoice",
                "invoice_type": "out_invoice",
                "partner_id": str(test_partner.id),
                "date_invoice": str(date.today()),
                "lines": [
                    {
                        "product_id": str(test_product.id),
                        "description": "Test Product",
                        "quantity": 3,
                        "price_unit": 100.00,
                        "account_id": str(test_revenue_account.id),
                        "tax_ids": []
                    }
                ]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Test Invoice"
        assert data["state"] == "draft"
