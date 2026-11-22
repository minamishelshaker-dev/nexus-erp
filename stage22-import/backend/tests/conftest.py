"""
Nexus ERP - Pytest Configuration
================================

This module provides comprehensive pytest fixtures and configuration for testing.
Includes fixtures for database, authentication, and test data creation.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator, Dict, Any, Optional, Tuple
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import select
from decimal import Decimal
from datetime import date, datetime, timedelta
import uuid

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.core.security import get_password_hash, create_access_token


# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://nexus_user:nexus_password@localhost:5432/nexus_erp_test"


# ========================================
# Event Loop
# ========================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ========================================
# Database Fixtures
# ========================================

@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


# ========================================
# Client Fixtures
# ========================================

@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


# ========================================
# User Fixtures
# ========================================

@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a standard test user."""
    from app.models.user import User, UserStatus
    
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash=get_password_hash("TestPassword123!"),
        first_name="Test",
        last_name="User",
        status=UserStatus.ACTIVE,
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession):
    """Create an admin test user with superuser privileges."""
    from app.models.user import User, UserStatus
    
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        username="adminuser",
        password_hash=get_password_hash("AdminPassword123!"),
        first_name="Admin",
        last_name="User",
        status=UserStatus.ACTIVE,
        is_superuser=True,
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user) -> Dict[str, str]:
    """Generate authentication headers for test user."""
    token = create_access_token(
        user_id=str(test_user.id),
        email=test_user.email,
        tenant_id=str(test_user.tenant_id),
        roles=["user"],
        permissions=["read"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user) -> Dict[str, str]:
    """Generate authentication headers for admin user."""
    token = create_access_token(
        user_id=str(admin_user.id),
        email=admin_user.email,
        tenant_id=str(admin_user.tenant_id),
        roles=["admin"],
        permissions=["read", "write", "delete"],
    )
    return {"Authorization": f"Bearer {token}"}


# ========================================
# Account Fixtures
# ========================================

@pytest.fixture
async def test_accounts(db_session: AsyncSession):
    """Create a set of test accounting accounts."""
    from app.models.accounting import Account, AccountType, AccountCategory
    
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    
    accounts = {
        "cash": Account(
            id=uuid.uuid4(),
            code="1000",
            name="الصندوق",
            account_type=AccountType.ASSET,
            category=AccountCategory.CASH,
            tenant_id=tenant_id,
        ),
        "bank": Account(
            id=uuid.uuid4(),
            code="1100",
            name="البنك",
            account_type=AccountType.ASSET,
            category=AccountCategory.CASH,
            tenant_id=tenant_id,
        ),
        "inventory": Account(
            id=uuid.uuid4(),
            code="1200",
            name="المخزون",
            account_type=AccountType.ASSET,
            category=AccountCategory.INVENTORY,
            tenant_id=tenant_id,
        ),
        "receivable": Account(
            id=uuid.uuid4(),
            code="1300",
            name="العملاء",
            account_type=AccountType.ASSET,
            category=AccountCategory.RECEIVABLE,
            tenant_id=tenant_id,
        ),
        "payable": Account(
            id=uuid.uuid4(),
            code="2000",
            name="الموردون",
            account_type=AccountType.LIABILITY,
            category=AccountCategory.PAYABLE,
            tenant_id=tenant_id,
        ),
        "sales": Account(
            id=uuid.uuid4(),
            code="4000",
            name="المبيعات",
            account_type=AccountType.REVENUE,
            category=AccountCategory.SALES,
            tenant_id=tenant_id,
        ),
        "cogs": Account(
            id=uuid.uuid4(),
            code="5000",
            name="تكلفة البضاعة المباعة",
            account_type=AccountType.EXPENSE,
            category=AccountCategory.COST_OF_SALES,
            tenant_id=tenant_id,
        ),
        "wip": Account(
            id=uuid.uuid4(),
            code="1400",
            name="العمل تحت التنفيذ",
            account_type=AccountType.ASSET,
            category=AccountCategory.INVENTORY,
            tenant_id=tenant_id,
        ),
    }
    
    for account in accounts.values():
        db_session.add(account)
    
    await db_session.commit()
    
    # Refresh to get IDs
    for name, account in accounts.items():
        await db_session.refresh(account)
    
    return accounts


# ========================================
# Product Fixtures
# ========================================

@pytest.fixture
async def test_product(db_session: AsyncSession, test_accounts):
    """Create a test product."""
    from app.models.inventory import Product, ProductCategory
    
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    
    # Create category first
    category = ProductCategory(
        id=uuid.uuid4(),
        name="Test Category",
        code="TEST-CAT",
        tenant_id=tenant_id,
        asset_account_id=test_accounts["inventory"].id,
        expense_account_id=test_accounts["cogs"].id,
        income_account_id=test_accounts["sales"].id,
    )
    db_session.add(category)
    await db_session.flush()
    
    product = Product(
        id=uuid.uuid4(),
        name="Test Product",
        sku="TEST-001",
        cost_price=Decimal("100.00"),
        sale_price=Decimal("150.00"),
        is_stockable=True,
        category_id=category.id,
        asset_account_id=test_accounts["inventory"].id,
        expense_account_id=test_accounts["cogs"].id,
        income_account_id=test_accounts["sales"].id,
        tenant_id=tenant_id,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    
    return product


@pytest.fixture
async def test_products(db_session: AsyncSession, test_accounts):
    """Create multiple test products for inventory/manufacturing tests."""
    from app.models.inventory import Product
    
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    
    products = []
    for i in range(5):
        product = Product(
            id=uuid.uuid4(),
            name=f"Test Product {i+1}",
            sku=f"TEST-{i+1:03d}",
            cost_price=Decimal("100.00") + Decimal(str(i * 10)),
            sale_price=Decimal("150.00") + Decimal(str(i * 15)),
            is_stockable=True,
            asset_account_id=test_accounts["inventory"].id,
            expense_account_id=test_accounts["cogs"].id,
            income_account_id=test_accounts["sales"].id,
            tenant_id=tenant_id,
        )
        db_session.add(product)
        products.append(product)
    
    await db_session.commit()
    
    for product in products:
        await db_session.refresh(product)
    
    return products


# ========================================
# Partner Fixtures
# ========================================

@pytest.fixture
async def test_customer(db_session: AsyncSession, test_accounts):
    """Create a test customer."""
    from app.models.crm import Partner, PartnerType
    
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    
    customer = Partner(
        id=uuid.uuid4(),
        name="Test Customer",
        code="CUST-001",
        partner_type=PartnerType.CUSTOMER,
        email="customer@example.com",
        phone="+1234567890",
        receivable_account_id=test_accounts["receivable"].id,
        tenant_id=tenant_id,
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    
    return customer


@pytest.fixture
async def test_supplier(db_session: AsyncSession, test_accounts):
    """Create a test supplier."""
    from app.models.crm import Partner, PartnerType
    
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    
    supplier = Partner(
        id=uuid.uuid4(),
        name="Test Supplier",
        code="SUPP-001",
        partner_type=PartnerType.SUPPLIER,
        email="supplier@example.com",
        phone="+0987654321",
        payable_account_id=test_accounts["payable"].id,
        tenant_id=tenant_id,
    )
    db_session.add(supplier)
    await db_session.commit()
    await db_session.refresh(supplier)
    
    return supplier


# ========================================
# BOM Fixtures
# ========================================

@pytest.fixture
async def test_bom(db_session: AsyncSession, test_products, test_accounts):
    """Create a test Bill of Materials."""
    from app.models.manufacturing import BillOfMaterial, BOMLine, BOMType, BOMState
    
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    
    # Finished product
    finished_product = test_products[0]
    # Raw materials
    raw_materials = test_products[1:3]
    
    bom = BillOfMaterial(
        id=uuid.uuid4(),
        code=f"BOM-{finished_product.sku}",
        name=f"BOM for {finished_product.name}",
        product_id=finished_product.id,
        product_qty=Decimal("1"),
        bom_type=BOMType.MANUFACTURE,
        state=BOMState.ACTIVE,
        tenant_id=tenant_id,
    )
    db_session.add(bom)
    await db_session.flush()
    
    # Add BOM lines
    for i, material in enumerate(raw_materials):
        line = BOMLine(
            id=uuid.uuid4(),
            bom_id=bom.id,
            sequence=(i + 1) * 10,
            product_id=material.id,
            product_qty=Decimal("2"),
            unit_cost=material.cost_price,
            total_cost=material.cost_price * Decimal("2"),
            tenant_id=tenant_id,
        )
        db_session.add(line)
    
    await db_session.commit()
    await db_session.refresh(bom)
    
    return bom


# ========================================
# Utility Fixtures
# ========================================

@pytest.fixture
def anyio_backend():
    """Set anyio backend to asyncio."""
    return "asyncio"


@pytest.fixture
def tenant_id():
    """Default tenant ID for tests."""
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def sample_invoice_data(test_product, test_customer):
    """Sample data for creating a sales invoice."""
    return {
        "partner_id": str(test_customer.id),
        "date_invoice": str(date.today()),
        "lines": [
            {
                "product_id": str(test_product.id),
                "quantity": 5,
                "unit_price": float(test_product.sale_price),
            }
        ]
    }


@pytest.fixture
def sample_journal_entry_data(test_accounts):
    """Sample data for creating a journal entry."""
    return {
        "date": str(date.today()),
        "description": "Test Journal Entry",
        "lines": [
            {
                "account_id": str(test_accounts["cash"].id),
                "debit": Decimal("1000"),
                "credit": Decimal("0"),
                "name": "Cash received"
            },
            {
                "account_id": str(test_accounts["sales"].id),
                "debit": Decimal("0"),
                "credit": Decimal("1000"),
                "name": "Sales revenue"
            }
        ]
    }


# ========================================
# Mock Fixtures for External Services
# ========================================

@pytest.fixture
def mock_ai_response():
    """Mock response for AI services."""
    return {
        "predictions": [
            {"date": "2024-02-01", "quantity": 100, "lower": 90, "upper": 110},
            {"date": "2024-03-01", "quantity": 110, "lower": 95, "upper": 125},
            {"date": "2024-04-01", "quantity": 120, "lower": 100, "upper": 140},
        ]
    }


@pytest.fixture
def mock_ocr_response():
    """Mock response for OCR service."""
    return {
        "invoice_number": "INV-2024-001",
        "invoice_date": "2024-01-15",
        "supplier_name": "Test Supplier Co.",
        "total_amount": 1500.00,
        "line_items": [
            {"description": "Item 1", "quantity": 10, "unit_price": 100.00},
            {"description": "Item 2", "quantity": 5, "unit_price": 100.00},
        ]
    }
