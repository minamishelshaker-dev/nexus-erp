"""
Nexus ERP - Purchase API Endpoints
===================================

REST API endpoints for the Purchase module.
"""

from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.user import User
from app.models.purchase import PurchaseOrderState, ReceiptState, PurchaseInvoiceState
from app.services.purchase_service import PurchaseService
from app.schemas.purchase import (
    PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse, PurchaseOrderListResponse,
    ReceiptCreate, ReceiptUpdate, ReceiptResponse, ReceiptListResponse,
    PurchaseInvoiceCreate, PurchaseInvoiceUpdate, PurchaseInvoiceResponse, PurchaseInvoiceListResponse,
    PurchaseOrderConfirmRequest, ReceiptConfirmRequest, PurchaseInvoicePostRequest,
    CreateReceiptFromPORequest, SupplierPaymentRegisterRequest, SupplierPaymentCancelRequest, SupplierPaymentResponse
)

router = APIRouter(prefix="/purchase", tags=["Purchase"])


# ========================================
# Purchase Order Endpoints
# ========================================

@router.get("/orders", response_model=PurchaseOrderListResponse)
async def list_purchase_orders(
    state: Optional[PurchaseOrderState] = None,
    partner_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List purchase orders with optional filters."""
    await require_permission(current_user, "purchase.order.read")
    
    service = PurchaseService(db)
    orders, total = await service.list_purchase_orders(
        tenant_id=current_user.tenant_id,
        state=state,
        partner_id=partner_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size
    )
    
    return PurchaseOrderListResponse(
        items=[PurchaseOrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/orders", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    data: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new purchase order."""
    await require_permission(current_user, "purchase.order.create")
    
    service = PurchaseService(db)
    order = await service.create_purchase_order(
        tenant_id=current_user.tenant_id,
        data=data.model_dump(),
        user_id=current_user.id
    )
    
    return PurchaseOrderResponse.model_validate(order)


@router.get("/orders/{order_id}", response_model=PurchaseOrderResponse)
async def get_purchase_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific purchase order."""
    await require_permission(current_user, "purchase.order.read")
    
    service = PurchaseService(db)
    order = await service._get_purchase_order(order_id, current_user.tenant_id)
    
    return PurchaseOrderResponse.model_validate(order)


@router.put("/orders/{order_id}", response_model=PurchaseOrderResponse)
async def update_purchase_order(
    order_id: UUID,
    data: PurchaseOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a purchase order."""
    await require_permission(current_user, "purchase.order.update")
    
    service = PurchaseService(db)
    order = await service._get_purchase_order(order_id, current_user.tenant_id)
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True, exclude={"lines"})
    for field, value in update_data.items():
        setattr(order, field, value)
    
    # Update lines if provided
    if data.lines:
        for line in order.lines:
            await db.delete(line)
        
        from app.models.purchase import PurchaseOrderLine
        for line_data in data.lines:
            line = PurchaseOrderLine(
                tenant_id=current_user.tenant_id,
                order_id=order.id,
                **line_data.model_dump()
            )
            line.calculate_subtotal()
            db.add(line)
    
    order.calculate_totals()
    await db.commit()
    await db.refresh(order)
    
    return PurchaseOrderResponse.model_validate(order)


@router.post("/orders/{order_id}/confirm", response_model=PurchaseOrderResponse)
async def confirm_purchase_order(
    order_id: UUID,
    data: Optional[PurchaseOrderConfirmRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm a purchase order."""
    await require_permission(current_user, "purchase.order.update")
    
    service = PurchaseService(db)
    approve = data.approve if data else False
    
    order = await service.confirm_purchase_order(
        order_id=order_id,
        tenant_id=current_user.tenant_id,
        approve=approve,
        user_id=current_user.id
    )
    
    return PurchaseOrderResponse.model_validate(order)


@router.post("/orders/{order_id}/approve", response_model=PurchaseOrderResponse)
async def approve_purchase_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a confirmed purchase order."""
    await require_permission(current_user, "purchase.order.approve")
    
    service = PurchaseService(db)
    order = await service.approve_purchase_order(
        order_id=order_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )
    
    return PurchaseOrderResponse.model_validate(order)


@router.post("/orders/{order_id}/cancel", response_model=PurchaseOrderResponse)
async def cancel_purchase_order(
    order_id: UUID,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a purchase order."""
    await require_permission(current_user, "purchase.order.update")
    
    service = PurchaseService(db)
    order = await service.cancel_purchase_order(
        order_id=order_id,
        tenant_id=current_user.tenant_id,
        reason=reason,
        user_id=current_user.id
    )
    
    return PurchaseOrderResponse.model_validate(order)


# ========================================
# Receipt Endpoints
# ========================================

@router.get("/receipts", response_model=ReceiptListResponse)
async def list_receipts(
    state: Optional[ReceiptState] = None,
    partner_id: Optional[UUID] = None,
    purchase_order_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List receipts with optional filters."""
    await require_permission(current_user, "purchase.receipt.read")
    
    service = PurchaseService(db)
    receipts, total = await service.list_receipts(
        tenant_id=current_user.tenant_id,
        state=state,
        partner_id=partner_id,
        purchase_order_id=purchase_order_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size
    )
    
    return ReceiptListResponse(
        items=[ReceiptResponse.model_validate(r) for r in receipts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/receipts", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED)
async def create_receipt(
    data: ReceiptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new receipt."""
    await require_permission(current_user, "purchase.receipt.create")
    
    service = PurchaseService(db)
    receipt = await service.create_receipt(
        tenant_id=current_user.tenant_id,
        data=data.model_dump(),
        user_id=current_user.id
    )
    
    return ReceiptResponse.model_validate(receipt)


@router.post("/receipts/from-order", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED)
async def create_receipt_from_order(
    data: CreateReceiptFromPORequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create receipt from purchase order."""
    await require_permission(current_user, "purchase.receipt.create")
    
    service = PurchaseService(db)
    receipt = await service.create_receipt_from_order(
        order_id=data.purchase_order_id,
        tenant_id=current_user.tenant_id,
        lines=data.lines,
        warehouse_id=data.warehouse_id,
        location_id=data.location_id,
        user_id=current_user.id
    )
    
    return ReceiptResponse.model_validate(receipt)


@router.get("/receipts/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(
    receipt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific receipt."""
    await require_permission(current_user, "purchase.receipt.read")
    
    service = PurchaseService(db)
    receipt = await service._get_receipt(receipt_id, current_user.tenant_id)
    
    return ReceiptResponse.model_validate(receipt)


@router.post("/receipts/{receipt_id}/confirm", response_model=ReceiptResponse)
async def confirm_receipt(
    receipt_id: UUID,
    data: Optional[ReceiptConfirmRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm a receipt - process the goods receipt."""
    await require_permission(current_user, "purchase.receipt.update")
    
    service = PurchaseService(db)
    date_done = data.date_done if data else None
    create_invoice = data.create_invoice if data else False
    
    receipt = await service.confirm_receipt(
        receipt_id=receipt_id,
        tenant_id=current_user.tenant_id,
        date_done=date_done,
        create_invoice=create_invoice,
        user_id=current_user.id
    )
    
    return ReceiptResponse.model_validate(receipt)


@router.post("/receipts/{receipt_id}/cancel", response_model=ReceiptResponse)
async def cancel_receipt(
    receipt_id: UUID,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a receipt."""
    await require_permission(current_user, "purchase.receipt.update")
    
    service = PurchaseService(db)
    receipt = await service.cancel_receipt(
        receipt_id=receipt_id,
        tenant_id=current_user.tenant_id,
        reason=reason,
        user_id=current_user.id
    )
    
    return ReceiptResponse.model_validate(receipt)


# ========================================
# Purchase Invoice Endpoints
# ========================================

@router.get("/invoices", response_model=PurchaseInvoiceListResponse)
async def list_purchase_invoices(
    state: Optional[PurchaseInvoiceState] = None,
    partner_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List purchase invoices with optional filters."""
    await require_permission(current_user, "purchase.invoice.read")
    
    service = PurchaseService(db)
    invoices, total = await service.list_purchase_invoices(
        tenant_id=current_user.tenant_id,
        state=state,
        partner_id=partner_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size
    )
    
    return PurchaseInvoiceListResponse(
        items=[PurchaseInvoiceResponse.model_validate(i) for i in invoices],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/invoices", response_model=PurchaseInvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_invoice(
    data: PurchaseInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new purchase invoice (vendor bill)."""
    await require_permission(current_user, "purchase.invoice.create")
    
    service = PurchaseService(db)
    invoice = await service.create_purchase_invoice(
        tenant_id=current_user.tenant_id,
        data=data.model_dump(),
        user_id=current_user.id
    )
    
    return PurchaseInvoiceResponse.model_validate(invoice)


@router.get("/invoices/{invoice_id}", response_model=PurchaseInvoiceResponse)
async def get_purchase_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific purchase invoice."""
    await require_permission(current_user, "purchase.invoice.read")
    
    service = PurchaseService(db)
    invoice = await service._get_purchase_invoice(invoice_id, current_user.tenant_id)
    
    return PurchaseInvoiceResponse.model_validate(invoice)


@router.post("/invoices/{invoice_id}/post", response_model=PurchaseInvoiceResponse)
async def post_purchase_invoice(
    invoice_id: UUID,
    data: Optional[PurchaseInvoicePostRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Post a purchase invoice."""
    await require_permission(current_user, "purchase.invoice.update")
    
    service = PurchaseService(db)
    date_posted = data.date_posted if data else None
    
    invoice = await service.post_purchase_invoice(
        invoice_id=invoice_id,
        tenant_id=current_user.tenant_id,
        date_posted=date_posted,
        user_id=current_user.id
    )
    
    return PurchaseInvoiceResponse.model_validate(invoice)


@router.post("/invoices/from-receipt", response_model=PurchaseInvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice_from_receipt(
    receipt_id: UUID,
    date_invoice: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create purchase invoice from receipt."""
    await require_permission(current_user, "purchase.invoice.create")
    
    service = PurchaseService(db)
    invoice = await service.create_invoice_from_receipt(
        receipt_id=receipt_id,
        tenant_id=current_user.tenant_id,
        date_invoice=date_invoice,
        user_id=current_user.id
    )
    
    return PurchaseInvoiceResponse.model_validate(invoice)


@router.post("/supplier-payments/{payment_id}/cancel", response_model=SupplierPaymentResponse)
async def cancel_supplier_payment(
    payment_id: UUID,
    data: SupplierPaymentCancelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a posted supplier payment using an auditable journal reversal."""
    await require_permission(current_user, "purchase.invoice.update")
    await require_permission(current_user, "accounting.journal.reverse")
    service = PurchaseService(db)
    try:
        payment = await service.cancel_supplier_payment(
            payment_id=payment_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            reversal_date=data.reversal_date,
            reason=data.reason,
        )
        return SupplierPaymentResponse.model_validate(payment)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        await db.rollback()
        raise


@router.post("/supplier-payments", response_model=SupplierPaymentResponse, status_code=status.HTTP_201_CREATED)
async def register_supplier_payment(
    data: SupplierPaymentRegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register and post a supplier payment allocated to existing vendor bills."""
    await require_permission(current_user, "purchase.invoice.update")
    service = PurchaseService(db)
    payment = await service.register_supplier_payment(
        tenant_id=current_user.tenant_id,
        supplier_id=data.supplier_id,
        payment_date=data.payment_date,
        amount=data.amount,
        journal_id=data.journal_id,
        bank_account_id=data.bank_account_id,
        allocations=[item.model_dump() for item in data.allocations],
        user_id=current_user.id,
        reference=data.reference,
        notes=data.notes,
    )
    return SupplierPaymentResponse.model_validate(payment)
