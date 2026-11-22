"""
Nexus ERP - Purchase Module Schemas
====================================

Pydantic schemas for the Purchase module API.
"""

from datetime import datetime, date as Date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ========================================
# Enums
# ========================================

class PurchaseOrderStateEnum(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    APPROVED = "approved"
    DONE = "done"
    CANCELLED = "cancelled"


class ReceiptStateEnum(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    DONE = "done"
    CANCELLED = "cancelled"


class PurchaseInvoiceStateEnum(str, Enum):
    DRAFT = "draft"
    POSTED = "posted"
    PAID = "paid"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


# ========================================
# Purchase Order Line Schemas
# ========================================

class PurchaseOrderLineBase(BaseModel):
    """Base schema for purchase order line."""
    product_id: Optional[UUID] = None
    description: str = Field(..., min_length=1, max_length=2000)
    quantity: Decimal = Field(..., gt=0)
    uom_id: Optional[UUID] = None
    price_unit: Decimal = Field(..., ge=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    tax_ids: List[str] = Field(default_factory=list)
    date_planned: Optional[Date] = None
    analytic_account_id: Optional[UUID] = None
    notes: Optional[str] = None


class PurchaseOrderLineCreate(PurchaseOrderLineBase):
    """Schema for creating purchase order line."""
    pass


class PurchaseOrderLineUpdate(BaseModel):
    """Schema for updating purchase order line."""
    product_id: Optional[UUID] = None
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    quantity: Optional[Decimal] = Field(None, gt=0)
    uom_id: Optional[UUID] = None
    price_unit: Optional[Decimal] = Field(None, ge=0)
    discount: Optional[Decimal] = Field(None, ge=0, le=100)
    tax_ids: Optional[List[str]] = None
    date_planned: Optional[Date] = None
    analytic_account_id: Optional[UUID] = None
    notes: Optional[str] = None


class PurchaseOrderLineResponse(PurchaseOrderLineBase):
    """Schema for purchase order line response."""
    id: UUID
    order_id: UUID
    sequence: int
    quantity_received: Decimal
    quantity_billed: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    subtotal: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========================================
# Purchase Order Schemas
# ========================================

class PurchaseOrderBase(BaseModel):
    """Base schema for purchase order."""
    name: str = Field(..., min_length=1, max_length=255)
    partner_id: UUID
    partner_ref: Optional[str] = None
    date_order: Date
    date_planned: Optional[Date] = None
    incoterm_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    purchaser_id: Optional[UUID] = None
    payment_term_id: Optional[UUID] = None
    currency_id: Optional[UUID] = None
    exchange_rate: Decimal = Field(default=Decimal("1"))
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None


class PurchaseOrderCreate(PurchaseOrderBase):
    """Schema for creating purchase order."""
    lines: List[PurchaseOrderLineCreate] = Field(..., min_length=1)


class PurchaseOrderUpdate(BaseModel):
    """Schema for updating purchase order."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    partner_id: Optional[UUID] = None
    partner_ref: Optional[str] = None
    date_order: Optional[Date] = None
    date_planned: Optional[Date] = None
    incoterm_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    purchaser_id: Optional[UUID] = None
    payment_term_id: Optional[UUID] = None
    currency_id: Optional[UUID] = None
    exchange_rate: Optional[Decimal] = None
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None
    lines: Optional[List[PurchaseOrderLineCreate]] = None


class PurchaseOrderResponse(PurchaseOrderBase):
    """Schema for purchase order response."""
    id: UUID
    number: str
    state: PurchaseOrderStateEnum
    amount_untaxed: Decimal
    amount_tax: Decimal
    amount_discount: Decimal
    amount_total: Decimal
    amount_billed: Decimal
    receipt_status: str
    invoice_status: str
    date_confirm: Optional[Date]
    date_approve: Optional[Date]
    confirmed_at: Optional[datetime]
    done_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    lines: List[PurchaseOrderLineResponse] = []

    class Config:
        from_attributes = True


class PurchaseOrderListResponse(BaseModel):
    """Schema for purchase order list response."""
    items: List[PurchaseOrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ========================================
# Receipt Line Schemas
# ========================================

class ReceiptLineBase(BaseModel):
    """Base schema for receipt line."""
    product_id: UUID
    description: Optional[str] = None
    quantity: Decimal = Field(..., gt=0)
    uom_id: Optional[UUID] = None
    purchase_line_id: Optional[UUID] = None
    lot_id: Optional[UUID] = None
    lot_name: Optional[str] = None
    expiration_date: Optional[Date] = None
    notes: Optional[str] = None


class ReceiptLineCreate(ReceiptLineBase):
    """Schema for creating receipt line."""
    pass


class ReceiptLineUpdate(BaseModel):
    """Schema for updating receipt line."""
    product_id: Optional[UUID] = None
    description: Optional[str] = None
    quantity: Optional[Decimal] = Field(None, gt=0)
    uom_id: Optional[UUID] = None
    purchase_line_id: Optional[UUID] = None
    lot_id: Optional[UUID] = None
    lot_name: Optional[str] = None
    expiration_date: Optional[Date] = None
    notes: Optional[str] = None


class ReceiptLineResponse(ReceiptLineBase):
    """Schema for receipt line response."""
    id: UUID
    receipt_id: UUID
    sequence: int
    quantity_done: Decimal
    stock_move_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========================================
# Receipt Schemas
# ========================================

class ReceiptBase(BaseModel):
    """Base schema for receipt."""
    name: str = Field(..., min_length=1, max_length=255)
    partner_id: UUID
    purchase_order_id: Optional[UUID] = None
    date: Date
    warehouse_id: Optional[UUID] = None
    location_id: Optional[UUID] = None
    notes: Optional[str] = None


class ReceiptCreate(ReceiptBase):
    """Schema for creating receipt."""
    lines: List[ReceiptLineCreate] = Field(..., min_length=1)


class ReceiptUpdate(BaseModel):
    """Schema for updating receipt."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    partner_id: Optional[UUID] = None
    purchase_order_id: Optional[UUID] = None
    date: Optional[Date] = None
    warehouse_id: Optional[UUID] = None
    location_id: Optional[UUID] = None
    notes: Optional[str] = None
    lines: Optional[List[ReceiptLineCreate]] = None


class ReceiptResponse(ReceiptBase):
    """Schema for receipt response."""
    id: UUID
    number: str
    state: ReceiptStateEnum
    date_done: Optional[Date]
    confirmed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    lines: List[ReceiptLineResponse] = []

    class Config:
        from_attributes = True


class ReceiptListResponse(BaseModel):
    """Schema for receipt list response."""
    items: List[ReceiptResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ========================================
# Purchase Invoice Line Schemas
# ========================================

class PurchaseInvoiceLineBase(BaseModel):
    """Base schema for purchase invoice line."""
    product_id: Optional[UUID] = None
    description: str = Field(..., min_length=1, max_length=2000)
    quantity: Decimal = Field(..., gt=0)
    uom_id: Optional[UUID] = None
    price_unit: Decimal = Field(..., ge=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    tax_ids: List[str] = Field(default_factory=list)
    account_id: UUID
    analytic_account_id: Optional[UUID] = None
    notes: Optional[str] = None


class PurchaseInvoiceLineCreate(PurchaseInvoiceLineBase):
    """Schema for creating purchase invoice line."""
    pass


class PurchaseInvoiceLineUpdate(BaseModel):
    """Schema for updating purchase invoice line."""
    product_id: Optional[UUID] = None
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    quantity: Optional[Decimal] = Field(None, gt=0)
    uom_id: Optional[UUID] = None
    price_unit: Optional[Decimal] = Field(None, ge=0)
    discount: Optional[Decimal] = Field(None, ge=0, le=100)
    tax_ids: Optional[List[str]] = None
    account_id: Optional[UUID] = None
    analytic_account_id: Optional[UUID] = None
    notes: Optional[str] = None


class PurchaseInvoiceLineResponse(PurchaseInvoiceLineBase):
    """Schema for purchase invoice line response."""
    id: UUID
    invoice_id: UUID
    sequence: int
    discount_amount: Decimal
    tax_amount: Decimal
    subtotal: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========================================
# Purchase Invoice Schemas
# ========================================

class PurchaseInvoiceBase(BaseModel):
    """Base schema for purchase invoice."""
    name: str = Field(..., min_length=1, max_length=255)
    supplier_invoice_number: Optional[str] = None
    partner_id: UUID
    date_invoice: Date
    date_due: Optional[Date] = None
    payment_term_id: Optional[UUID] = None
    currency_id: Optional[UUID] = None
    exchange_rate: Decimal = Field(default=Decimal("1"))
    journal_id: Optional[UUID] = None
    purchase_order_id: Optional[UUID] = None
    receipt_id: Optional[UUID] = None
    origin: Optional[str] = None
    notes: Optional[str] = None


class PurchaseInvoiceCreate(PurchaseInvoiceBase):
    """Schema for creating purchase invoice."""
    lines: List[PurchaseInvoiceLineCreate] = Field(..., min_length=1)


class PurchaseInvoiceUpdate(BaseModel):
    """Schema for updating purchase invoice."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    supplier_invoice_number: Optional[str] = None
    partner_id: Optional[UUID] = None
    date_invoice: Optional[Date] = None
    date_due: Optional[Date] = None
    payment_term_id: Optional[UUID] = None
    currency_id: Optional[UUID] = None
    exchange_rate: Optional[Decimal] = None
    journal_id: Optional[UUID] = None
    purchase_order_id: Optional[UUID] = None
    receipt_id: Optional[UUID] = None
    origin: Optional[str] = None
    notes: Optional[str] = None
    lines: Optional[List[PurchaseInvoiceLineCreate]] = None


class PurchaseInvoiceResponse(PurchaseInvoiceBase):
    """Schema for purchase invoice response."""
    id: UUID
    number: str
    state: PurchaseInvoiceStateEnum
    amount_untaxed: Decimal
    amount_tax: Decimal
    amount_discount: Decimal
    amount_total: Decimal
    amount_residual: Decimal
    amount_paid: Decimal
    date_posted: Optional[Date]
    posted_at: Optional[datetime]
    journal_entry_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    lines: List[PurchaseInvoiceLineResponse] = []

    class Config:
        from_attributes = True


class PurchaseInvoiceListResponse(BaseModel):
    """Schema for purchase invoice list response."""
    items: List[PurchaseInvoiceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ========================================
# Action Schemas
# ========================================

class PurchaseOrderConfirmRequest(BaseModel):
    """Schema for confirming purchase order."""
    approve: bool = Field(default=False)
    approval_notes: Optional[str] = None


class ReceiptConfirmRequest(BaseModel):
    """Schema for confirming receipt."""
    create_invoice: bool = Field(default=False)
    date_done: Optional[Date] = None


class PurchaseInvoicePostRequest(BaseModel):
    """Schema for posting purchase invoice."""
    date_posted: Optional[Date] = None


class CreateReceiptFromPORequest(BaseModel):
    """Schema for creating receipt from purchase order."""
    date: Optional[Date] = None
    warehouse_id: Optional[UUID] = None
    location_id: Optional[UUID] = None
    lines: Optional[List[dict]] = None  # [{"purchase_line_id": UUID, "quantity": Decimal}]


class CreateInvoiceFromReceiptRequest(BaseModel):
    """Schema for creating invoice from receipt."""
    receipt_id: UUID
    date_invoice: Optional[Date] = None


# ========================================
# Supplier Info Schemas
# ========================================

class SupplierInfoBase(BaseModel):
    """Base schema for supplier info."""
    partner_id: UUID
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    currency_id: Optional[UUID] = None
    min_qty: Decimal = Field(default=Decimal("0"), ge=0)
    delay: int = Field(default=0, ge=0)


class SupplierInfoCreate(SupplierInfoBase):
    """Schema for creating supplier info."""
    product_id: UUID


class SupplierInfoUpdate(BaseModel):
    """Schema for updating supplier info."""
    partner_id: Optional[UUID] = None
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    currency_id: Optional[UUID] = None
    min_qty: Optional[Decimal] = Field(None, ge=0)
    delay: Optional[int] = Field(None, ge=0)


class SupplierInfoResponse(SupplierInfoBase):
    """Schema for supplier info response."""
    id: UUID
    product_id: UUID
    sequence: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========================================
# Supplier Payment Schemas
# ========================================

class SupplierPaymentAllocationInput(BaseModel):
    invoice_id: UUID
    amount: Decimal = Field(..., gt=0, allow_inf_nan=False)


class SupplierPaymentRegisterRequest(BaseModel):
    supplier_id: UUID
    payment_date: Date
    amount: Decimal = Field(..., gt=0, allow_inf_nan=False)
    journal_id: UUID
    bank_account_id: UUID
    allocations: List[SupplierPaymentAllocationInput] = Field(..., min_length=1)
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class SupplierPaymentCancelRequest(BaseModel):
    reversal_date: Optional[Date] = None
    reason: str = Field(..., min_length=3, max_length=500)


class SupplierPaymentResponse(BaseModel):
    id: UUID
    number: str
    partner_id: UUID
    payment_date: Date
    amount: Decimal
    currency_id: Optional[UUID]
    journal_id: UUID
    bank_account_id: UUID
    reference: Optional[str]
    state: str
    journal_entry_id: Optional[UUID]
    reversal_journal_entry_id: Optional[UUID] = None
    posted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
