"""
Nexus ERP - Sales Module Models
================================

This module implements comprehensive sales functionality including:
- Quotations (عروض الأسعار)
- Sale Orders (أوامر البيع)
- Sale Order Lines (بنود أوامر البيع)
- Invoices (الفواتير) - Both Customer and Supplier
- Invoice Lines (بنود الفواتير)
- Payments (المدفوعات)

Features:
- Full sales cycle from quotation to invoice
- Integration with inventory for stock movements
- Integration with accounting for journal entries
- Multi-currency support
- Discount and tax calculations
"""

from datetime import datetime, date
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Date,
    Text,
    ForeignKey,
    Numeric,
    Integer,
    Enum as SQLEnum,
    Index,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from decimal import Decimal
import enum
import uuid

from app.models.base import BaseModel, TenantMixin


# ========================================
# Enums
# ========================================

class QuotationState(str, enum.Enum):
    """Quotation state enumeration."""
    DRAFT = "draft"              # مسودة
    SENT = "sent"                # مرسل
    ACCEPTED = "accepted"        # مقبول
    LOST = "lost"                # مرفوض/خاسر
    EXPIRED = "expired"          # منتهي الصلاحية
    CANCELLED = "cancelled"      # ملغي


class SaleOrderState(str, enum.Enum):
    """Sale order state enumeration."""
    DRAFT = "draft"              # مسودة
    CONFIRMED = "confirmed"      # مؤكد
    DONE = "done"                # تم التنفيذ
    CANCELLED = "cancelled"      # ملغي


class InvoiceType(str, enum.Enum):
    """Invoice type enumeration."""
    OUT_INVOICE = "out_invoice"          # فاتورة مبيعات (للعميل)
    OUT_REFUND = "out_refund"            # إشعار دائن للعميل
    IN_INVOICE = "in_invoice"            # فاتورة مشتريات (من المورد)
    IN_REFUND = "in_refund"              # إشعار مدين من المورد


class InvoiceState(str, enum.Enum):
    """Invoice state enumeration."""
    DRAFT = "draft"              # مسودة
    POSTED = "posted"            # مرحلة
    PAID = "paid"                # مدفوعة
    PARTIAL = "partial"          # مدفوعة جزئياً
    CANCELLED = "cancelled"      # ملغاة


class PaymentState(str, enum.Enum):
    """Payment state enumeration."""
    DRAFT = "draft"              # مسودة
    POSTED = "posted"            # مرحلة
    CANCELLED = "cancelled"      # ملغي


class PaymentType(str, enum.Enum):
    """Payment type enumeration."""
    RECEIPT = "receipt"          # قبض (من عميل)
    PAYMENT = "payment"          # سداد (لمورد)


# ========================================
# Quotation Model
# ========================================

class Quotation(BaseModel, TenantMixin):
    """
    Quotation Model (عرض سعر)
    
    Represents a sales quotation sent to a customer.
    Can be converted to a sale order when accepted.
    """
    __tablename__ = "quotations"
    __table_args__ = (
        Index("ix_quotations_number", "number"),
        Index("ix_quotations_partner", "partner_id"),
        Index("ix_quotations_date", "date"),
        Index("ix_quotations_state", "state"),
        Index("ix_quotations_company", "tenant_id"),
        UniqueConstraint("number", "tenant_id", name="uq_quotation_number"),
    )
    
    # Identification
    number: str = Column(
        String(50),
        nullable=False,
        doc="Quotation number (auto-generated)"
    )
    name: str = Column(
        String(255),
        nullable=False,
        doc="Quotation name/reference"
    )
    
    # Partner (Customer)
    partner_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="RESTRICT"),
        nullable=False,
        doc="Customer ID"
    )
    partner_shipping_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Shipping address ID"
    )
    partner_invoice_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Invoice address ID"
    )
    
    # Dates
    date: date = Column(
        Date,
        nullable=False,
        doc="Quotation date"
    )
    valid_until: Optional[date] = Column(
        Date,
        nullable=True,
        doc="Validity expiration date"
    )
    
    # State
    state: QuotationState = Column(
        SQLEnum(QuotationState),
        default=QuotationState.DRAFT,
        nullable=False,
        doc="Quotation state"
    )
    
    # Amounts
    amount_untaxed: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Amount before taxes"
    )
    amount_tax: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Tax amount"
    )
    amount_discount: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Discount amount"
    )
    amount_total: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Total amount including taxes"
    )
    
    # Terms
    payment_term_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    incoterm_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Currency
    currency_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    exchange_rate: Decimal = Column(
        Numeric(12, 6),
        default=Decimal("1"),
        nullable=False
    )
    
    # Warehouse
    warehouse_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Salesperson
    salesperson_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Salesperson responsible"
    )
    team_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Sales team"
    )
    
    # Additional Info
    notes: Optional[str] = Column(Text, nullable=True)
    terms_conditions: Optional[str] = Column(Text, nullable=True)
    internal_notes: Optional[str] = Column(Text, nullable=True)
    
    # Tracking
    sent_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    accepted_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    
    # Custom fields
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    lines: Mapped[List["QuotationLine"]] = relationship(
        "QuotationLine",
        back_populates="quotation",
        cascade="all, delete-orphan",
        order_by="QuotationLine.sequence"
    )
    sale_order: Mapped[Optional["SaleOrder"]] = relationship(
        "SaleOrder",
        back_populates="quotation",
        uselist=False
    )
    
    # ========================================
    # Properties
    # ========================================
    
    @property
    def is_expired(self) -> bool:
        """Check if quotation has expired."""
        if self.valid_until:
            return date.today() > self.valid_until
        return False
    
    @property
    def line_count(self) -> int:
        """Get number of lines."""
        return len(self.lines) if self.lines else 0
    
    def calculate_totals(self):
        """Calculate and update all totals."""
        self.amount_untaxed = sum(line.subtotal for line in self.lines) if self.lines else Decimal("0")
        self.amount_tax = sum(line.tax_amount for line in self.lines) if self.lines else Decimal("0")
        self.amount_discount = sum(line.discount_amount for line in self.lines) if self.lines else Decimal("0")
        self.amount_total = self.amount_untaxed + self.amount_tax  # subtotal already includes line discount


class QuotationLine(BaseModel, TenantMixin):
    """
    Quotation Line Model (بند عرض السعر)
    
    Represents a single line item in a quotation.
    """
    __tablename__ = "quotation_lines"
    __table_args__ = (
        Index("ix_quotation_lines_quotation", "quotation_id"),
        Index("ix_quotation_lines_product", "product_id"),
    )
    
    quotation_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=False
    )
    
    sequence: int = Column(Integer, default=10, nullable=False)
    
    # Product
    product_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )
    description: str = Column(Text, nullable=False)
    
    # Quantity and UOM
    quantity: Decimal = Column(Numeric(18, 4), nullable=False)
    uom_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Pricing
    price_unit: Decimal = Column(Numeric(18, 4), nullable=False)
    discount: Decimal = Column(Numeric(5, 2), default=Decimal("0"), nullable=False)
    discount_amount: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Taxes
    tax_ids: List[str] = Column(ARRAY(String), default=list, nullable=False)
    tax_amount: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Subtotal
    subtotal: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    subtotal_with_tax: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Delivery
    date_planned: Optional[date] = Column(Date, nullable=True)
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    quotation: Mapped["Quotation"] = relationship("Quotation", back_populates="lines")
    
    # ========================================
    # Methods
    # ========================================
    
    def calculate_subtotal(self):
        """Calculate line subtotal."""
        self.discount_amount = self.price_unit * self.quantity * (self.discount / 100)
        self.subtotal = (self.price_unit * self.quantity) - self.discount_amount
        self.subtotal_with_tax = self.subtotal + self.tax_amount


# ========================================
# Sale Order Model
# ========================================

class SaleOrder(BaseModel, TenantMixin):
    """
    Sale Order Model (أمر بيع)
    
    Represents a confirmed sales order.
    Triggers inventory movements and invoice creation.
    """
    __tablename__ = "sale_orders"
    __table_args__ = (
        Index("ix_sale_orders_number", "number"),
        Index("ix_sale_orders_partner", "partner_id"),
        Index("ix_sale_orders_date", "date_order"),
        Index("ix_sale_orders_state", "state"),
        Index("ix_sale_orders_company", "tenant_id"),
        UniqueConstraint("number", "tenant_id", name="uq_sale_order_number"),
    )
    
    # Identification
    number: str = Column(
        String(50),
        nullable=False,
        doc="Sale order number (auto-generated)"
    )
    name: str = Column(
        String(255),
        nullable=False,
        doc="Order name/reference"
    )
    
    # Origin
    quotation_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("quotations.id", ondelete="SET NULL"),
        nullable=True,
        doc="Source quotation ID"
    )
    origin: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Origin document reference"
    )
    
    # Partner (Customer)
    partner_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="RESTRICT"),
        nullable=False,
        doc="Customer ID"
    )
    partner_shipping_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    partner_invoice_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Dates
    date_order: date = Column(
        Date,
        nullable=False,
        doc="Order date"
    )
    date_confirm: Optional[date] = Column(
        Date,
        nullable=True,
        doc="Confirmation date"
    )
    date_planned: Optional[date] = Column(
        Date,
        nullable=True,
        doc="Expected delivery date"
    )
    
    # State
    state: SaleOrderState = Column(
        SQLEnum(SaleOrderState),
        default=SaleOrderState.DRAFT,
        nullable=False,
        doc="Order state"
    )
    
    # Amounts
    amount_untaxed: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_tax: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_discount: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_total: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_invoiced: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_residual: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Delivery Status
    delivery_status: str = Column(
        String(20),
        default="no",
        nullable=False,
        doc="Delivery status: no, partial, done"
    )
    invoice_status: str = Column(
        String(20),
        default="no",
        nullable=False,
        doc="Invoice status: no, partial, invoiced"
    )
    
    # Terms
    payment_term_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    incoterm_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Currency
    currency_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    exchange_rate: Decimal = Column(Numeric(12, 6), default=Decimal("1"), nullable=False)
    
    # Warehouse
    warehouse_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Source warehouse"
    )
    
    # Salesperson
    salesperson_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    team_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Additional Info
    notes: Optional[str] = Column(Text, nullable=True)
    terms_conditions: Optional[str] = Column(Text, nullable=True)
    internal_notes: Optional[str] = Column(Text, nullable=True)
    
    # Tracking
    confirmed_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    confirmed_by_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    done_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    
    # Custom fields
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    lines: Mapped[List["SaleOrderLine"]] = relationship(
        "SaleOrderLine",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="SaleOrderLine.sequence"
    )
    quotation: Mapped[Optional["Quotation"]] = relationship(
        "Quotation", back_populates="sale_order"
    )
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="sale_order",
        lazy="dynamic"
    )
    # StockMove currently has no sale_order_id foreign key; explicit linkage is pending.

    # ========================================
    # Properties
    # ========================================
    
    @property
    def is_fully_invoiced(self) -> bool:
        """Check if order is fully invoiced."""
        return self.invoice_status == "invoiced"
    
    @property
    def is_fully_delivered(self) -> bool:
        """Check if order is fully delivered."""
        return self.delivery_status == "done"
    
    def calculate_totals(self):
        """Calculate and update all totals."""
        self.amount_untaxed = sum(line.subtotal for line in self.lines) if self.lines else Decimal("0")
        self.amount_tax = sum(line.tax_amount for line in self.lines) if self.lines else Decimal("0")
        self.amount_discount = sum(line.discount_amount for line in self.lines) if self.lines else Decimal("0")
        self.amount_total = self.amount_untaxed + self.amount_tax  # subtotal already includes line discount
        self.amount_residual = self.amount_total - self.amount_invoiced


class SaleOrderLine(BaseModel, TenantMixin):
    """
    Sale Order Line Model (بند أمر البيع)
    
    Represents a single line item in a sale order.
    """
    __tablename__ = "sale_order_lines"
    __table_args__ = (
        Index("ix_sale_order_lines_order", "order_id"),
        Index("ix_sale_order_lines_product", "product_id"),
    )
    
    order_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("sale_orders.id", ondelete="CASCADE"),
        nullable=False
    )
    
    sequence: int = Column(Integer, default=10, nullable=False)
    
    # Product
    product_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )
    description: str = Column(Text, nullable=False)
    
    # Quantity and UOM
    quantity: Decimal = Column(Numeric(18, 4), nullable=False, doc="Ordered quantity")
    quantity_delivered: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    quantity_invoiced: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    uom_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Pricing
    price_unit: Decimal = Column(Numeric(18, 4), nullable=False)
    cost_price: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False, doc="Unit cost")
    discount: Decimal = Column(Numeric(5, 2), default=Decimal("0"), nullable=False)
    discount_amount: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Taxes
    tax_ids: List[str] = Column(ARRAY(String), default=list, nullable=False)
    tax_amount: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Subtotal
    subtotal: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Delivery
    date_planned: Optional[date] = Column(Date, nullable=True)
    
    # Analytic
    analytic_account_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    order: Mapped["SaleOrder"] = relationship("SaleOrder", back_populates="lines")
    
    # ========================================
    # Properties
    # ========================================
    
    @property
    def quantity_to_deliver(self) -> Decimal:
        """Get remaining quantity to deliver."""
        return self.quantity - self.quantity_delivered
    
    @property
    def quantity_to_invoice(self) -> Decimal:
        """Get remaining quantity to invoice."""
        return self.quantity - self.quantity_invoiced
    
    def calculate_subtotal(self):
        """Calculate line subtotal."""
        self.discount_amount = self.price_unit * self.quantity * (self.discount / 100)
        self.subtotal = (self.price_unit * self.quantity) - self.discount_amount


# ========================================
# Invoice Model
# ========================================

class Invoice(BaseModel, TenantMixin):
    """
    Invoice Model (فاتورة)
    
    Represents a customer or supplier invoice.
    Supports sales invoices, purchase invoices, and refunds.
    """
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_number", "number"),
        Index("ix_invoices_partner", "partner_id"),
        Index("ix_invoices_date", "date_invoice"),
        Index("ix_invoices_type", "invoice_type"),
        Index("ix_invoices_state", "state"),
        Index("ix_invoices_company", "tenant_id"),
        UniqueConstraint("number", "tenant_id", name="uq_invoice_number"),
        CheckConstraint("amount_total >= 0", name="ck_invoice_amount_positive"),
    )
    
    # Identification
    number: str = Column(
        String(50),
        nullable=False,
        doc="Invoice number (auto-generated)"
    )
    name: str = Column(
        String(255),
        nullable=False,
        doc="Invoice reference/description"
    )
    
    # Type
    invoice_type: InvoiceType = Column(
        SQLEnum(InvoiceType),
        nullable=False,
        doc="Invoice type (out_invoice, out_refund, in_invoice, in_refund)"
    )
    
    # Origin
    sale_order_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("sale_orders.id", ondelete="SET NULL"),
        nullable=True,
        doc="Related sale order"
    )
    purchase_order_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Related purchase order"
    )
    origin: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Origin document reference"
    )
    
    # Partner
    partner_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="RESTRICT"),
        nullable=False,
        doc="Customer or Supplier ID"
    )
    partner_shipping_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Dates
    date_invoice: date = Column(
        Date,
        nullable=False,
        doc="Invoice date"
    )
    date_due: Optional[date] = Column(
        Date,
        nullable=True,
        doc="Due date"
    )
    date_posted: Optional[date] = Column(
        Date,
        nullable=True,
        doc="Posting date"
    )
    
    # State
    state: InvoiceState = Column(
        SQLEnum(InvoiceState),
        default=InvoiceState.DRAFT,
        nullable=False,
        doc="Invoice state"
    )
    
    # Amounts
    amount_untaxed: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_tax: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_discount: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_total: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_residual: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_paid: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Payment
    payment_term_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    payment_reference: Optional[str] = Column(String(100), nullable=True)
    
    # Currency
    currency_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    exchange_rate: Decimal = Column(Numeric(12, 6), default=Decimal("1"), nullable=False)
    
    # Journal
    journal_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("journals.id", ondelete="SET NULL"),
        nullable=True
    )
    account_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Receivable/Payable account"
    )
    
    # Additional Info
    notes: Optional[str] = Column(Text, nullable=True)
    terms_conditions: Optional[str] = Column(Text, nullable=True)
    internal_notes: Optional[str] = Column(Text, nullable=True)
    
    # Accounting Reference
    journal_entry_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
        doc="Related journal entry"
    )
    
    # Tracking
    posted_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    posted_by_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Custom fields
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    lines: Mapped[List["InvoiceLine"]] = relationship(
        "InvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.sequence"
    )
    sale_order: Mapped[Optional["SaleOrder"]] = relationship(
        "SaleOrder", back_populates="invoices"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        secondary="payment_invoices",
        back_populates="invoices"
    )
    
    # ========================================
    # Properties
    # ========================================
    
    @property
    def is_customer_invoice(self) -> bool:
        """Check if this is a customer invoice."""
        return self.invoice_type in (InvoiceType.OUT_INVOICE, InvoiceType.OUT_REFUND)
    
    @property
    def is_supplier_invoice(self) -> bool:
        """Check if this is a supplier invoice."""
        return self.invoice_type in (InvoiceType.IN_INVOICE, InvoiceType.IN_REFUND)
    
    @property
    def is_refund(self) -> bool:
        """Check if this is a refund/credit note."""
        return self.invoice_type in (InvoiceType.OUT_REFUND, InvoiceType.IN_REFUND)
    
    @property
    def is_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.state == InvoiceState.PAID or self.amount_residual == 0
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        if self.date_due and self.state not in (InvoiceState.PAID, InvoiceState.CANCELLED):
            return date.today() > self.date_due
        return False
    
    def calculate_totals(self):
        """Calculate and update all totals."""
        self.amount_untaxed = sum(line.subtotal for line in self.lines) if self.lines else Decimal("0")
        self.amount_tax = sum(line.tax_amount for line in self.lines) if self.lines else Decimal("0")
        self.amount_discount = sum(line.discount_amount for line in self.lines) if self.lines else Decimal("0")
        self.amount_total = self.amount_untaxed + self.amount_tax  # subtotal already includes line discount
        self.amount_residual = self.amount_total - self.amount_paid


class InvoiceLine(BaseModel, TenantMixin):
    """
    Invoice Line Model (بند الفاتورة)
    
    Represents a single line item in an invoice.
    """
    __tablename__ = "invoice_lines"
    __table_args__ = (
        Index("ix_invoice_lines_invoice", "invoice_id"),
        Index("ix_invoice_lines_product", "product_id"),
        Index("ix_invoice_lines_account", "account_id"),
    )
    
    invoice_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False
    )
    
    sequence: int = Column(Integer, default=10, nullable=False)
    
    # Product
    product_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )
    description: str = Column(Text, nullable=False)
    
    # Quantity and UOM
    quantity: Decimal = Column(Numeric(18, 4), nullable=False)
    uom_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Pricing
    price_unit: Decimal = Column(Numeric(18, 4), nullable=False)
    discount: Decimal = Column(Numeric(5, 2), default=Decimal("0"), nullable=False)
    discount_amount: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Taxes
    tax_ids: List[str] = Column(ARRAY(String), default=list, nullable=False)
    tax_amount: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Subtotal
    subtotal: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Account
    account_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        doc="Revenue/Expense account"
    )
    
    # Analytic
    analytic_account_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="lines")
    
    def calculate_subtotal(self):
        """Calculate line subtotal."""
        self.discount_amount = self.price_unit * self.quantity * (self.discount / 100)
        self.subtotal = (self.price_unit * self.quantity) - self.discount_amount


# ========================================
# Payment Model
# ========================================

class Payment(BaseModel, TenantMixin):
    """
    Payment Model (دفعة/سداد)
    
    Represents a payment received from or made to a partner.
    """
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_number", "number"),
        Index("ix_payments_partner", "partner_id"),
        Index("ix_payments_date", "date"),
        Index("ix_payments_type", "payment_type"),
        Index("ix_payments_state", "state"),
        Index("ix_payments_company", "tenant_id"),
        UniqueConstraint("number", "tenant_id", name="uq_payment_number"),
    )
    
    # Identification
    number: str = Column(
        String(50),
        nullable=False,
        doc="Payment number (auto-generated)"
    )
    name: str = Column(
        String(255),
        nullable=False,
        doc="Payment reference"
    )
    
    # Type
    payment_type: PaymentType = Column(
        SQLEnum(PaymentType),
        nullable=False,
        doc="Payment type (receipt/payment)"
    )
    
    # Partner
    partner_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="RESTRICT"),
        nullable=False,
        doc="Customer/Supplier ID"
    )
    
    # Dates
    date: date = Column(
        Date,
        nullable=False,
        doc="Payment date"
    )
    date_posted: Optional[date] = Column(
        Date,
        nullable=True,
        doc="Posting date"
    )
    
    # State
    state: PaymentState = Column(
        SQLEnum(PaymentState),
        default=PaymentState.DRAFT,
        nullable=False,
        doc="Payment state"
    )
    
    # Amount
    amount: Decimal = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Payment amount"
    )
    currency_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Payment Method
    payment_method_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    journal_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("journals.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Account
    destination_account_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        doc="Account to debit/credit"
    )
    
    # Bank Info
    partner_bank_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    reference: Optional[str] = Column(String(100), nullable=True)
    cheque_number: Optional[str] = Column(String(50), nullable=True)
    
    # Accounting Reference
    journal_entry_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    
    # Tracking
    posted_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    posted_by_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Custom fields
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        secondary="payment_invoices",
        back_populates="payments"
    )
    reconciliation: Mapped[Optional["PaymentReconciliation"]] = relationship(
        "PaymentReconciliation",
        back_populates="payment",
        uselist=False
    )


class PaymentInvoice(BaseModel, TenantMixin):
    """
    Payment-Invoice Association Table
    
    Links payments to invoices for reconciliation.
    """
    __tablename__ = "payment_invoices"
    __table_args__ = (
        Index("ix_payment_invoices_payment", "payment_id"),
        Index("ix_payment_invoices_invoice", "invoice_id"),
    )
    
    payment_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False
    )
    invoice_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False
    )
    amount: Decimal = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Amount allocated to this invoice"
    )


class PaymentReconciliation(BaseModel, TenantMixin):
    """
    Payment Reconciliation Model
    
    Tracks reconciliation of payments with invoices.
    """
    __tablename__ = "payment_reconciliations"
    __table_args__ = (
        Index("ix_payment_reconciliations_payment", "payment_id"),
    )
    
    payment_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False
    )
    date: date = Column(Date, nullable=False)
    amount: Decimal = Column(Numeric(18, 4), nullable=False)
    is_full: bool = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    payment: Mapped["Payment"] = relationship("Payment", back_populates="reconciliation")


# ========================================
# Sales Team
# ========================================

class SalesTeam(BaseModel, TenantMixin):
    """
    Sales Team Model (فريق المبيعات)
    """
    __tablename__ = "sales_teams"
    __table_args__ = (
        Index("ix_sales_teams_code", "code"),
    )
    
    code: str = Column(String(20), nullable=False)
    name: str = Column(String(100), nullable=False)
    description: Optional[str] = Column(Text, nullable=True)
    
    leader_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    member_ids: List[str] = Column(ARRAY(String), default=list, nullable=False)
    
    is_active: bool = Column(Boolean, default=True, nullable=False)
    
    # Quota
    monthly_target: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    quarterly_target: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    yearly_target: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
