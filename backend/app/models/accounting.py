"""
Nexus ERP - Accounting Models
==============================

This module implements comprehensive accounting functionality including:
- Chart of Accounts (hierarchical account structure)
- Journal Entries (double-entry bookkeeping)
- Financial Statements generation
- Fiscal Periods management

Features:
- Full double-entry bookkeeping
- Multi-currency support
- Analytic accounting
- Automatic balance calculations
- Audit trail
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
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import event, func
from typing import Optional, List
from decimal import Decimal
import enum
import uuid

from app.models.base import BaseModel, TenantMixin


# ========================================
# Enums
# ========================================

class AccountType(str, enum.Enum):
    """Account type classification."""
    ASSET = "asset"                    # أصول
    LIABILITY = "liability"            # خصوم
    EQUITY = "equity"                  # حقوق الملكية
    REVENUE = "revenue"                # إيرادات
    EXPENSE = "expense"                # مصروفات
    CONTRA_ASSET = "contra_asset"      # أصول مقابلة
    CONTRA_LIABILITY = "contra_liability"
    CONTRA_EQUITY = "contra_equity"
    CONTRA_REVENUE = "contra_revenue"
    CONTRA_EXPENSE = "contra_expense"


class AccountCategory(str, enum.Enum):
    """Account category for reporting."""
    CASH = "cash"
    BANK = "bank"
    RECEIVABLE = "receivable"
    INVENTORY = "inventory"
    FIXED_ASSET = "fixed_asset"
    PAYABLE = "payable"
    TAX = "tax"
    CAPITAL = "capital"
    SALES = "sales"
    COST_OF_SALES = "cost_of_sales"
    OPERATING_EXPENSE = "operating_expense"
    OTHER_INCOME = "other_income"
    OTHER_EXPENSE = "other_expense"


class EntryState(str, enum.Enum):
    """Journal entry state."""
    DRAFT = "draft"            # مسودة
    POSTED = "posted"          # مرحلة
    CANCELLED = "cancelled"    # ملغاة


class MoveType(str, enum.Enum):
    """Journal entry move type."""
    MANUAL = "manual"              # قيد يدوي
    SALES = "sales"                # مبيعات
    PURCHASE = "purchase"          # مشتريات
    PAYMENT = "payment"            # سداد
    RECEIPT = "receipt"            # قبض
    TRANSFER = "transfer"          # تحويل
    ADJUSTMENT = "adjustment"      # تسوية
    DEPRECIATION = "depreciation"  # إهلاك
    CLOSING = "closing"            # إقفال
    OPENING = "opening"            # افتتاحي


# ========================================
# Fiscal Period
# ========================================

class FiscalYear(BaseModel, TenantMixin):
    """
    Fiscal Year Model
    
    Represents a financial year for accounting purposes.
    """
    __tablename__ = "fiscal_years"
    __table_args__ = (
        Index("ix_fiscal_years_tenant", "tenant_id"),
        UniqueConstraint("name", "tenant_id", name="uq_fiscal_year_tenant_name"),
    )
    
    name: str = Column(String(100), nullable=False, doc="Year name (e.g., '2024')")
    start_date: date = Column(Date, nullable=False, doc="Year start date")
    end_date: date = Column(Date, nullable=False, doc="Year end date")
    is_closed: bool = Column(Boolean, default=False, nullable=False, doc="Whether year is closed")
    closed_at: Optional[datetime] = Column(DateTime, nullable=True, doc="When year was closed")
    closed_by_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Relationships
    periods: Mapped[List["FiscalPeriod"]] = relationship(
        "FiscalPeriod", back_populates="fiscal_year", lazy="dynamic"
    )


class FiscalPeriod(BaseModel, TenantMixin):
    """
    Fiscal Period Model
    
    Represents a period (month/quarter) within a fiscal year.
    """
    __tablename__ = "fiscal_periods"
    __table_args__ = (
        Index("ix_fiscal_periods_fiscal_year", "fiscal_year_id"),
        Index("ix_fiscal_periods_date", "start_date", "end_date"),
        UniqueConstraint("fiscal_year_id", "period_number", name="uq_period_number"),
    )
    
    fiscal_year_id: uuid.UUID = Column(
        UUID(as_uuid=True), ForeignKey("fiscal_years.id"), nullable=False
    )
    name: str = Column(String(50), nullable=False, doc="Period name")
    period_number: int = Column(Integer, nullable=False, doc="Period number (1-12)")
    start_date: date = Column(Date, nullable=False)
    end_date: date = Column(Date, nullable=False)
    is_closed: bool = Column(Boolean, default=False, nullable=False)
    is_adjustment: bool = Column(Boolean, default=False, nullable=False, doc="Adjustment period")
    
    # Relationships
    fiscal_year: Mapped["FiscalYear"] = relationship("FiscalYear", back_populates="periods")


# ========================================
# Chart of Accounts
# ========================================

class Account(BaseModel, TenantMixin):
    """
    Account Model
    
    Represents an account in the Chart of Accounts.
    Supports hierarchical structure with parent-child relationships.
    """
    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_accounts_code_tenant", "code", "tenant_id", unique=True),
        Index("ix_accounts_parent", "parent_id"),
        Index("ix_accounts_type", "account_type"),
        Index("ix_accounts_tenant", "tenant_id"),
        CheckConstraint("debit_balance >= 0", name="ck_account_debit_balance"),
        CheckConstraint("credit_balance >= 0", name="ck_account_credit_balance"),
    )
    
    # Basic Information
    code: str = Column(
        String(20),
        nullable=False,
        doc="Unique account code (e.g., '1000', '4001')"
    )
    name: str = Column(
        String(255),
        nullable=False,
        doc="Account name"
    )
    name_ar: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Arabic account name"
    )
    
    # Classification
    account_type: AccountType = Column(
        SQLEnum(AccountType),
        nullable=False,
        doc="Account type (Asset, Liability, Equity, Revenue, Expense)"
    )
    category: Optional[AccountCategory] = Column(
        SQLEnum(AccountCategory),
        nullable=True,
        doc="Account category for reporting"
    )
    
    # Hierarchy
    parent_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        doc="Parent account for hierarchical structure"
    )
    level: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Hierarchy level (0 = root)"
    )
    is_parent: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this account has children"
    )
    
    # Configuration
    is_active: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether account is active"
    )
    is_header: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Header account (cannot have entries)"
    )
    is_reconcilable: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Supports reconciliation (bank, receivable, payable)"
    )
    is_contra: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Contra account"
    )
    
    # Balances (Computed/Updated)
    debit_balance: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Total debit balance"
    )
    credit_balance: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Total credit balance"
    )
    balance: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Net balance (debit - credit)"
    )
    
    # Opening Balance
    opening_debit: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Opening debit balance"
    )
    opening_credit: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Opening credit balance"
    )
    
    # Currency
    currency_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("currencies.id", ondelete="SET NULL"),
        nullable=True,
        doc="Account currency (if multi-currency)"
    )
    
    # Partner Linking
    partner_type: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Partner type (customer, supplier, employee)"
    )
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    tags: List[str] = Column(
        "ARRAY(String)",
        default=list,
        nullable=False
    )
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    parent: Mapped[Optional["Account"]] = relationship(
        "Account",
        remote_side="Account.id",
        backref="children"
    )
    
    journal_items: Mapped[List["JournalItem"]] = relationship(
        "JournalItem",
        back_populates="account",
        lazy="dynamic"
    )
    
    
    # ========================================
    # Computed Properties
    # ========================================
    
    @property
    def normal_balance(self) -> str:
        """
        Get the normal balance side for this account type.
        
        Returns:
            'debit' for assets and expenses
            'credit' for liabilities, equity, and revenue
        """
        debit_types = {
            AccountType.ASSET, AccountType.EXPENSE,
            AccountType.CONTRA_LIABILITY, AccountType.CONTRA_EQUITY, AccountType.CONTRA_REVENUE
        }
        return 'debit' if self.account_type in debit_types else 'credit'
    
    @property
    def is_debit_account(self) -> bool:
        """Check if account normally has debit balance."""
        return self.normal_balance == 'debit'
    
    def update_balance(self, debit: Decimal, credit: Decimal):
        """
        Update account balance with new amounts.
        
        Args:
            debit: Debit amount to add
            credit: Credit amount to add
        """
        self.debit_balance += debit
        self.credit_balance += credit
        
        # Calculate net balance based on account type
        if self.is_debit_account:
            self.balance = self.debit_balance - self.credit_balance
        else:
            self.balance = self.credit_balance - self.debit_balance
    
    def get_children_recursive(self) -> List["Account"]:
        """Get all child accounts recursively."""
        children = list(self.children) if self.children else []
        for child in children:
            children.extend(child.get_children_recursive())
        return children


# ========================================
# Journal Entry
# ========================================

class JournalEntry(BaseModel, TenantMixin):
    """
    Journal Entry Model
    
    Represents a double-entry journal entry with multiple lines.
    Each entry must be balanced (total debits = total credits).
    """
    __tablename__ = "journal_entries"
    __table_args__ = (
        Index("ix_journal_entries_number", "number"),
        Index("ix_journal_entries_date", "date"),
        Index("ix_journal_entries_state", "state"),
        Index("ix_journal_entries_tenant", "tenant_id"),
        Index("ix_journal_entries_fiscal_period", "fiscal_period_id"),
        # A source document may produce at most one active journal entry per tenant.
        # Reversal entries intentionally have no source document and are excluded.
        Index(
            "uq_journal_entry_tenant_source",
            "tenant_id", "source_model", "source_id",
            unique=True,
            postgresql_where=(
                text("source_model IS NOT NULL AND source_id IS NOT NULL AND is_deleted = false")
            ),
        ),
        CheckConstraint(
            "total_debit = total_credit",
            name="ck_journal_entry_balanced"
        ),
    )
    
    # Entry Identification
    number: str = Column(
        String(50),
        nullable=False,
        doc="Entry number (auto-generated)"
    )
    ref: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Reference number"
    )
    
    # Date and Period
    date: date = Column(
        Date,
        nullable=False,
        doc="Entry date"
    )
    fiscal_period_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("fiscal_periods.id", ondelete="SET NULL"),
        nullable=True,
        doc="Fiscal period"
    )
    
    # Classification
    move_type: MoveType = Column(
        SQLEnum(MoveType),
        default=MoveType.MANUAL,
        nullable=False,
        doc="Entry type"
    )
    journal_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("journals.id", ondelete="SET NULL"),
        nullable=True,
        doc="Journal"
    )
    
    # State
    state: EntryState = Column(
        SQLEnum(EntryState),
        default=EntryState.DRAFT,
        nullable=False,
        doc="Entry state"
    )
    
    # Totals
    total_debit: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Total debit amount"
    )
    total_credit: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Total credit amount"
    )
    
    # Description
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Entry description"
    )
    narration: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Additional narration"
    )
    
    # Source Document
    source_model: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Source model name (e.g., 'purchase.invoice')"
    )
    source_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Source document ID"
    )
    
    # Currency
    currency_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("currencies.id", ondelete="SET NULL"),
        nullable=True
    )
    exchange_rate: Decimal = Column(
        Numeric(12, 6),
        default=Decimal("1"),
        nullable=False
    )
    
    # Reversal
    is_reversal: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this is a reversal entry"
    )
    original_entry_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
        doc="Original entry being reversed"
    )
    
    # Posting Info
    posted_at: Optional[datetime] = Column(
        DateTime,
        nullable=True,
        doc="When entry was posted"
    )
    posted_by_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    lines: Mapped[List["JournalItem"]] = relationship(
        "JournalItem",
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="JournalItem.sequence"
    )
    
    journal: Mapped[Optional["Journal"]] = relationship(
        "Journal",
        back_populates="entries"
    )
    
    fiscal_period: Mapped[Optional["FiscalPeriod"]] = relationship(
        "FiscalPeriod"
    )
    
    original_entry: Mapped[Optional["JournalEntry"]] = relationship(
        "JournalEntry",
        remote_side="JournalEntry.id",
        backref="reversals"
    )
    
    # ========================================
    # Computed Properties
    # ========================================
    
    @property
    def is_balanced(self) -> bool:
        """Check if entry is balanced."""
        return abs(self.total_debit - self.total_credit) < Decimal("0.001")
    
    @property
    def is_posted(self) -> bool:
        """Check if entry is posted."""
        return self.state == EntryState.POSTED
    
    @property
    def can_edit(self) -> bool:
        """Check if entry can be edited."""
        return self.state == EntryState.DRAFT
    
    @property
    def line_count(self) -> int:
        """Get number of lines."""
        return len(self.lines) if self.lines else 0
    
    def calculate_totals(self):
        """Calculate and update total debit and credit."""
        self.total_debit = sum(line.debit for line in self.lines) if self.lines else Decimal("0")
        self.total_credit = sum(line.credit for line in self.lines) if self.lines else Decimal("0")
    
    def post(self, user_id: uuid.UUID):
        """
        Post the journal entry.
        
        Args:
            user_id: ID of user posting the entry
            
        Raises:
            ValueError: If entry is not balanced or already posted
        """
        if self.state != EntryState.DRAFT:
            raise ValueError("Only draft entries can be posted")
        
        if not self.is_balanced:
            raise ValueError("Entry must be balanced before posting")
        
        self.state = EntryState.POSTED
        self.posted_at = datetime.utcnow()
        self.posted_by_id = user_id
    
    def cancel(self):
        """Cancel the journal entry."""
        if self.state == EntryState.POSTED:
            raise ValueError("Cannot cancel posted entries. Create a reversal instead.")
        self.state = EntryState.CANCELLED


# ========================================
# Journal Item
# ========================================

class JournalItem(BaseModel, TenantMixin):
    """
    Journal Item Model
    
    Represents a single line in a journal entry.
    """
    __tablename__ = "journal_items"
    __table_args__ = (
        Index("ix_journal_items_entry", "entry_id"),
        Index("ix_journal_items_account", "account_id"),
        Index("ix_journal_items_partner", "partner_id"),
        Index("ix_journal_items_date", "date"),
        CheckConstraint(
            "debit >= 0 AND credit >= 0",
            name="ck_journal_item_amounts_positive"
        ),
        CheckConstraint(
            "NOT (debit > 0 AND credit > 0)",
            name="ck_journal_item_not_both"
        ),
    )
    
    # Entry Reference
    entry_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Account
    account_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    # Sequence
    sequence: int = Column(
        Integer,
        default=10,
        nullable=False,
        doc="Line sequence"
    )
    
    # Amounts
    debit: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Debit amount"
    )
    credit: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Credit amount"
    )
    
    # Balance (after transaction)
    balance_after: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Account balance after this transaction"
    )
    
    # Date (for reporting)
    date: date = Column(
        Date,
        nullable=False,
        doc="Transaction date (copied from entry)"
    )
    
    # Partner (Customer/Supplier)
    partner_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="SET NULL"),
        nullable=True,
        doc="Partner (customer/supplier)"
    )
    partner_type: Optional[str] = Column(
        String(20),
        nullable=True
    )
    
    # Analytic Accounting
    analytic_account_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("analytic_accounts.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Reconciliation
    reconciliation_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("reconciliations.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reconciliation reference"
    )
    
    # Description
    name: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Line description"
    )
    
    # Source Document
    source_model: Optional[str] = Column(String(100), nullable=True)
    source_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Currency
    currency_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    amount_currency: Optional[Decimal] = Column(
        Numeric(18, 4),
        nullable=True,
        doc="Amount in foreign currency"
    )
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    
    # ========================================
    # Relationships
    # ========================================
    entry: Mapped["JournalEntry"] = relationship(
        "JournalEntry",
        back_populates="lines"
    )
    
    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="journal_items"
    )
    
    analytic_account: Mapped[Optional["AnalyticAccount"]] = relationship(
        "AnalyticAccount",
        back_populates="lines"
    )
    
    @property
    def amount(self) -> Decimal:
        """Get the transaction amount."""
        return self.debit if self.debit > 0 else self.credit


# ========================================
# Journal
# ========================================

class Journal(BaseModel, TenantMixin):
    """
    Journal Model
    
    Represents a journal for organizing entries by type.
    """
    __tablename__ = "journals"
    __table_args__ = (
        Index("ix_journals_code_tenant", "code", "tenant_id", unique=True),
    )
    
    code: str = Column(String(20), nullable=False, doc="Journal code")
    name: str = Column(String(100), nullable=False, doc="Journal name")
    journal_type: str = Column(
        String(20),
        nullable=False,
        doc="Journal type (sale, purchase, cash, bank, general)"
    )
    
    default_account_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True
    )
    
    sequence_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Sequence for entry numbers"
    )
    
    is_active: bool = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    entries: Mapped[List["JournalEntry"]] = relationship(
        "JournalEntry",
        back_populates="journal"
    )


# ========================================
# Analytic Accounting
# ========================================

class AnalyticAccount(BaseModel, TenantMixin):
    """
    Analytic Account Model
    
    For cost center and project-based accounting.
    """
    __tablename__ = "analytic_accounts"
    __table_args__ = (
        Index("ix_analytic_accounts_code", "code"),
    )
    
    code: str = Column(String(20), nullable=False)
    name: str = Column(String(255), nullable=False)
    parent_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("analytic_accounts.id", ondelete="SET NULL"),
        nullable=True
    )
    partner_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    is_active: bool = Column(Boolean, default=True, nullable=False)
    
    # Balance
    debit_balance: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    credit_balance: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    balance: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    
    # Relationships
    lines: Mapped[List["JournalItem"]] = relationship(
        "JournalItem",
        back_populates="analytic_account"
    )
    analytic_lines: Mapped[List["AnalyticLine"]] = relationship(
        "AnalyticLine",
        back_populates="analytic_account"
    )


class AnalyticLine(BaseModel, TenantMixin):
    """Analytic distribution line."""
    __tablename__ = "analytic_lines"
    
    journal_item_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("journal_items.id", ondelete="CASCADE"),
        nullable=False
    )
    analytic_account_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("analytic_accounts.id"),
        nullable=False
    )
    amount: Decimal = Column(Numeric(18, 4), nullable=False)
    percentage: Decimal = Column(Numeric(5, 2), default=Decimal("100"))
    
    # Relationships
    analytic_account: Mapped["AnalyticAccount"] = relationship(
        "AnalyticAccount", back_populates="analytic_lines"
    )


# ========================================
# Reconciliation
# ========================================

class Reconciliation(BaseModel, TenantMixin):
    """
    Reconciliation Model
    
    Links journal items for reconciliation (payments, etc.)
    """
    __tablename__ = "reconciliations"
    
    name: str = Column(String(50), nullable=False)
    date: date = Column(Date, nullable=False)
    account_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("accounts.id"))
    
    total_debit: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    total_credit: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    
    is_full: bool = Column(Boolean, default=False)
    is_partial: bool = Column(Boolean, default=False)


# ========================================
# Partner (for linking)
# ========================================

class Partner(BaseModel, TenantMixin):
    """
    Partner Model (Customer/Supplier)
    
    Unified model for both customers and suppliers.
    """
    __tablename__ = "partners"
    
    name: str = Column(String(255), nullable=False)
    partner_type: str = Column(String(20), nullable=False)  # customer, supplier, both
    code: Optional[str] = Column(String(50), nullable=True)
    
    # Contact
    email: Optional[str] = Column(String(255), nullable=True)
    phone: Optional[str] = Column(String(20), nullable=True)
    
    # Accounts
    receivable_account_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    payable_account_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Balance
    receivable_balance: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    payable_balance: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    
    is_active: bool = Column(Boolean, default=True)


# ========================================
# Currency (Reference)
# ========================================

class Currency(BaseModel):
    """Currency Model."""
    __tablename__ = "currencies"
    
    code: str = Column(String(3), unique=True, nullable=False)
    name: str = Column(String(50), nullable=False)
    symbol: str = Column(String(10), nullable=False)
    decimal_places: int = Column(Integer, default=2)
    is_active: bool = Column(Boolean, default=True)


# ========================================
# Bank Statements and Reconciliation
# ========================================

class BankStatementState(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    RECONCILED = "reconciled"
    CANCELLED = "cancelled"


class BankStatement(BaseModel, TenantMixin):
    """Imported bank statement header; source files are not retained in this model."""
    __tablename__ = "bank_statements"
    __table_args__ = (
        UniqueConstraint("tenant_id", "account_id", "statement_number", name="uq_bank_statement_tenant_account_number"),
        Index("ix_bank_statements_tenant_account_period", "tenant_id", "account_id", "start_date", "end_date"),
        CheckConstraint("end_date >= start_date", name="ck_bank_statement_date_range"),
    )

    account_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    statement_number: str = Column(String(100), nullable=False)
    start_date: date = Column(Date, nullable=False)
    end_date: date = Column(Date, nullable=False)
    opening_balance: Decimal = Column(Numeric(18, 4), nullable=False)
    closing_balance: Decimal = Column(Numeric(18, 4), nullable=False)
    total_debits: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total_credits: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    currency_code: Optional[str] = Column(String(3), nullable=True)
    state: BankStatementState = Column(SQLEnum(BankStatementState), default=BankStatementState.DRAFT, nullable=False)
    notes: Optional[str] = Column(Text, nullable=True)


class BankStatementLine(BaseModel, TenantMixin):
    """A single bank movement; debit/credit are expressed from the bank statement's perspective."""
    __tablename__ = "bank_statement_lines"
    __table_args__ = (
        UniqueConstraint("tenant_id", "statement_id", "line_number", name="uq_bank_statement_line_number"),
        UniqueConstraint("tenant_id", "matched_journal_item_id", name="uq_bank_statement_matched_journal_item"),
        Index(
            "uq_bank_statement_external_reference",
            "tenant_id", "statement_id", "external_reference",
            unique=True,
            postgresql_where=text("external_reference IS NOT NULL AND is_deleted = false"),
        ),
        CheckConstraint("debit >= 0 AND credit >= 0", name="ck_bank_statement_line_nonnegative"),
        CheckConstraint("NOT (debit > 0 AND credit > 0)", name="ck_bank_statement_line_one_side"),
        CheckConstraint("debit > 0 OR credit > 0", name="ck_bank_statement_line_positive"),
        Index("ix_bank_statement_lines_tenant_statement", "tenant_id", "statement_id"),
    )

    statement_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("bank_statements.id", ondelete="CASCADE"), nullable=False)
    line_number: int = Column(Integer, nullable=False)
    transaction_date: date = Column(Date, nullable=False)
    value_date: Optional[date] = Column(Date, nullable=True)
    description: str = Column(String(500), nullable=False)
    external_reference: Optional[str] = Column(String(150), nullable=True)
    debit: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    credit: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    matched_journal_item_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), ForeignKey("journal_items.id", ondelete="RESTRICT"), nullable=True)
    matched_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    matched_by_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
