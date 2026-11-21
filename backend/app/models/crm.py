"""
Nexus ERP - CRM Models (Customer, Lead, Opportunity)
=====================================================

This module implements the Customer Relationship Management (CRM) module
with comprehensive customer lifecycle management.

Features:
- Customer management with full profile
- Lead tracking and qualification
- Sales opportunity pipeline
- Contact management
- Customer interaction history
- Customer segmentation
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
    Integer,
    Enum as SQLEnum,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, List
import enum
import uuid
import decimal

from app.models.base import BaseModel, TenantMixin


class CustomerType(str, enum.Enum):
    """Customer type enumeration."""
    INDIVIDUAL = "individual"
    COMPANY = "company"
    GOVERNMENT = "government"
    PARTNER = "partner"


class CustomerStatus(str, enum.Enum):
    """Customer status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROSPECT = "prospect"
    BLACKLISTED = "blacklisted"
    SUSPENDED = "suspended"


class LeadStatus(str, enum.Enum):
    """Lead status enumeration."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    CONVERTED = "converted"
    LOST = "lost"


class LeadSource(str, enum.Enum):
    """Lead source enumeration."""
    WEBSITE = "website"
    REFERRAL = "referral"
    SOCIAL_MEDIA = "social_media"
    EMAIL_CAMPAIGN = "email_campaign"
    TRADE_SHOW = "trade_show"
    COLD_CALL = "cold_call"
    ADVERTISEMENT = "advertisement"
    OTHER = "other"


class OpportunityStage(str, enum.Enum):
    """Sales opportunity stage enumeration."""
    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSING = "closing"
    WON = "won"
    LOST = "lost"


class Customer(BaseModel, TenantMixin):
    """
    Customer Model
    
    Represents a customer (individual or company) with comprehensive
    profile information, contact details, and business relationships.
    """
    
    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_code_tenant", "code", "tenant_id", unique=True),
        Index("ix_customers_email", "email"),
        Index("ix_customers_phone", "phone"),
        Index("ix_customers_name", "name"),
        Index("ix_customers_status", "status"),
        Index("ix_customers_type", "customer_type"),
        CheckConstraint(
            "credit_limit >= 0",
            name="ck_customers_credit_limit"
        ),
    )
    
    # ========================================
    # Basic Information
    # ========================================
    code: str = Column(
        String(50),
        nullable=False,
        doc="Unique customer code"
    )
    
    name: str = Column(
        String(255),
        nullable=False,
        doc="Customer name (company or individual)"
    )
    
    customer_type: CustomerType = Column(
        SQLEnum(CustomerType),
        default=CustomerType.COMPANY,
        nullable=False,
        doc="Type of customer"
    )
    
    status: CustomerStatus = Column(
        SQLEnum(CustomerStatus),
        default=CustomerStatus.PROSPECT,
        nullable=False,
        doc="Current customer status"
    )
    
    # ========================================
    # Contact Information
    # ========================================
    email: Optional[str] = Column(
        String(255),
        nullable=True,
        index=True,
        doc="Primary email address"
    )
    
    email_secondary: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Secondary email address"
    )
    
    phone: Optional[str] = Column(
        String(20),
        nullable=True,
        index=True,
        doc="Primary phone number"
    )
    
    phone_secondary: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Secondary phone number"
    )
    
    fax: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Fax number"
    )
    
    website: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Website URL"
    )
    
    # ========================================
    # Address Information
    # ========================================
    address_line1: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Street address line 1"
    )
    
    address_line2: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Street address line 2"
    )
    
    city: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="City name"
    )
    
    state: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="State/Province name"
    )
    
    postal_code: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Postal/ZIP code"
    )
    
    country: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Country name"
    )
    
    country_code: Optional[str] = Column(
        String(3),
        nullable=True,
        doc="ISO 3166 country code"
    )
    
    # ========================================
    # Business Information
    # ========================================
    tax_id: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Tax identification number"
    )
    
    registration_number: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Business registration number"
    )
    
    industry_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="SET NULL"),
        nullable=True,
        doc="Industry classification"
    )
    
    company_size: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Company size category"
    )
    
    annual_revenue: Optional[decimal.Decimal] = Column(
        Numeric(18, 2),
        nullable=True,
        doc="Annual revenue"
    )
    
    employees_count: Optional[int] = Column(
        Integer,
        nullable=True,
        doc="Number of employees"
    )
    
    founded_year: Optional[int] = Column(
        Integer,
        nullable=True,
        doc="Year founded"
    )
    
    # ========================================
    # Financial Settings
    # ========================================
    payment_terms_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("payment_terms.id", ondelete="SET NULL"),
        nullable=True,
        doc="Default payment terms"
    )
    
    currency_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("currencies.id", ondelete="SET NULL"),
        nullable=True,
        doc="Default currency"
    )
    
    price_list_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("price_lists.id", ondelete="SET NULL"),
        nullable=True,
        doc="Default price list"
    )
    
    credit_limit: decimal.Decimal = Column(
        Numeric(18, 2),
        default=decimal.Decimal("0"),
        nullable=False,
        doc="Credit limit"
    )
    
    credit_used: decimal.Decimal = Column(
        Numeric(18, 2),
        default=decimal.Decimal("0"),
        nullable=False,
        doc="Current credit utilization"
    )
    
    credit_available: decimal.Decimal = Column(
        Numeric(18, 2),
        default=decimal.Decimal("0"),
        nullable=False,
        doc="Available credit"
    )
    
    # ========================================
    # Account Management
    # ========================================
    parent_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        doc="Parent company for subsidiaries"
    )
    
    sales_rep_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Assigned sales representative"
    )
    
    territory_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("territories.id", ondelete="SET NULL"),
        nullable=True,
        doc="Sales territory"
    )
    
    customer_group_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_groups.id", ondelete="SET NULL"),
        nullable=True,
        doc="Customer group/segment"
    )
    
    # ========================================
    # Additional Information
    # ========================================
    notes: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Internal notes about customer"
    )
    
    tags: List[str] = Column(
        ARRAY(String),
        default=list,
        nullable=False,
        doc="Tags for categorization"
    )
    
    custom_fields: dict = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Custom field values"
    )
    
    # ========================================
    # Statistics (Computed/Updated)
    # ========================================
    total_orders: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total number of orders"
    )
    
    total_revenue: decimal.Decimal = Column(
        Numeric(18, 2),
        default=decimal.Decimal("0"),
        nullable=False,
        doc="Total revenue from customer"
    )
    
    total_paid: decimal.Decimal = Column(
        Numeric(18, 2),
        default=decimal.Decimal("0"),
        nullable=False,
        doc="Total amount paid"
    )
    
    total_due: decimal.Decimal = Column(
        Numeric(18, 2),
        default=decimal.Decimal("0"),
        nullable=False,
        doc="Total outstanding amount"
    )
    
    last_order_date: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date of last order"
    )
    
    last_payment_date: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date of last payment"
    )
    
    lifetime_value: decimal.Decimal = Column(
        Numeric(18, 2),
        default=decimal.Decimal("0"),
        nullable=False,
        doc="Customer lifetime value"
    )
    
    # ========================================
    # Relationships
    # ========================================
    contacts: Mapped[List["Contact"]] = relationship(
        "Contact",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="dynamic",
        doc="Customer contacts"
    )
    
    addresses: Mapped[List["CustomerAddress"]] = relationship(
        "CustomerAddress",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="dynamic",
        doc="Customer addresses"
    )
    
    leads: Mapped[List["Lead"]] = relationship(
        "Lead",
        back_populates="customer",
        lazy="dynamic",
        doc="Leads from this customer"
    )
    
    opportunities: Mapped[List["Opportunity"]] = relationship(
        "Opportunity",
        back_populates="customer",
        lazy="dynamic",
        doc="Sales opportunities"
    )
    
    # Sales documents reference Partner, not Customer, in the current schema.
    # Keep these cross-domain relationships out until the domain FK model is unified.

    interactions: Mapped[List["CustomerInteraction"]] = relationship(
        "CustomerInteraction",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="dynamic",
        doc="Interaction history"
    )
    
    parent: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        remote_side="Customer.id",
        backref="subsidiaries",
        doc="Parent company"
    )
    
    @property
    def primary_contact(self) -> Optional["Contact"]:
        """Get the primary contact for this customer."""
        return self.contacts.filter_by(is_primary=True).first()
    
    @property
    def billing_address(self) -> Optional["CustomerAddress"]:
        """Get the default billing address."""
        return self.addresses.filter_by(is_billing=True, is_default=True).first()
    
    @property
    def shipping_address(self) -> Optional["CustomerAddress"]:
        """Get the default shipping address."""
        return self.addresses.filter_by(is_shipping=True, is_default=True).first()
    
    @property
    def available_credit(self) -> decimal.Decimal:
        """Calculate available credit."""
        return self.credit_limit - self.credit_used
    
    def update_credit(self, amount: decimal.Decimal, is_payment: bool = False):
        """
        Update credit utilization.
        
        Args:
            amount: Amount to add/subtract
            is_payment: True if this is a payment (reduces used credit)
        """
        if is_payment:
            self.credit_used -= amount
        else:
            self.credit_used += amount
        
        self.credit_available = self.credit_limit - self.credit_used


class Contact(BaseModel, TenantMixin):
    """
    Contact Model
    
    Represents a contact person associated with a customer.
    """
    
    __tablename__ = "contacts"
    __table_args__ = (
        Index("ix_contacts_email", "email"),
        Index("ix_contacts_customer", "customer_id"),
    )
    
    customer_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        doc="Associated customer"
    )
    
    first_name: str = Column(
        String(100),
        nullable=False,
        doc="Contact first name"
    )
    
    last_name: str = Column(
        String(100),
        nullable=False,
        doc="Contact last name"
    )
    
    title: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Job title"
    )
    
    department: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Department"
    )
    
    email: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Email address"
    )
    
    phone: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Phone number"
    )
    
    mobile: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Mobile number"
    )
    
    linkedin: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="LinkedIn profile URL"
    )
    
    is_primary: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this is primary contact"
    )
    
    is_active: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether contact is active"
    )
    
    notes: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Notes about contact"
    )
    
    # ========================================
    # Relationships
    # ========================================
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="contacts"
    )
    
    @property
    def full_name(self) -> str:
        """Get contact's full name."""
        return f"{self.first_name} {self.last_name}"


class CustomerAddress(BaseModel, TenantMixin):
    """
    CustomerAddress Model
    
    Represents an address associated with a customer.
    """
    
    __tablename__ = "customer_addresses"
    __table_args__ = (
        Index("ix_customer_addresses_customer", "customer_id"),
    )
    
    customer_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False
    )
    
    name: str = Column(
        String(100),
        nullable=False,
        doc="Address name/label"
    )
    
    address_line1: str = Column(
        String(255),
        nullable=False,
        doc="Street address line 1"
    )
    
    address_line2: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Street address line 2"
    )
    
    city: str = Column(
        String(100),
        nullable=False,
        doc="City"
    )
    
    state: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="State/Province"
    )
    
    postal_code: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Postal code"
    )
    
    country: str = Column(
        String(100),
        nullable=False,
        doc="Country"
    )
    
    country_code: Optional[str] = Column(
        String(3),
        nullable=True,
        doc="Country code"
    )
    
    is_billing: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Can be used for billing"
    )
    
    is_shipping: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Can be used for shipping"
    )
    
    is_default: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Default address"
    )
    
    latitude: Optional[decimal.Decimal] = Column(
        Numeric(10, 8),
        nullable=True,
        doc="Geographic latitude"
    )
    
    longitude: Optional[decimal.Decimal] = Column(
        Numeric(11, 8),
        nullable=True,
        doc="Geographic longitude"
    )
    
    # ========================================
    # Relationships
    # ========================================
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="addresses"
    )


class Lead(BaseModel, TenantMixin):
    """
    Lead Model
    
    Represents a potential customer in the sales pipeline.
    """
    
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_status", "status"),
        Index("ix_leads_source", "source"),
    )
    
    # ========================================
    # Basic Information
    # ========================================
    name: str = Column(
        String(255),
        nullable=False,
        doc="Lead name (person or company)"
    )
    
    company: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Company name if B2B"
    )
    
    customer_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        doc="Converted to customer"
    )
    
    # ========================================
    # Contact Information
    # ========================================
    email: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Email address"
    )
    
    phone: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Phone number"
    )
    
    mobile: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Mobile number"
    )
    
    website: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Website URL"
    )
    
    # ========================================
    # Address
    # ========================================
    address: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Full address"
    )
    
    city: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="City"
    )
    
    country: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Country"
    )
    
    # ========================================
    # Lead Details
    # ========================================
    status: LeadStatus = Column(
        SQLEnum(LeadStatus),
        default=LeadStatus.NEW,
        nullable=False,
        doc="Current lead status"
    )
    
    source: Optional[LeadSource] = Column(
        SQLEnum(LeadSource),
        nullable=True,
        doc="Lead source"
    )
    
    title: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Lead title/subject"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Lead description"
    )
    
    # ========================================
    # Assignment
    # ========================================
    owner_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Assigned sales rep"
    )
    
    team_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        doc="Assigned team"
    )
    
    # ========================================
    # Scoring
    # ========================================
    score: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Lead quality score"
    )
    
    rating: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Lead rating (hot, warm, cold)"
    )
    
    estimated_value: Optional[decimal.Decimal] = Column(
        Numeric(18, 2),
        nullable=True,
        doc="Estimated deal value"
    )
    
    probability: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Probability of conversion (0-100)"
    )
    
    # ========================================
    # Dates
    # ========================================
    contacted_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When lead was first contacted"
    )
    
    qualified_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When lead was qualified"
    )
    
    converted_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When lead was converted"
    )
    
    next_follow_up: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Next follow-up date"
    )
    
    # ========================================
    # Additional
    # ========================================
    notes: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Notes"
    )
    
    tags: List[str] = Column(
        ARRAY(String),
        default=list,
        nullable=False,
        doc="Tags"
    )
    
    custom_fields: dict = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Custom fields"
    )
    
    # ========================================
    # Relationships
    # ========================================
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        back_populates="leads"
    )
    
    opportunities: Mapped[List["Opportunity"]] = relationship(
        "Opportunity",
        back_populates="lead",
        lazy="dynamic"
    )


class Opportunity(BaseModel, TenantMixin):
    """
    Opportunity Model
    
    Represents a sales opportunity in the pipeline.
    """
    
    __tablename__ = "opportunities"
    __table_args__ = (
        Index("ix_opportunities_stage", "stage"),
        Index("ix_opportunities_customer", "customer_id"),
        Index("ix_opportunities_owner", "owner_id"),
        Index("ix_opportunities_expected_close", "expected_close_date"),
    )
    
    # ========================================
    # Basic Information
    # ========================================
    name: str = Column(
        String(255),
        nullable=False,
        doc="Opportunity name"
    )
    
    number: str = Column(
        String(50),
        nullable=False,
        doc="Opportunity number"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Description"
    )
    
    # ========================================
    # Relations
    # ========================================
    customer_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        doc="Associated customer"
    )
    
    lead_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        doc="Source lead"
    )
    
    contact_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        doc="Primary contact"
    )
    
    # ========================================
    # Pipeline
    # ========================================
    stage: OpportunityStage = Column(
        SQLEnum(OpportunityStage),
        default=OpportunityStage.PROSPECTING,
        nullable=False,
        doc="Current stage"
    )
    
    probability: int = Column(
        Integer,
        default=10,
        nullable=False,
        doc="Win probability (0-100)"
    )
    
    # ========================================
    # Financial
    # ========================================
    amount: decimal.Decimal = Column(
        Numeric(18, 2),
        default=decimal.Decimal("0"),
        nullable=False,
        doc="Opportunity amount"
    )
    
    currency_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("currencies.id", ondelete="SET NULL"),
        nullable=True,
        doc="Currency"
    )
    
    weighted_amount: decimal.Decimal = Column(
        Numeric(18, 2),
        default=decimal.Decimal("0"),
        nullable=False,
        doc="Amount × Probability"
    )
    
    expected_revenue: decimal.Decimal = Column(
        Numeric(18, 2),
        default=decimal.Decimal("0"),
        nullable=False,
        doc="Expected revenue"
    )
    
    cost_estimate: Optional[decimal.Decimal] = Column(
        Numeric(18, 2),
        nullable=True,
        doc="Estimated cost"
    )
    
    margin: Optional[decimal.Decimal] = Column(
        Numeric(5, 2),
        nullable=True,
        doc="Expected margin %"
    )
    
    # ========================================
    # Assignment
    # ========================================
    owner_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Opportunity owner"
    )
    
    team_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        doc="Sales team"
    )
    
    # ========================================
    # Dates
    # ========================================
    expected_close_date: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Expected close date"
    )
    
    actual_close_date: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Actual close date"
    )
    
    # ========================================
    # Close Details
    # ========================================
    close_reason: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Reason for won/lost"
    )
    
    competitors: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Competitors involved"
    )
    
    # ========================================
    # Additional
    # ========================================
    next_step: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Next step description"
    )
    
    next_step_date: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Next step date"
    )
    
    notes: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Notes"
    )
    
    tags: List[str] = Column(
        ARRAY(String),
        default=list,
        nullable=False,
        doc="Tags"
    )
    
    custom_fields: dict = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Custom fields"
    )
    
    # ========================================
    # Relationships
    # ========================================
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="opportunities"
    )
    
    lead: Mapped[Optional["Lead"]] = relationship(
        "Lead",
        back_populates="opportunities"
    )


class CustomerInteraction(BaseModel, TenantMixin):
    """
    CustomerInteraction Model
    
    Records all interactions with customers.
    """
    
    __tablename__ = "customer_interactions"
    __table_args__ = (
        Index("ix_customer_interactions_customer", "customer_id"),
        Index("ix_customer_interactions_date", "interaction_date"),
    )
    
    customer_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False
    )
    
    contact_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True
    )
    
    type: str = Column(
        String(50),
        nullable=False,
        doc="Interaction type (call, email, meeting, etc.)"
    )
    
    subject: str = Column(
        String(255),
        nullable=False,
        doc="Interaction subject"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Interaction details"
    )
    
    direction: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Direction (inbound, outbound)"
    )
    
    duration_minutes: Optional[int] = Column(
        Integer,
        nullable=True,
        doc="Duration in minutes"
    )
    
    interaction_date: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="When interaction occurred"
    )
    
    user_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who logged interaction"
    )
    
    opportunity_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
        doc="Related opportunity"
    )
    
    outcome: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Interaction outcome"
    )
    
    follow_up_required: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether follow-up is required"
    )
    
    follow_up_date: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Follow-up date"
    )
    
    # ========================================
    # Relationships
    # ========================================
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="interactions"
    )


# Forward references for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.sales import Quote, SalesOrder, Invoice
    from app.models.inventory import Product
