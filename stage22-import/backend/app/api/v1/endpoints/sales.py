"""
Nexus ERP - Sales API Endpoints
================================

REST API endpoints for the Sales module.
"""

from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.user import User
from app.models.sales import QuotationState, SaleOrderState, InvoiceType, InvoiceState
from app.services.sales_service import SalesService
from app.schemas.sales import (
    QuotationCreate, QuotationUpdate, QuotationResponse, QuotationListResponse,
    SaleOrderCreate, SaleOrderUpdate, SaleOrderResponse, SaleOrderListResponse,
    InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceListResponse,
    PaymentCreate, PaymentResponse, PaymentListResponse,
    QuotationSendRequest, QuotationConfirmRequest,
    SaleOrderConfirmRequest, InvoicePostRequest, PaymentRegisterRequest
)

router = APIRouter(prefix="/sales", tags=["Sales"])


# ========================================
# Quotation Endpoints
# ========================================

@router.get("/quotations", response_model=QuotationListResponse)
async def list_quotations(
    state: Optional[QuotationState] = None,
    partner_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List quotations with optional filters."""
    await require_permission(current_user, "sales.quotation.read")
    
    service = SalesService(db)
    quotations, total = await service.list_quotations(
        tenant_id=current_user.tenant_id,
        state=state,
        partner_id=partner_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size
    )
    
    return QuotationListResponse(
        items=[QuotationResponse.model_validate(q) for q in quotations],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/quotations", response_model=QuotationResponse, status_code=status.HTTP_201_CREATED)
async def create_quotation(
    data: QuotationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new quotation."""
    await require_permission(current_user, "sales.quotation.create")
    
    service = SalesService(db)
    quotation = await service.create_quotation(
        tenant_id=current_user.tenant_id,
        data=data.model_dump(),
        user_id=current_user.id
    )
    
    return QuotationResponse.model_validate(quotation)


@router.get("/quotations/{quotation_id}", response_model=QuotationResponse)
async def get_quotation(
    quotation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific quotation."""
    await require_permission(current_user, "sales.quotation.read")
    
    service = SalesService(db)
    quotation = await service._get_quotation(quotation_id, current_user.tenant_id)
    
    return QuotationResponse.model_validate(quotation)


@router.put("/quotations/{quotation_id}", response_model=QuotationResponse)
async def update_quotation(
    quotation_id: UUID,
    data: QuotationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a quotation."""
    await require_permission(current_user, "sales.quotation.update")
    
    service = SalesService(db)
    quotation = await service._get_quotation(quotation_id, current_user.tenant_id)
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True, exclude={"lines"})
    for field, value in update_data.items():
        setattr(quotation, field, value)
    
    # Update lines if provided
    if data.lines:
        # Delete existing lines
        for line in quotation.lines:
            await db.delete(line)
        
        # Create new lines
        from app.models.sales import QuotationLine
        for line_data in data.lines:
            line = QuotationLine(
                tenant_id=current_user.tenant_id,
                quotation_id=quotation.id,
                **line_data.model_dump()
            )
            line.calculate_subtotal()
            db.add(line)
    
    quotation.calculate_totals()
    await db.commit()
    await db.refresh(quotation)
    
    return QuotationResponse.model_validate(quotation)


@router.post("/quotations/{quotation_id}/send", response_model=QuotationResponse)
async def send_quotation(
    quotation_id: UUID,
    data: Optional[QuotationSendRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a quotation to the customer."""
    await require_permission(current_user, "sales.quotation.update")
    
    service = SalesService(db)
    quotation = await service.send_quotation(
        quotation_id=quotation_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )
    
    return QuotationResponse.model_validate(quotation)


@router.post("/quotations/{quotation_id}/confirm", response_model=SaleOrderResponse)
async def confirm_quotation(
    quotation_id: UUID,
    data: Optional[QuotationConfirmRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm quotation and create sale order."""
    await require_permission(current_user, "sales.quotation.update")
    
    service = SalesService(db)
    create_order = data.create_order if data else True
    
    order = await service.confirm_quotation(
        quotation_id=quotation_id,
        tenant_id=current_user.tenant_id,
        create_order=create_order,
        user_id=current_user.id
    )
    
    if order:
        return SaleOrderResponse.model_validate(order)
    raise HTTPException(status_code=400, detail="Failed to create sale order")


@router.post("/quotations/{quotation_id}/cancel", response_model=QuotationResponse)
async def cancel_quotation(
    quotation_id: UUID,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a quotation."""
    await require_permission(current_user, "sales.quotation.update")
    
    service = SalesService(db)
    quotation = await service.cancel_quotation(
        quotation_id=quotation_id,
        tenant_id=current_user.tenant_id,
        reason=reason,
        user_id=current_user.id
    )
    
    return QuotationResponse.model_validate(quotation)


# ========================================
# Sale Order Endpoints
# ========================================

@router.get("/orders", response_model=SaleOrderListResponse)
async def list_sale_orders(
    state: Optional[SaleOrderState] = None,
    partner_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List sale orders with optional filters."""
    await require_permission(current_user, "sales.order.read")
    
    service = SalesService(db)
    orders, total = await service.list_sale_orders(
        tenant_id=current_user.tenant_id,
        state=state,
        partner_id=partner_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size
    )
    
    return SaleOrderListResponse(
        items=[SaleOrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/orders", response_model=SaleOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_sale_order(
    data: SaleOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new sale order."""
    await require_permission(current_user, "sales.order.create")
    
    service = SalesService(db)
    order = await service.create_sale_order(
        tenant_id=current_user.tenant_id,
        data=data.model_dump(),
        user_id=current_user.id
    )
    
    return SaleOrderResponse.model_validate(order)


@router.get("/orders/{order_id}", response_model=SaleOrderResponse)
async def get_sale_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific sale order."""
    await require_permission(current_user, "sales.order.read")
    
    service = SalesService(db)
    order = await service._get_sale_order(order_id, current_user.tenant_id)
    
    return SaleOrderResponse.model_validate(order)


@router.post("/orders/{order_id}/confirm", response_model=SaleOrderResponse)
async def confirm_sale_order(
    order_id: UUID,
    data: Optional[SaleOrderConfirmRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm a sale order."""
    await require_permission(current_user, "sales.order.update")
    
    service = SalesService(db)
    create_delivery = data.create_delivery if data else True
    create_invoice = data.create_invoice if data else False
    
    order = await service.confirm_sale_order(
        order_id=order_id,
        tenant_id=current_user.tenant_id,
        create_delivery=create_delivery,
        create_invoice=create_invoice,
        user_id=current_user.id
    )
    
    return SaleOrderResponse.model_validate(order)


@router.post("/orders/{order_id}/cancel", response_model=SaleOrderResponse)
async def cancel_sale_order(
    order_id: UUID,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a sale order."""
    await require_permission(current_user, "sales.order.update")
    
    service = SalesService(db)
    order = await service.cancel_sale_order(
        order_id=order_id,
        tenant_id=current_user.tenant_id,
        reason=reason,
        user_id=current_user.id
    )
    
    return SaleOrderResponse.model_validate(order)


@router.post("/orders/{order_id}/invoice", response_model=InvoiceResponse)
async def create_invoice_from_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create invoice from sale order."""
    await require_permission(current_user, "sales.invoice.create")
    
    service = SalesService(db)
    invoice = await service.create_invoice_from_order(
        order_id=order_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )
    
    return InvoiceResponse.model_validate(invoice)


# ========================================
# Invoice Endpoints
# ========================================

@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    invoice_type: Optional[InvoiceType] = None,
    state: Optional[InvoiceState] = None,
    partner_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List invoices with optional filters."""
    await require_permission(current_user, "sales.invoice.read")
    
    service = SalesService(db)
    invoices, total = await service.list_invoices(
        tenant_id=current_user.tenant_id,
        invoice_type=invoice_type,
        state=state,
        partner_id=partner_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size
    )
    
    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(i) for i in invoices],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new invoice."""
    await require_permission(current_user, "sales.invoice.create")
    
    service = SalesService(db)
    invoice = await service.create_invoice(
        tenant_id=current_user.tenant_id,
        data=data.model_dump(),
        user_id=current_user.id
    )
    
    return InvoiceResponse.model_validate(invoice)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific invoice."""
    await require_permission(current_user, "sales.invoice.read")
    
    service = SalesService(db)
    invoice = await service._get_invoice(invoice_id, current_user.tenant_id)
    
    return InvoiceResponse.model_validate(invoice)


@router.post("/invoices/{invoice_id}/post", response_model=InvoiceResponse)
async def post_invoice(
    invoice_id: UUID,
    data: Optional[InvoicePostRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Post an invoice."""
    await require_permission(current_user, "sales.invoice.update")
    
    service = SalesService(db)
    date_posted = data.date_posted if data else None
    
    invoice = await service.post_invoice(
        invoice_id=invoice_id,
        tenant_id=current_user.tenant_id,
        date_posted=date_posted,
        user_id=current_user.id
    )
    
    return InvoiceResponse.model_validate(invoice)


@router.post("/invoices/{invoice_id}/register-payment", response_model=PaymentResponse)
async def register_payment(
    invoice_id: UUID,
    data: PaymentRegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Register a payment for an invoice."""
    await require_permission(current_user, "sales.payment.create")
    
    service = SalesService(db)
    payment = await service.register_payment(
        invoice_id=invoice_id,
        tenant_id=current_user.tenant_id,
        amount=data.amount,
        date=data.date,
        journal_id=data.journal_id,
        payment_method_id=data.payment_method_id,
        reference=data.reference,
        user_id=current_user.id
    )
    
    return PaymentResponse.model_validate(payment)
