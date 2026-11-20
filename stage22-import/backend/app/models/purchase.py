"""
Nexus ERP - Purchase Module Models
===================================

This module implements comprehensive purchasing functionality including:
- Purchase Orders (أوامر الشراء)
- Purchase Order Lines (بنود أوامر الشراء)
- Receipts (استلام البضاعة)
- Receipt Lines (بنود الاستلام)

Features:
- Full purchase cycle from order to receipt
- Integration with inventory for stock movements
- Integration with accounting for journal entries
- Multi-currency support
- Bill of Materials support
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

class PurchaseOrderState(str, enum.Enum):
    """Purchase order state enumeration."""
    DRAFT = "draft"              # مسودة
    CONFIRMED = "confirmed"      # مؤكد
    APPROVED = "approved"        # معتمد
    DONE = "done"                # تم الاستلام
    CANCELLED = "cancelled"      # ملغي


class ReceiptState(str, enum.Enum):
    """Receipt state enumeration."""
    DRAFT = "draft"              # مسودة
    CONFIRMED = "confirmed"      # مؤكد
    DONE = "done"                # تم
    CANCELLED = "cancelled"      # ملغي


class PurchaseInvoiceState(str, enum.Enum):
    """Purchase invoice state enumeration."""
    DRAFT = "draft"              # مسودة
    POSTED = "posted"            # مرحلة
    PAID = "paid"                # مدفوعة
    PARTIAL = "partial"          # مدفوعة جزئياً
    CANCELLED = "cancelled"      # ملغاة


# ========================================
# Purchase Order Model
# ========================================

class PurchaseOrder(BaseModel, TenantMixin):
    """
    Purchase Order Model (أمر شراء)
    
    Represents a purchase order sent to a supplier.
    Triggers inventory receipts and vendor bills.
    """
    __tablename__ = "purchase_orders"
    __table_args__ = (
        Index("ix_purchase_orders_number", "number"),
        Index("ix_purchase_orders_partner", "partner_id"),
        Index("ix_purchase_orders_date", "date_order"),
        Index("ix_purchase_orders_state", "state"),
        Index("ix_purchase_orders_company", "tenant_id"),
        UniqueConstraint("number", "tenant_id", name="uq_purchase_order_number"),
    )
    
    # Identification
    number: str = Column(
        String(50),
        nullable=False,
        doc="Purchase order number (auto-generated)"
    )
    name: str = Column(
        String(255),
        nullable=False,
        doc="Order name/reference"
    )
    
    # Partner (Supplier)
    partner_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="RESTRICT"),
        nullable=False,
        doc="Supplier ID"
    )
    partner_ref: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Supplier's order reference"
    )
    
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
        doc="Expected receipt date"
    )
    date_approve: Optional[date] = Column(
        Date,
        nullable=True,
        doc="Approval date"
    )
    
    # State
    state: PurchaseOrderState = Column(
        SQLEnum(PurchaseOrderState),
        default=PurchaseOrderState.DRAFT,
        nullable=False,
        doc="Order state"
    )
    
    # Amounts
    amount_untaxed: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_tax: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_discount: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_total: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    amount_billed: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Receipt Status
    receipt_status: str = Column(
        String(20),
        default="no",
        nullable=False,
        doc="Receipt status: no, partial, done"
    )
    invoice_status: str = Column(
        String(20),
        default="no",
        nullable=False,
        doc="Invoice status: no, partial, invoiced"
    )
    
    # Incoterm
    incoterm_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Currency
    currency_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    exchange_rate: Decimal = Column(Numeric(12, 6), default=Decimal("1"), nullable=False)
    
    # Warehouse
    warehouse_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Destination warehouse"
    )
    
    # Purchaser
    purchaser_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Buyer responsible"
    )
    
    # Payment Terms
    payment_term_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Approval
    approved_by_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
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
    lines: Mapped[List["PurchaseOrderLine"]] = relationship(
        "PurchaseOrderLine",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="PurchaseOrderLine.sequence"
    )
    receipts: Mapped[List["Receipt"]] = relationship(
        "Receipt",
        back_populates="purchase_order",
        lazy="dynamic"
    )
    invoices: Mapped[List["PurchaseInvoice"]] = relationship(
        "PurchaseInvoice", back_populates="purchase_order", lazy="dynamic"
    )
    
    # ========================================
    # Properties
    # ========================================
    
    @property
    def is_fully_received(self) -> bool:
        """Check if order is fully received."""
        return self.receipt_status == "done"
    
    @property
    def is_fully_billed(self) -> bool:
        """Check if order is fully billed."""
        return self.invoice_status == "invoiced"
    
    def calculate_totals(self):
        """Calculate and update all totals."""
        self.amount_untaxed = sum(line.subtotal for line in self.lines) if self.lines else Decimal("0")
        self.amount_tax = sum(line.tax_amount for line in self.lines) if self.lines else Decimal("0")
        self.amount_discount = sum(line.discount_amount for line in self.lines) if self.lines else Decimal("0")
        self.amount_total = self.amount_untaxed + self.amount_tax  # subtotal already includes line discount


class PurchaseOrderLine(BaseModel, TenantMixin):
    """
    Purchase Order Line Model (بند أمر الشراء)
    
    Represents a single line item in a purchase order.
    """
    __tablename__ = "purchase_order_lines"
    __table_args__ = (
        Index("ix_purchase_order_lines_order", "order_id"),
        Index("ix_purchase_order_lines_product", "product_id"),
    )
    
    order_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
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
    quantity_received: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    quantity_billed: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
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
    
    # Delivery
    date_planned: Optional[date] = Column(
        Date,
        nullable=True,
        doc="Expected delivery date"
    )
    
    # Analytic
    analytic_account_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="lines")
    receipt_lines: Mapped[List["ReceiptLine"]] = relationship(
        "ReceiptLine",
        back_populates="purchase_line",
        lazy="dynamic"
    )
    
    # ========================================
    # Properties
    # ========================================
    
    @property
    def quantity_to_receive(self) -> Decimal:
        """Get remaining quantity to receive."""
        return self.quantity - self.quantity_received
    
    @property
    def quantity_to_bill(self) -> Decimal:
        """Get remaining quantity to bill."""
        return self.quantity_received - self.quantity_billed
    
    def calculate_subtotal(self):
        """Calculate line subtotal."""
        self.discount_amount = self.price_unit * self.quantity * (self.discount / 100)
        self.subtotal = (self.price_unit * self.quantity) - self.discount_amount


# ========================================
# Receipt Model
# ========================================

class Receipt(BaseModel, TenantMixin):
    """
    Receipt Model (استلام بضاعة)
    
    Represents the receipt of goods from a supplier.
    Triggers inventory movements and accounting entries.
    """
    __tablename__ = "receipts"
    __table_args__ = (
        Index("ix_receipts_number", "number"),
        Index("ix_receipts_partner", "partner_id"),
        Index("ix_receipts_date", "date"),
        Index("ix_receipts_state", "state"),
        Index("ix_receipts_company", "tenant_id"),
        UniqueConstraint("number", "tenant_id", name="uq_receipt_number"),
    )
    
    # Identification
    number: str = Column(
        String(50),
        nullable=False,
        doc="Receipt number (auto-generated)"
    )
    name: str = Column(
        String(255),
        nullable=False,
        doc="Receipt reference"
    )
    
    # Purchase Order
    purchase_order_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        nullable=True,
        doc="Related purchase order"
    )
    
    # Partner (Supplier)
    partner_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="RESTRICT"),
        nullable=False,
        doc="Supplier ID"
    )
    
    # Dates
    date: date = Column(
        Date,
        nullable=False,
        doc="Receipt date"
    )
    date_done: Optional[date] = Column(
        Date,
        nullable=True,
        doc="Completion date"
    )
    
    # State
    state: ReceiptState = Column(
        SQLEnum(ReceiptState),
        default=ReceiptState.DRAFT,
        nullable=False,
        doc="Receipt state"
    )
    
    # Warehouse
    warehouse_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Destination warehouse"
    )
    location_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("stock_locations.id", ondelete="SET NULL"),
        nullable=True,
        doc="Destination location"
    )
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    
    # Tracking
    confirmed_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    confirmed_by_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Custom fields
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    lines: Mapped[List["ReceiptLine"]] = relationship(
        "ReceiptLine",
        back_populates="receipt",
        cascade="all, delete-orphan",
        order_by="ReceiptLine.sequence"
    )
    purchase_order: Mapped[Optional["PurchaseOrder"]] = relationship(
        "PurchaseOrder", back_populates="receipts"
    )
    # Stock moves are linked through ReceiptLine.stock_move_id.

    # ========================================
    # Properties
    # ========================================
    
    @property
    def line_count(self) -> int:
        """Get number of lines."""
        return len(self.lines) if self.lines else 0
    
    @property
    def total_quantity(self) -> Decimal:
        """Get total quantity received."""
        return sum(line.quantity for line in self.lines) if self.lines else Decimal("0")


class ReceiptLine(BaseModel, TenantMixin):
    """
    Receipt Line Model (بند الاستلام)
    
    Represents a single line item in a receipt.
    """
    __tablename__ = "receipt_lines"
    __table_args__ = (
        Index("ix_receipt_lines_receipt", "receipt_id"),
        Index("ix_receipt_lines_product", "product_id"),
        Index("ix_receipt_lines_stock_move", "stock_move_id"),
    )
    
    receipt_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Purchase Line Reference
    purchase_line_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("purchase_order_lines.id", ondelete="SET NULL"),
        nullable=True
    )
    
    sequence: int = Column(Integer, default=10, nullable=False)
    
    # Product
    product_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False
    )
    description: Optional[str] = Column(Text, nullable=True)
    
    # Quantity
    quantity: Decimal = Column(Numeric(18, 4), nullable=False, doc="Received quantity")
    quantity_done: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    uom_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Stock Move
    stock_move_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("stock_moves.id", ondelete="SET NULL"),
        nullable=True,
        doc="Related stock movement"
    )
    
    # Lot/Serial
    lot_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    lot_name: Optional[str] = Column(String(100), nullable=True)
    expiration_date: Optional[date] = Column(Date, nullable=True)
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    receipt: Mapped["Receipt"] = relationship("Receipt", back_populates="lines")
    purchase_line: Mapped[Optional["PurchaseOrderLine"]] = relationship(
        "PurchaseOrderLine", back_populates="receipt_lines"
    )


# ========================================
# Purchase Invoice (Vendor Bill)
# ========================================

class PurchaseInvoice(BaseModel, TenantMixin):
    """
    Purchase Invoice Model (فاتورة مورد)
    
    Represents a bill received from a supplier.
    Can be linked to purchase orders and receipts.
    """
    __tablename__ = "purchase_invoices"
    __table_args__ = (
        Index("ix_purchase_invoices_number", "number"),
        Index("ix_purchase_invoices_partner", "partner_id"),
        Index("ix_purchase_invoices_date", "date_invoice"),
        Index("ix_purchase_invoices_state", "state"),
        Index("ix_purchase_invoices_company", "tenant_id"),
        UniqueConstraint("number", "tenant_id", name="uq_purchase_invoice_number"),
    )
    
    # Identification
    number: str = Column(
        String(50),
        nullable=False,
        doc="Invoice number (auto-generated)"
    )
    supplier_invoice_number: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Supplier's invoice number"
    )
    name: str = Column(
        String(255),
        nullable=False,
        doc="Invoice reference"
    )
    
    # Partner (Supplier)
    partner_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="RESTRICT"),
        nullable=False,
        doc="Supplier ID"
    )
    
    # Origin
    purchase_order_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True
    )
    receipt_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    origin: Optional[str] = Column(String(100), nullable=True)
    
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
    state: PurchaseInvoiceState = Column(
        SQLEnum(PurchaseInvoiceState),
        default=PurchaseInvoiceState.DRAFT,
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
        doc="Payable account"
    )
    
    # Accounting Reference
    journal_entry_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    internal_notes: Optional[str] = Column(Text, nullable=True)
    
    # Tracking
    posted_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    posted_by_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Custom fields
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    lines: Mapped[List["PurchaseInvoiceLine"]] = relationship(
        "PurchaseInvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="PurchaseInvoiceLine.sequence"
    )
    purchase_order: Mapped[Optional["PurchaseOrder"]] = relationship(
        "PurchaseOrder", back_populates="invoices"
    )
    
    # ========================================
    # Properties
    # ========================================
    
    @property
    def is_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.state == PurchaseInvoiceState.PAID or self.amount_residual == 0
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        if self.date_due and self.state not in (PurchaseInvoiceState.PAID, PurchaseInvoiceState.CANCELLED):
            return date.today() > self.date_due
        return False
    
    def calculate_totals(self):
        """Calculate and update all totals."""
        self.amount_untaxed = sum(line.subtotal for line in self.lines) if self.lines else Decimal("0")
        self.amount_tax = sum(line.tax_amount for line in self.lines) if self.lines else Decimal("0")
        self.amount_discount = sum(line.discount_amount for line in self.lines) if self.lines else Decimal("0")
        self.amount_total = self.amount_untaxed + self.amount_tax  # subtotal already includes line discount
        self.amount_residual = self.amount_total - self.amount_paid


class PurchaseInvoiceLine(BaseModel, TenantMixin):
    """
    Purchase Invoice Line Model (بند فاتورة المورد)
    """
    __tablename__ = "purchase_invoice_lines"
    __table_args__ = (
        Index("ix_purchase_invoice_lines_invoice", "invoice_id"),
        Index("ix_purchase_invoice_lines_product", "product_id"),
    )
    
    invoice_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("purchase_invoices.id", ondelete="CASCADE"),
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
    
    # Quantity
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
        doc="Expense/Asset account"
    )
    
    # Analytic
    analytic_account_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    
    # ========================================
    # Relationships
    # ========================================
    invoice: Mapped["PurchaseInvoice"] = relationship("PurchaseInvoice", back_populates="lines")
    
    def calculate_subtotal(self):
        """Calculate line subtotal."""
        self.discount_amount = self.price_unit * self.quantity * (self.discount / 100)
        self.subtotal = (self.price_unit * self.quantity) - self.discount_amount


class SupplierPaymentState(str, enum.Enum):
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"


class SupplierPayment(BaseModel, TenantMixin):
    """A supplier disbursement posted atomically with its accounting entry."""
    __tablename__ = "supplier_payments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "number", name="uq_supplier_payment_number"),
        CheckConstraint("amount > 0", name="ck_supplier_payment_positive_amount"),
        Index("ix_supplier_payments_partner", "tenant_id", "partner_id"),
        Index("ix_supplier_payments_date", "tenant_id", "payment_date"),
        Index("ix_supplier_payments_state", "tenant_id", "state"),
    )

    number: str = Column(String(50), nullable=False)
    partner_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("partners.id", ondelete="RESTRICT"), nullable=False)
    payment_date: date = Column(Date, nullable=False)
    amount: Decimal = Column(Numeric(18, 4), nullable=False)
    currency_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    journal_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("journals.id", ondelete="RESTRICT"), nullable=False)
    bank_account_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    reference: Optional[str] = Column(String(100), nullable=True)
    state: str = Column(String(20), nullable=False, default=SupplierPaymentState.POSTED.value)
    journal_entry_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True)
    reversal_journal_entry_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True)
    posted_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    posted_by_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    notes: Optional[str] = Column(Text, nullable=True)


class SupplierPaymentAllocation(BaseModel, TenantMixin):
    """Allocation of a supplier payment to one vendor bill."""
    __tablename__ = "supplier_payment_allocations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "payment_id", "invoice_id", name="uq_supplier_payment_invoice_allocation"),
        CheckConstraint("amount > 0", name="ck_supplier_payment_allocation_positive_amount"),
        Index("ix_supplier_payment_alloc_payment", "tenant_id", "payment_id"),
        Index("ix_supplier_payment_alloc_invoice", "tenant_id", "invoice_id"),
    )

    payment_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("supplier_payments.id", ondelete="RESTRICT"), nullable=False)
    invoice_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("purchase_invoices.id", ondelete="RESTRICT"), nullable=False)
    amount: Decimal = Column(Numeric(18, 4), nullable=False)


# ========================================
# Supplier Info
# ========================================

class SupplierInfo(BaseModel):
    """
    Supplier Info Model (معلومات المورد للمنتج)
    
    Links products to suppliers with specific pricing and terms.
    """
    __tablename__ = "supplier_infos"
    __table_args__ = (
        Index("ix_supplier_infos_product", "product_id"),
        Index("ix_supplier_infos_partner", "partner_id"),
    )
    
    product_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    partner_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="CASCADE"),
        nullable=False
    )
    
    product_name: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Supplier's product name"
    )
    product_code: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Supplier's product code"
    )
    
    # Pricing
    price: Decimal = Column(Numeric(18, 4), nullable=False)
    currency_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Min Quantity
    min_qty: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Lead Time
    delay: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Lead time in days"
    )

    
    sequence: int = Column(Integer, default=10, nullable=False)
    is_active: bool = Column(Boolean, default=True, nullable=False)


# ========================================
# Update Invoice Model to link to Purchase Order
# ========================================

# Note: The Invoice model in sales.py already has purchase_order_id field
# We need to add the relationship dynamically or in the Invoice model itself
