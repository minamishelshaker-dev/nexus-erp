"""
Nexus ERP - Sales Module Schemas
=================================

Pydantic schemas for the Sales module API.
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

class QuotationStateEnum(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    LOST = "lost"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SaleOrderStateEnum(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    DONE = "done"
    CANCELLED = "cancelled"


class InvoiceTypeEnum(str, Enum):
    OUT_INVOICE = "out_invoice"
    OUT_REFUND = "out_refund"
    IN_INVOICE = "in_invoice"
    IN_REFUND = "in_refund"


class InvoiceStateEnum(str, Enum):
    DRAFT = "draft"
    POSTED = "posted"
    PAID = "paid"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class PaymentTypeEnum(str, Enum):
    RECEIPT = "receipt"
    PAYMENT = "payment"


class PaymentStateEnum(str, Enum):
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"


# ========================================
# Line Schemas
# ========================================

class QuotationLineBase(BaseModel):
    """Base schema for quotation line."""
    product_id: Optional[UUID] = None
    description: str = Field(..., min_length=1, max_length=2000)
    quantity: Decimal = Field(..., gt=0)
    uom_id: Optional[UUID] = None
    price_unit: Decimal = Field(..., ge=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    tax_ids: List[str] = Field(default_factory=list)
    date_planned: Optional[Date] = None
    notes: Optional[str] = None


class QuotationLineCreate(QuotationLineBase):
    """Schema for creating quotation line."""
    pass


class QuotationLineUpdate(BaseModel):
    """Schema for updating quotation line."""
    product_id: Optional[UUID] = None
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    quantity: Optional[Decimal] = Field(None, gt=0)
    uom_id: Optional[UUID] = None
    price_unit: Optional[Decimal] = Field(None, ge=0)
    discount: Optional[Decimal] = Field(None, ge=0, le=100)
    tax_ids: Optional[List[str]] = None
    date_planned: Optional[Date] = None
    notes: Optional[str] = None


class QuotationLineResponse(QuotationLineBase):
    """Schema for quotation line response."""
    id: UUID
    quotation_id: UUID
    sequence: int
    discount_amount: Decimal
    tax_amount: Decimal
    subtotal: Decimal
    subtotal_with_tax: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========================================
# Quotation Schemas
# ========================================

class QuotationBase(BaseModel):
    """Base schema for quotation."""
    name: str = Field(..., min_length=1, max_length=255)
    partner_id: UUID
    partner_shipping_id: Optional[UUID] = None
    partner_invoice_id: Optional[UUID] = None
    date: Date
    valid_until: Optional[Date] = None
    payment_term_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    salesperson_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    currency_id: Optional[UUID] = None
    exchange_rate: Decimal = Field(default=Decimal("1"))
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None


class QuotationCreate(QuotationBase):
    """Schema for creating quotation."""
    lines: List[QuotationLineCreate] = Field(..., min_length=1)
    
    @field_validator('valid_until')
    @classmethod
    def validate_valid_until(cls, v, info):
        if v and 'date' in info.data and v < info.data['date']:
            raise ValueError('valid_until must be after date')
        return v


class QuotationUpdate(BaseModel):
    """Schema for updating quotation."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    partner_id: Optional[UUID] = None
    partner_shipping_id: Optional[UUID] = None
    partner_invoice_id: Optional[UUID] = None
    date: Optional[Date] = None
    valid_until: Optional[Date] = None
    payment_term_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    salesperson_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    currency_id: Optional[UUID] = None
    exchange_rate: Optional[Decimal] = None
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None
    lines: Optional[List[QuotationLineCreate]] = None


class QuotationResponse(QuotationBase):
    """Schema for quotation response."""
    id: UUID
    number: str
    state: QuotationStateEnum
    amount_untaxed: Decimal
    amount_tax: Decimal
    amount_discount: Decimal
    amount_total: Decimal
    sent_at: Optional[datetime]
    accepted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    lines: List[QuotationLineResponse] = []

    class Config:
        from_attributes = True


class QuotationListResponse(BaseModel):
    """Schema for quotation list response."""
    items: List[QuotationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ========================================
# Sale Order Line Schemas
# ========================================

class SaleOrderLineBase(BaseModel):
    """Base schema for sale order line."""
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


class SaleOrderLineCreate(SaleOrderLineBase):
    """Schema for creating sale order line."""
    pass


class SaleOrderLineUpdate(BaseModel):
    """Schema for updating sale order line."""
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


class SaleOrderLineResponse(SaleOrderLineBase):
    """Schema for sale order line response."""
    id: UUID
    order_id: UUID
    sequence: int
    quantity_delivered: Decimal
    quantity_invoiced: Decimal
    cost_price: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    subtotal: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========================================
# Sale Order Schemas
# ========================================

class SaleOrderBase(BaseModel):
    """Base schema for sale order."""
    name: str = Field(..., min_length=1, max_length=255)
    partner_id: UUID
    partner_shipping_id: Optional[UUID] = None
    partner_invoice_id: Optional[UUID] = None
    date_order: Date
    date_planned: Optional[Date] = None
    payment_term_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    salesperson_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    currency_id: Optional[UUID] = None
    exchange_rate: Decimal = Field(default=Decimal("1"))
    origin: Optional[str] = None
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None


class SaleOrderCreate(SaleOrderBase):
    """Schema for creating sale order."""
    quotation_id: Optional[UUID] = None
    lines: List[SaleOrderLineCreate] = Field(..., min_length=1)


class SaleOrderUpdate(BaseModel):
    """Schema for updating sale order."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    partner_id: Optional[UUID] = None
    partner_shipping_id: Optional[UUID] = None
    partner_invoice_id: Optional[UUID] = None
    date_order: Optional[Date] = None
    date_planned: Optional[Date] = None
    payment_term_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    salesperson_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    currency_id: Optional[UUID] = None
    exchange_rate: Optional[Decimal] = None
    origin: Optional[str] = None
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None
    lines: Optional[List[SaleOrderLineCreate]] = None


class SaleOrderResponse(SaleOrderBase):
    """Schema for sale order response."""
    id: UUID
    number: str
    quotation_id: Optional[UUID]
    state: SaleOrderStateEnum
    amount_untaxed: Decimal
    amount_tax: Decimal
    amount_discount: Decimal
    amount_total: Decimal
    amount_invoiced: Decimal
    amount_residual: Decimal
    delivery_status: str
    invoice_status: str
    date_confirm: Optional[Date]
    confirmed_at: Optional[datetime]
    done_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    lines: List[SaleOrderLineResponse] = []

    class Config:
        from_attributes = True


class SaleOrderListResponse(BaseModel):
    """Schema for sale order list response."""
    items: List[SaleOrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ========================================
# Invoice Line Schemas
# ========================================

class InvoiceLineBase(BaseModel):
    """Base schema for invoice line."""
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


class InvoiceLineCreate(InvoiceLineBase):
    """Schema for creating invoice line."""
    pass


class InvoiceLineUpdate(BaseModel):
    """Schema for updating invoice line."""
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


class InvoiceLineResponse(InvoiceLineBase):
    """Schema for invoice line response."""
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
# Invoice Schemas
# ========================================

class InvoiceBase(BaseModel):
    """Base schema for invoice."""
    name: str = Field(..., min_length=1, max_length=255)
    invoice_type: InvoiceTypeEnum
    partner_id: UUID
    partner_shipping_id: Optional[UUID] = None
    date_invoice: Date
    date_due: Optional[Date] = None
    payment_term_id: Optional[UUID] = None
    journal_id: Optional[UUID] = None
    currency_id: Optional[UUID] = None
    exchange_rate: Decimal = Field(default=Decimal("1"))
    origin: Optional[str] = None
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    """Schema for creating invoice."""
    sale_order_id: Optional[UUID] = None
    purchase_order_id: Optional[UUID] = None
    lines: List[InvoiceLineCreate] = Field(..., min_length=1)


class InvoiceUpdate(BaseModel):
    """Schema for updating invoice."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    partner_id: Optional[UUID] = None
    partner_shipping_id: Optional[UUID] = None
    date_invoice: Optional[Date] = None
    date_due: Optional[Date] = None
    payment_term_id: Optional[UUID] = None
    journal_id: Optional[UUID] = None
    currency_id: Optional[UUID] = None
    exchange_rate: Optional[Decimal] = None
    origin: Optional[str] = None
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None
    lines: Optional[List[InvoiceLineCreate]] = None


class InvoiceResponse(InvoiceBase):
    """Schema for invoice response."""
    id: UUID
    number: str
    sale_order_id: Optional[UUID]
    purchase_order_id: Optional[UUID]
    state: InvoiceStateEnum
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
    lines: List[InvoiceLineResponse] = []

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    """Schema for invoice list response."""
    items: List[InvoiceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ========================================
# Payment Schemas
# ========================================

class PaymentInvoiceAllocation(BaseModel):
    """Schema for invoice allocation in payment."""
    invoice_id: UUID
    amount: Decimal = Field(..., gt=0)


class PaymentBase(BaseModel):
    """Base schema for payment."""
    name: str = Field(..., min_length=1, max_length=255)
    payment_type: PaymentTypeEnum
    partner_id: UUID
    date: Date
    amount: Decimal = Field(..., gt=0)
    currency_id: Optional[UUID] = None
    payment_method_id: Optional[UUID] = None
    journal_id: Optional[UUID] = None
    destination_account_id: Optional[UUID] = None
    partner_bank_id: Optional[UUID] = None
    reference: Optional[str] = None
    cheque_number: Optional[str] = None
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    """Schema for creating payment."""
    invoice_allocations: Optional[List[PaymentInvoiceAllocation]] = None


class PaymentUpdate(BaseModel):
    """Schema for updating payment."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    date: Optional[Date] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    currency_id: Optional[UUID] = None
    payment_method_id: Optional[UUID] = None
    journal_id: Optional[UUID] = None
    destination_account_id: Optional[UUID] = None
    partner_bank_id: Optional[UUID] = None
    reference: Optional[str] = None
    cheque_number: Optional[str] = None
    notes: Optional[str] = None
    invoice_allocations: Optional[List[PaymentInvoiceAllocation]] = None


class PaymentResponse(PaymentBase):
    """Schema for payment response."""
    id: UUID
    number: str
    state: PaymentStateEnum
    date_posted: Optional[Date]
    posted_at: Optional[datetime]
    journal_entry_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentListResponse(BaseModel):
    """Schema for payment list response."""
    items: List[PaymentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ========================================
# Action Schemas
# ========================================

class QuotationSendRequest(BaseModel):
    """Schema for sending quotation."""
    send_email: bool = Field(default=True)
    email_subject: Optional[str] = None
    email_body: Optional[str] = None


class QuotationConfirmRequest(BaseModel):
    """Schema for confirming quotation to sale order."""
    create_order: bool = Field(default=True)
    order_name: Optional[str] = None


class SaleOrderConfirmRequest(BaseModel):
    """Schema for confirming sale order."""
    create_delivery: bool = Field(default=True)
    create_invoice: bool = Field(default=False)


class InvoicePostRequest(BaseModel):
    """Schema for posting invoice."""
    date_posted: Optional[Date] = None


class PaymentRegisterRequest(BaseModel):
    """Schema for registering payment on invoice."""
    amount: Decimal = Field(..., gt=0)
    date: Date
    journal_id: UUID
    payment_method_id: Optional[UUID] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
