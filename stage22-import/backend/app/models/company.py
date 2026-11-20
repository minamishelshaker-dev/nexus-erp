"""
Nexus ERP - Multi-Company Models
=================================

This module implements multi-company support within a tenant,
allowing for inter-company transactions and consolidated reporting.

Features:
- Multiple companies per tenant
- Inter-company transaction tracking
- Company-specific settings and branding
- Branch/location management
- Consolidated financial reporting
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    Index,
    Enum as SQLEnum,
    CheckConstraint,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, List
import enum
import uuid

from app.models.base import BaseModel, TenantMixin


class CompanyStatus(str, enum.Enum):
    """Company status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class CompanyType(str, enum.Enum):
    """Company type enumeration."""
    HEADQUARTERS = "headquarters"
    BRANCH = "branch"
    SUBSIDIARY = "subsidiary"
    DIVISION = "division"


class InterCompanyTransactionStatus(str, enum.Enum):
    """Inter-company transaction status."""
    DRAFT = "draft"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Company(BaseModel, TenantMixin):
    """
    Company Model
    
    Represents a company within a tenant. Supports multi-company operations
    with inter-company transactions and consolidated reporting.
    """
    
    __tablename__ = "companies"
    __table_args__ = (
        Index("ix_companies_code_tenant", "code", "tenant_id", unique=True),
        Index("ix_companies_status", "status"),
        Index("ix_companies_parent", "parent_company_id"),
        CheckConstraint(
            "length(code) >= 2",
            name="ck_companies_code_length"
        ),
    )
    
    # ========================================
    # Basic Information
    # ========================================
    code: str = Column(
        String(20),
        nullable=False,
        index=True,
        doc="Unique company code (e.g., 'HQ', 'BR001')"
    )
    
    name: str = Column(
        String(200),
        nullable=False,
        doc="Company legal name"
    )
    
    short_name: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Short display name"
    )
    
    company_type: CompanyType = Column(
        SQLEnum(CompanyType),
        default=CompanyType.BRANCH,
        nullable=False,
        doc="Type of company (headquarters, branch, subsidiary)"
    )
    
    status: CompanyStatus = Column(
        SQLEnum(CompanyStatus),
        default=CompanyStatus.ACTIVE,
        nullable=False,
        doc="Company status"
    )
    
    # ========================================
    # Parent Company (for hierarchy)
    # ========================================
    parent_company_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        doc="Parent company for subsidiaries/branches"
    )
    
    # ========================================
    # Contact Information
    # ========================================
    legal_name: Optional[str] = Column(
        String(200),
        nullable=True,
        doc="Legal registered name (if different from name)"
    )
    
    tax_id: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Tax identification number"
    )
    
    registration_number: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Company registration number"
    )
    
    email: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Company email address"
    )
    
    phone: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Company phone number"
    )
    
    fax: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Company fax number"
    )
    
    website: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Company website URL"
    )
    
    # ========================================
    # Address Information
    # ========================================
    street: Optional[str] = Column(
        String(200),
        nullable=True,
        doc="Street address"
    )
    
    street2: Optional[str] = Column(
        String(200),
        nullable=True,
        doc="Street address line 2"
    )
    
    city: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="City"
    )
    
    state: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="State/Province"
    )
    
    zip_code: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Postal/ZIP code"
    )
    
    country: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Country"
    )
    
    # ========================================
    # Financial Settings
    # ========================================
    currency_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("currencies.id", ondelete="SET NULL"),
        nullable=True,
        doc="Default currency for this company"
    )
    
    fiscal_year_start_month: int = Column(
        Integer,
        default=1,
        nullable=False,
        doc="Fiscal year start month (1-12)"
    )
    
    default_payable_account_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        doc="Default payable account"
    )
    
    default_receivable_account_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        doc="Default receivable account"
    )
    
    default_expense_account_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        doc="Default expense account"
    )
    
    default_income_account_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        doc="Default income account"
    )
    
    # ========================================
    # Branding & Display
    # ========================================
    logo_url: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="Company logo URL"
    )
    
    primary_color: Optional[str] = Column(
        String(7),
        nullable=True,
        doc="Primary brand color (hex)"
    )
    
    secondary_color: Optional[str] = Column(
        String(7),
        nullable=True,
        doc="Secondary brand color (hex)"
    )
    
    # ========================================
    # Settings & Configuration
    # ========================================
    settings: dict = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Company-specific settings and configuration"
    )
    
    is_default: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this is the default company"
    )
    
    allow_inter_company: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether inter-company transactions are allowed"
    )
    
    # ========================================
    # Relationships
    # ========================================
    parent_company: Mapped[Optional["Company"]] = relationship(
        "Company",
        remote_side="Company.id",
        backref="child_companies",
        lazy="selectin",
        doc="Parent company"
    )
    
    branches: Mapped[List["CompanyBranch"]] = relationship(
        "CompanyBranch",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="Branches belonging to this company"
    )
    
    inter_company_transactions_from: Mapped[List["InterCompanyTransaction"]] = relationship(
        "InterCompanyTransaction",
        foreign_keys="InterCompanyTransaction.from_company_id",
        back_populates="from_company",
        lazy="dynamic",
        doc="Inter-company transactions sent from this company"
    )
    
    inter_company_transactions_to: Mapped[List["InterCompanyTransaction"]] = relationship(
        "InterCompanyTransaction",
        foreign_keys="InterCompanyTransaction.to_company_id",
        back_populates="to_company",
        lazy="dynamic",
        doc="Inter-company transactions received by this company"
    )
    
    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = [self.street, self.street2, self.city, self.state, self.zip_code, self.country]
        return ", ".join(part for part in parts if part)
    
    @property
    def display_name(self) -> str:
        """Get display name."""
        return self.short_name or self.name


class CompanyBranch(BaseModel):
    """
    Company Branch Model
    
    Represents a branch or location within a company.
    """
    
    __tablename__ = "company_branches"
    __table_args__ = (
        Index("ix_company_branches_company", "company_id"),
        Index("ix_company_branches_code", "code"),
        UniqueConstraint("company_id", "code", name="uq_branch_code"),
    )
    
    company_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        doc="Parent company"
    )
    
    code: str = Column(
        String(20),
        nullable=False,
        doc="Branch code"
    )
    
    name: str = Column(
        String(200),
        nullable=False,
        doc="Branch name"
    )
    
    is_headquarters: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this is the headquarters location"
    )
    
    status: CompanyStatus = Column(
        SQLEnum(CompanyStatus),
        default=CompanyStatus.ACTIVE,
        nullable=False,
        doc="Branch status"
    )
    
    # Contact Info
    email: Optional[str] = Column(String(255), nullable=True)
    phone: Optional[str] = Column(String(20), nullable=True)
    street: Optional[str] = Column(String(200), nullable=True)
    city: Optional[str] = Column(String(100), nullable=True)
    state: Optional[str] = Column(String(100), nullable=True)
    zip_code: Optional[str] = Column(String(20), nullable=True)
    country: Optional[str] = Column(String(100), nullable=True)
    
    # Warehouse Assignment
    default_warehouse_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        doc="Default warehouse for this branch"
    )
    
    manager_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Branch manager"
    )
    
    # Relationships
    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="branches"
    )


class InterCompanyTransaction(BaseModel, TenantMixin):
    """
    Inter-Company Transaction Model
    
    Tracks transactions between companies within the same tenant.
    Enables consolidated reporting and proper elimination entries.
    """
    
    __tablename__ = "inter_company_transactions"
    __table_args__ = (
        Index("ix_inter_company_from", "from_company_id"),
        Index("ix_inter_company_to", "to_company_id"),
        Index("ix_inter_company_status", "status"),
        Index("ix_inter_company_date", "transaction_date"),
        CheckConstraint(
            "from_company_id != to_company_id",
            name="ck_inter_company_different"
        ),
    )
    
    # Transaction Reference
    transaction_number: str = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Unique transaction number"
    )
    
    transaction_date: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="Transaction date"
    )
    
    transaction_type: str = Column(
        String(50),
        nullable=False,
        doc="Type: sale, purchase, transfer, payment, etc."
    )
    
    # Companies involved
    from_company_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        doc="Company sending goods/money"
    )
    
    to_company_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        doc="Company receiving goods/money"
    )
    
    # Amounts
    amount: float = Column(
        Numeric(18, 2),
        nullable=False,
        doc="Transaction amount"
    )
    
    currency_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("currencies.id", ondelete="SET NULL"),
        nullable=True,
        doc="Transaction currency"
    )
    
    # Related Documents
    source_document_type: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Source document type (sale_order, invoice, etc.)"
    )
    
    source_document_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Source document ID"
    )
    
    source_document_number: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Source document number for display"
    )
    
    # Accounting References
    from_journal_entry_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
        doc="Journal entry in from company"
    )
    
    to_journal_entry_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
        doc="Journal entry in to company"
    )
    
    # Elimination Entry (for consolidated reporting)
    elimination_entry_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Elimination journal entry ID for consolidation"
    )
    
    # Status & Description
    status: InterCompanyTransactionStatus = Column(
        SQLEnum(InterCompanyTransactionStatus),
        default=InterCompanyTransactionStatus.DRAFT,
        nullable=False,
        doc="Transaction status"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Transaction description"
    )
    
    notes: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Internal notes"
    )
    
    # Relationships
    from_company: Mapped["Company"] = relationship(
        "Company",
        foreign_keys=[from_company_id],
        back_populates="inter_company_transactions_from"
    )
    
    to_company: Mapped["Company"] = relationship(
        "Company",
        foreign_keys=[to_company_id],
        back_populates="inter_company_transactions_to"
    )
    
    # Items for detailed breakdown
    items: Mapped[List["InterCompanyTransactionItem"]] = relationship(
        "InterCompanyTransactionItem",
        back_populates="transaction",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class InterCompanyTransactionItem(BaseModel):
    """
    Inter-Company Transaction Line Item
    """
    
    __tablename__ = "inter_company_transaction_items"
    __table_args__ = (
        Index("ix_inter_company_items_transaction", "transaction_id"),
    )
    
    transaction_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("inter_company_transactions.id", ondelete="CASCADE"),
        nullable=False
    )
    
    product_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        doc="Product being transferred"
    )
    
    description: str = Column(
        String(500),
        nullable=False,
        doc="Line item description"
    )
    
    quantity: float = Column(
        Numeric(18, 4),
        default=1,
        nullable=False,
        doc="Quantity"
    )
    
    unit_price: float = Column(
        Numeric(18, 2),
        default=0,
        nullable=False,
        doc="Unit price"
    )
    
    subtotal: float = Column(
        Numeric(18, 2),
        nullable=False,
        doc="Line subtotal"
    )
    
    account_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        doc="Account for this line item"
    )
    
    # Relationships
    transaction: Mapped["InterCompanyTransaction"] = relationship(
        "InterCompanyTransaction",
        back_populates="items"
    )


class ConsolidationGroup(BaseModel, TenantMixin):
    """
    Consolidation Group Model
    
    Groups companies for consolidated financial reporting.
    """
    
    __tablename__ = "consolidation_groups"
    __table_args__ = (
        Index("ix_consolidation_groups_tenant", "tenant_id"),
    )
    
    name: str = Column(
        String(200),
        nullable=False,
        doc="Consolidation group name"
    )
    
    code: str = Column(
        String(20),
        nullable=False,
        doc="Group code"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Group description"
    )
    
    is_active: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether group is active"
    )
    
    # Consolidation Settings
    consolidation_method: str = Column(
        String(50),
        default="full",
        doc="Consolidation method (full, equity, proportional)"
    )
    
    ownership_percentage: float = Column(
        Numeric(5, 2),
        default=100.00,
        doc="Ownership percentage for proportional consolidation"
    )
    
    # Companies in this group
    companies: Mapped[List["ConsolidationGroupCompany"]] = relationship(
        "ConsolidationGroupCompany",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class ConsolidationGroupCompany(BaseModel):
    """
    Association between Consolidation Group and Company
    """
    
    __tablename__ = "consolidation_group_companies"
    __table_args__ = (
        UniqueConstraint("group_id", "company_id", name="uq_group_company"),
    )
    
    group_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("consolidation_groups.id", ondelete="CASCADE"),
        nullable=False
    )
    
    company_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )
    
    ownership_percentage: float = Column(
        Numeric(5, 2),
        default=100.00,
        doc="Ownership percentage for this company"
    )
    
    consolidation_method: str = Column(
        String(50),
        default="full",
        doc="Consolidation method for this company"
    )
    
    include_in_consolidation: bool = Column(
        Boolean,
        default=True,
        doc="Whether to include in consolidation"
    )
    
    # Relationships
    group: Mapped["ConsolidationGroup"] = relationship(
        "ConsolidationGroup",
        back_populates="companies"
    )
    
    company: Mapped["Company"] = relationship(
        "Company"
    )
