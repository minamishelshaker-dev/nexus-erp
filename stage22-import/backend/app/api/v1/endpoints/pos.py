"""
Nexus ERP - POS API Endpoints
=============================

REST API endpoints for Point of Sale.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, Field
from decimal import Decimal

from app.core.database import db_manager
from app.core.security import get_current_user

router = APIRouter(prefix="/pos", tags=["Point of Sale"])


# ========================================
# Pydantic Schemas
# ========================================

class POSConfigBase(BaseModel):
    name: str
    warehouse_id: UUID
    default_customer_id: Optional[UUID] = None
    receipt_header: Optional[str] = None
    receipt_footer: Optional[str] = None


class POSConfigResponse(POSConfigBase):
    id: UUID
    is_active: bool = True
    
    class Config:
        from_attributes = True


class POSSessionBase(BaseModel):
    config_id: UUID
    opening_balance: float = 0


class POSSessionResponse(POSSessionBase):
    id: UUID
    status: str = "open"
    opening_date: datetime
    closing_date: Optional[datetime] = None
    closing_balance: Optional[float] = None
    total_sales: float = 0
    total_orders: int = 0
    
    class Config:
        from_attributes = True


class POSOrderLineBase(BaseModel):
    product_id: UUID
    quantity: float
    price_unit: float
    discount: float = 0


class POSOrderBase(BaseModel):
    session_id: UUID
    customer_id: Optional[UUID] = None
    lines: List[POSOrderLineBase]
    payment_method: str = "cash"
    amount_received: Optional[float] = None
    notes: Optional[str] = None


class POSOrderResponse(BaseModel):
    id: UUID
    number: str
    session_id: UUID
    customer_id: Optional[UUID] = None
    amount_untaxed: float
    amount_tax: float
    amount_total: float
    payment_method: str
    amount_received: float
    change: float
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProductQuickView(BaseModel):
    id: UUID
    name: str
    sku: str
    list_price: float
    quantity_available: float
    image_url: Optional[str] = None
    
    class Config:
        from_attributes = True


# ========================================
# POS Config Endpoints
# ========================================

@router.get("/configs", response_model=List[POSConfigResponse])
async def list_pos_configs(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List POS configurations."""
    # Placeholder - would query actual POSConfig model
    return [
        POSConfigResponse(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Main POS",
            warehouse_id=UUID("00000000-0000-0000-0000-000000000001"),
            is_active=True,
            receipt_header="Nexus ERP Store",
            receipt_footer="Thank you for your purchase!"
        )
    ]


@router.get("/configs/{config_id}", response_model=POSConfigResponse)
async def get_pos_config(
    config_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Get POS configuration."""
    return POSConfigResponse(
        id=config_id,
        name="Main POS",
        warehouse_id=UUID("00000000-0000-0000-0000-000000000001"),
        is_active=True
    )


# ========================================
# POS Session Endpoints
# ========================================

@router.get("/sessions", response_model=List[POSSessionResponse])
async def list_pos_sessions(
    status: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List POS sessions."""
    # Placeholder
    return []


@router.post("/sessions", response_model=POSSessionResponse, status_code=status.HTTP_201_CREATED)
async def open_pos_session(
    data: POSSessionBase,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Open a new POS session."""
    # Placeholder
    return POSSessionResponse(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        config_id=data.config_id,
        opening_balance=data.opening_balance,
        status="open",
        opening_date=datetime.utcnow()
    )


@router.post("/sessions/{session_id}/close")
async def close_pos_session(
    session_id: UUID,
    closing_balance: float,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Close a POS session."""
    return {
        "success": True,
        "session_id": str(session_id),
        "closing_balance": closing_balance,
        "closing_date": datetime.utcnow().isoformat()
    }


# ========================================
# POS Products (Quick Access)
# ========================================

@router.get("/products", response_model=List[ProductQuickView])
async def list_pos_products(
    search: Optional[str] = None,
    category_id: Optional[UUID] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List products for POS (optimized for quick access)."""
    # This would query the products table with POS-specific filters
    return [
        ProductQuickView(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Sample Product",
            sku="PROD-001",
            list_price=99.99,
            quantity_available=100
        ),
        ProductQuickView(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            name="Another Product",
            sku="PROD-002",
            list_price=49.99,
            quantity_available=50
        )
    ]


@router.get("/products/{product_id}", response_model=ProductQuickView)
async def get_pos_product(
    product_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Get product details for POS."""
    return ProductQuickView(
        id=product_id,
        name="Sample Product",
        sku="PROD-001",
        list_price=99.99,
        quantity_available=100
    )


# ========================================
# POS Orders
# ========================================

@router.post("/orders", response_model=POSOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_pos_order(
    data: POSOrderBase,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Create a POS order (complete sale)."""
    # Calculate totals
    amount_untaxed = sum(line.quantity * line.price_unit * (1 - line.discount / 100) for line in data.lines)
    tax_rate = 0.15  # 15% VAT
    amount_tax = amount_untaxed * tax_rate
    amount_total = amount_untaxed + amount_tax
    
    amount_received = data.amount_received or amount_total
    change = amount_received - amount_total
    
    return POSOrderResponse(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        number=f"POS-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        session_id=data.session_id,
        customer_id=data.customer_id,
        amount_untaxed=amount_untaxed,
        amount_tax=amount_tax,
        amount_total=amount_total,
        payment_method=data.payment_method,
        amount_received=amount_received,
        change=max(0, change),
        status="paid",
        created_at=datetime.utcnow()
    )


@router.get("/orders", response_model=List[POSOrderResponse])
async def list_pos_orders(
    session_id: Optional[UUID] = None,
    date: Optional[date] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """List POS orders."""
    return []


@router.get("/orders/{order_id}", response_model=POSOrderResponse)
async def get_pos_order(
    order_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Get POS order details."""
    return POSOrderResponse(
        id=order_id,
        number="POS-20240101120000",
        session_id=UUID("00000000-0000-0000-0000-000000000001"),
        amount_untaxed=100.00,
        amount_tax=15.00,
        amount_total=115.00,
        payment_method="cash",
        amount_received=120.00,
        change=5.00,
        status="paid",
        created_at=datetime.utcnow()
    )


@router.post("/orders/{order_id}/refund")
async def refund_pos_order(
    order_id: UUID,
    reason: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_session)
):
    """Process a refund for a POS order."""
    return {
        "success": True,
        "order_id": str(order_id),
        "refund_reason": reason,
        "status": "refunded"
    }


# ========================================
# Payment Methods
# ========================================

@router.get("/payment-methods")
async def list_payment_methods():
    """List available payment methods."""
    return [
        {"code": "cash", "name": "Cash", "icon": "banknote"},
        {"code": "card", "name": "Credit/Debit Card", "icon": "credit-card"},
        {"code": "mobile", "name": "Mobile Payment", "icon": "smartphone"},
    ]
