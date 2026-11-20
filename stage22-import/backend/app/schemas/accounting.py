"""
Nexus ERP - Accounting Schemas
===============================

Pydantic schemas for accounting module API validation and serialization.
"""

from datetime import datetime, date as Date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from uuid import UUID
from decimal import Decimal
import re


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
            Date: lambda v: v.isoformat() if v else None,
            Decimal: lambda v: float(v) if v else None,
        }
    )


# ========================================
# Account Schemas
# ========================================

class AccountBriefResponse(BaseSchema):
    """Brief account information for nested responses."""
    id: UUID
    code: str
    name: str
    account_type: str
    is_active: bool = True


class AccountCreate(BaseModel):
    """Schema for creating an account."""
    code: str = Field(..., min_length=1, max_length=20, description="Unique account code")
    name: str = Field(..., min_length=1, max_length=255, description="Account name")
    name_ar: Optional[str] = Field(None, max_length=255, description="Arabic name")
    account_type: str = Field(..., description="Account type")
    category: Optional[str] = Field(None, description="Account category")
    parent_id: Optional[UUID] = Field(None, description="Parent account ID")
    is_active: bool = Field(default=True)
    is_header: bool = Field(default=False, description="Header accounts cannot have entries")
    is_reconcilable: bool = Field(default=False)
    currency_id: Optional[UUID] = None
    opening_debit: Decimal = Field(default=Decimal("0"), ge=0)
    opening_credit: Decimal = Field(default=Decimal("0"), ge=0)
    notes: Optional[str] = None
    
    @field_validator('account_type')
    @classmethod
    def validate_account_type(cls, v: str) -> str:
        allowed = ['asset', 'liability', 'equity', 'revenue', 'expense',
                   'contra_asset', 'contra_liability', 'contra_equity',
                   'contra_revenue', 'contra_expense']
        if v.lower() not in allowed:
            raise ValueError(f'Account type must be one of: {allowed}')
        return v.lower()
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not re.match(r'^[A-Za-z0-9\-\.]+$', v):
            raise ValueError('Code can only contain letters, numbers, hyphens, and dots')
        return v.upper()


class AccountUpdate(BaseModel):
    """Schema for updating an account."""
    name: Optional[str] = Field(None, max_length=255)
    name_ar: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = None
    parent_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    is_header: Optional[bool] = None
    is_reconcilable: Optional[bool] = None
    currency_id: Optional[UUID] = None
    notes: Optional[str] = None


class AccountResponse(AccountBriefResponse):
    """Full account response schema."""
    name_ar: Optional[str] = None
    category: Optional[str] = None
    parent_id: Optional[UUID] = None
    level: int = 0
    is_parent: bool = False
    is_header: bool = False
    is_reconcilable: bool = False
    is_contra: bool = False
    
    debit_balance: Decimal = Decimal("0")
    credit_balance: Decimal = Decimal("0")
    balance: Decimal = Decimal("0")
    opening_debit: Decimal = Decimal("0")
    opening_credit: Decimal = Decimal("0")
    
    currency_id: Optional[UUID] = None
    normal_balance: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Children for tree view
    children: List["AccountResponse"] = []


class AccountListResponse(BaseModel):
    """Paginated account list response."""
    items: List[AccountResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AccountTreeResponse(BaseSchema):
    """Account tree structure for hierarchical display."""
    id: UUID
    code: str
    name: str
    account_type: str
    balance: Decimal = Decimal("0")
    children: List["AccountTreeResponse"] = []


# ========================================
# Journal Entry Schemas
# ========================================

class JournalItemCreate(BaseModel):
    """Schema for creating a journal item."""
    account_id: UUID = Field(..., description="Account ID")
    debit: Decimal = Field(default=Decimal("0"), ge=0, description="Debit amount")
    credit: Decimal = Field(default=Decimal("0"), ge=0, description="Credit amount")
    name: Optional[str] = Field(None, max_length=255, description="Line description")
    partner_id: Optional[UUID] = Field(None, description="Partner (customer/supplier) ID")
    partner_type: Optional[str] = Field(None, description="Partner type")
    analytic_account_id: Optional[UUID] = Field(None, description="Analytic account ID")
    notes: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_amounts(self):
        if self.debit > 0 and self.credit > 0:
            raise ValueError('A line cannot have both debit and credit amounts')
        if self.debit == 0 and self.credit == 0:
            raise ValueError('Either debit or credit must be greater than zero')
        return self


class JournalItemResponse(BaseSchema):
    """Journal item response schema."""
    id: UUID
    account_id: UUID
    account: Optional[AccountBriefResponse] = None
    sequence: int
    debit: Decimal
    credit: Decimal
    name: Optional[str] = None
    partner_id: Optional[UUID] = None
    analytic_account_id: Optional[UUID] = None
    date: Date
    notes: Optional[str] = None


class JournalEntryCreate(BaseModel):
    """Schema for creating a journal entry."""
    date: Date = Field(..., description="Entry date")
    ref: Optional[str] = Field(None, max_length=100, description="Reference number")
    move_type: str = Field(default="manual", description="Entry type")
    journal_id: Optional[UUID] = Field(None, description="Journal ID")
    description: Optional[str] = Field(None, description="Entry description")
    narration: Optional[str] = Field(None, description="Additional narration")
    currency_id: Optional[UUID] = None
    exchange_rate: Decimal = Field(default=Decimal("1"))
    lines: List[JournalItemCreate] = Field(..., min_length=2, description="Entry lines")
    notes: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_balanced(self):
        total_debit = sum(line.debit for line in self.lines)
        total_credit = sum(line.credit for line in self.lines)
        if abs(total_debit - total_credit) > Decimal("0.01"):
            raise ValueError(
                f'Entry must be balanced. Debit: {total_debit}, Credit: {total_credit}'
            )
        return self


class JournalEntryUpdate(BaseModel):
    """Schema for updating a journal entry."""
    date: Optional[Date] = None
    ref: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    narration: Optional[str] = None
    notes: Optional[str] = None
    lines: Optional[List[JournalItemCreate]] = None
    
    @model_validator(mode='after')
    def validate_balanced_if_lines(self):
        if self.lines is not None:
            total_debit = sum(line.debit for line in self.lines)
            total_credit = sum(line.credit for line in self.lines)
            if abs(total_debit - total_credit) > Decimal("0.01"):
                raise ValueError('Entry must be balanced')
        return self


class JournalEntryResponse(BaseSchema):
    """Full journal entry response."""
    id: UUID
    number: str
    ref: Optional[str] = None
    date: Date
    move_type: str
    state: str
    journal_id: Optional[UUID] = None
    
    total_debit: Decimal
    total_credit: Decimal
    
    description: Optional[str] = None
    narration: Optional[str] = None
    
    source_model: Optional[str] = None
    source_id: Optional[UUID] = None
    
    is_reversal: bool = False
    original_entry_id: Optional[UUID] = None
    
    posted_at: Optional[datetime] = None
    posted_by_id: Optional[UUID] = None
    
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    lines: List[JournalItemResponse] = []
    
    @property
    def is_balanced(self) -> bool:
        return abs(self.total_debit - self.total_credit) < Decimal("0.01")


class JournalEntryListResponse(BaseModel):
    """Paginated journal entry list."""
    items: List[JournalEntryResponse]
    total: int
    page: int
    page_size: int
    pages: int


class JournalEntryPostRequest(BaseModel):
    """Request to post a journal entry."""
    pass


class JournalEntryReverseRequest(BaseModel):
    """Request to reverse a journal entry."""
    date: Optional[Date] = Field(None, description="Reversal date")
    reason: Optional[str] = Field(None, description="Reversal reason")


# ========================================
# General Ledger Schemas
# ========================================

class GeneralLedgerLine(BaseSchema):
    """Single line in general ledger report."""
    date: Date
    entry_number: str
    entry_id: UUID
    account_code: str
    account_name: str
    description: Optional[str] = None
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    balance: Decimal = Decimal("0")
    running_balance: Decimal = Decimal("0")
    partner_name: Optional[str] = None
    ref: Optional[str] = None


class GeneralLedgerRequest(BaseModel):
    """Request for general ledger report."""
    account_id: Optional[UUID] = Field(None, description="Filter by account")
    account_codes: Optional[List[str]] = Field(None, description="Filter by account codes")
    date_from: Date = Field(..., description="Start date")
    date_to: Date = Field(..., description="End date")
    partner_id: Optional[UUID] = Field(None, description="Filter by partner")
    include_opening: bool = Field(default=True, description="Include opening balance")
    
    @model_validator(mode='after')
    def validate_dates(self):
        if self.date_from > self.date_to:
            raise ValueError('date_from must be before date_to')
        return self


class GeneralLedgerResponse(BaseModel):
    """General ledger report response."""
    account_id: Optional[UUID] = None
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    date_from: Date
    date_to: Date
    
    opening_debit: Decimal = Decimal("0")
    opening_credit: Decimal = Decimal("0")
    opening_balance: Decimal = Decimal("0")
    
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")
    
    closing_debit: Decimal = Decimal("0")
    closing_credit: Decimal = Decimal("0")
    closing_balance: Decimal = Decimal("0")
    
    lines: List[GeneralLedgerLine] = []


# ========================================
# Financial Report Schemas
# ========================================

class TrialBalanceLine(BaseSchema):
    """Single line in trial balance."""
    account_id: UUID
    account_code: str
    account_name: str
    account_type: str
    opening_debit: Decimal = Decimal("0")
    opening_credit: Decimal = Decimal("0")
    period_debit: Decimal = Decimal("0")
    period_credit: Decimal = Decimal("0")
    closing_debit: Decimal = Decimal("0")
    closing_credit: Decimal = Decimal("0")


class TrialBalanceRequest(BaseModel):
    """Request for trial balance report."""
    date_from: Date = Field(..., description="Start date")
    date_to: Date = Field(..., description="End date")
    include_zero_balances: bool = Field(default=False)
    group_by_type: bool = Field(default=True)


class TrialBalanceResponse(BaseModel):
    """Trial balance report response."""
    date_from: Date
    date_to: Date
    generated_at: datetime
    
    total_opening_debit: Decimal = Decimal("0")
    total_opening_credit: Decimal = Decimal("0")
    total_period_debit: Decimal = Decimal("0")
    total_period_credit: Decimal = Decimal("0")
    total_closing_debit: Decimal = Decimal("0")
    total_closing_credit: Decimal = Decimal("0")
    
    is_balanced: bool
    lines: List[TrialBalanceLine] = []


class IncomeStatementLine(BaseSchema):
    """Single line in income statement."""
    account_id: UUID
    account_code: str
    account_name: str
    category: Optional[str] = None
    amount: Decimal = Decimal("0")
    percentage: Optional[Decimal] = None


class IncomeStatementSection(BaseSchema):
    """Section in income statement."""
    title: str
    total: Decimal = Decimal("0")
    percentage: Optional[Decimal] = None
    lines: List[IncomeStatementLine] = []


class IncomeStatementRequest(BaseModel):
    """Request for income statement."""
    date_from: Date = Field(..., description="Start date")
    date_to: Date = Field(..., description="End date")
    comparison_date_from: Optional[Date] = Field(None, description="Comparison period start")
    comparison_date_to: Optional[Date] = Field(None, description="Comparison period end")
    show_percentages: bool = Field(default=True)


class IncomeStatementResponse(BaseModel):
    """Income statement response."""
    date_from: Date
    date_to: Date
    comparison_date_from: Optional[Date] = None
    comparison_date_to: Optional[Date] = None
    generated_at: datetime
    
    revenue: IncomeStatementSection
    cost_of_sales: IncomeStatementSection
    gross_profit: Decimal = Decimal("0")
    gross_profit_percentage: Optional[Decimal] = None
    
    operating_expenses: IncomeStatementSection
    operating_income: Decimal = Decimal("0")
    operating_income_percentage: Optional[Decimal] = None
    
    other_income: IncomeStatementSection
    other_expenses: IncomeStatementSection
    
    net_income: Decimal = Decimal("0")
    net_income_percentage: Optional[Decimal] = None


class BalanceSheetLine(BaseSchema):
    """Single line in balance sheet."""
    account_id: UUID
    account_code: str
    account_name: str
    amount: Decimal = Decimal("0")
    percentage: Optional[Decimal] = None


class BalanceSheetSection(BaseSchema):
    """Section in balance sheet."""
    title: str
    total: Decimal = Decimal("0")
    percentage: Optional[Decimal] = None
    lines: List[BalanceSheetLine] = []


class BalanceSheetRequest(BaseModel):
    """Request for balance sheet."""
    date: Date = Field(..., description="As of date")
    comparison_date: Optional[Date] = Field(None, description="Comparison date")
    show_percentages: bool = Field(default=True)


class BalanceSheetResponse(BaseModel):
    """Balance sheet response."""
    date: Date
    comparison_date: Optional[Date] = None
    generated_at: datetime
    
    # Assets
    current_assets: BalanceSheetSection
    fixed_assets: BalanceSheetSection
    other_assets: BalanceSheetSection
    total_assets: Decimal = Decimal("0")
    
    # Liabilities
    current_liabilities: BalanceSheetSection
    long_term_liabilities: BalanceSheetSection
    other_liabilities: BalanceSheetSection
    total_liabilities: Decimal = Decimal("0")
    
    # Equity
    equity: BalanceSheetSection
    total_equity: Decimal = Decimal("0")
    
    total_liabilities_and_equity: Decimal = Decimal("0")
    is_balanced: bool


# ========================================
# Fiscal Period Schemas
# ========================================

class FiscalYearCreate(BaseModel):
    """Schema for creating a fiscal year."""
    name: str = Field(..., max_length=100)
    start_date: Date
    end_date: Date
    
    @model_validator(mode='after')
    def validate_dates(self):
        if self.start_date >= self.end_date:
            raise ValueError('start_date must be before end_date')
        return self


class FiscalYearResponse(BaseSchema):
    """Fiscal year response."""
    id: UUID
    name: str
    start_date: Date
    end_date: Date
    is_closed: bool
    closed_at: Optional[datetime] = None
    periods: List["FiscalPeriodResponse"] = []


class FiscalPeriodResponse(BaseSchema):
    """Fiscal period response."""
    id: UUID
    fiscal_year_id: UUID
    name: str
    period_number: int
    start_date: Date
    end_date: Date
    is_closed: bool
    is_adjustment: bool


# ========================================
# Partner Schemas
# ========================================

class PartnerBriefResponse(BaseSchema):
    """Brief partner information."""
    id: UUID
    name: str
    partner_type: str
    code: Optional[str] = None


class PartnerCreate(BaseModel):
    """Schema for creating a partner."""
    name: str = Field(..., max_length=255)
    partner_type: str = Field(..., description="customer, supplier, or both")
    code: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    receivable_account_id: Optional[UUID] = None
    payable_account_id: Optional[UUID] = None
    
    @field_validator('partner_type')
    @classmethod
    def validate_partner_type(cls, v: str) -> str:
        allowed = ['customer', 'supplier', 'both']
        if v.lower() not in allowed:
            raise ValueError(f'Partner type must be one of: {allowed}')
        return v.lower()


class PartnerResponse(PartnerBriefResponse):
    """Full partner response."""
    email: Optional[str] = None
    phone: Optional[str] = None
    receivable_account_id: Optional[UUID] = None
    payable_account_id: Optional[UUID] = None
    receivable_balance: Decimal = Decimal("0")
    payable_balance: Decimal = Decimal("0")
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


# ========================================
# Analytic Account Schemas
# ========================================

class AnalyticAccountCreate(BaseModel):
    """Schema for creating an analytic account."""
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=255)
    parent_id: Optional[UUID] = None
    partner_id: Optional[UUID] = None


class AnalyticAccountResponse(BaseSchema):
    """Analytic account response."""
    id: UUID
    code: str
    name: str
    parent_id: Optional[UUID] = None
    partner_id: Optional[UUID] = None
    is_active: bool
    debit_balance: Decimal = Decimal("0")
    credit_balance: Decimal = Decimal("0")
    balance: Decimal = Decimal("0")


# Update forward references
AccountResponse.model_rebuild()
AccountTreeResponse.model_rebuild()
JournalEntryResponse.model_rebuild()
FiscalYearResponse.model_rebuild()


# ========================================
# Bank Reconciliation Schemas
# ========================================

class BankStatementCreate(BaseModel):
    account_id: UUID
    statement_number: str = Field(..., min_length=1, max_length=100)
    start_date: Date
    end_date: Date
    opening_balance: Decimal
    closing_balance: Decimal
    currency_code: Optional[str] = Field(None, min_length=3, max_length=3)
    notes: Optional[str] = None


class BankStatementLineCreate(BaseModel):
    line_number: int = Field(..., ge=1)
    transaction_date: Date
    value_date: Optional[Date] = None
    description: str = Field(..., min_length=1, max_length=500)
    external_reference: Optional[str] = Field(None, max_length=150)
    debit: Decimal = Field(default=Decimal("0"), ge=0)
    credit: Decimal = Field(default=Decimal("0"), ge=0)


class BankStatementMatch(BaseModel):
    journal_item_id: UUID
