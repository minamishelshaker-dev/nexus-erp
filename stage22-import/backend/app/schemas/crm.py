"""
Nexus ERP - Pydantic Schemas for CRM Module
===========================================

This module defines Pydantic schemas for Customer, Lead, and Opportunity
management within the CRM module.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
)
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
            Decimal: lambda v: float(v) if v else None
        }
    )


# ========================================
# Contact Schemas
# ========================================

class ContactBase(BaseModel):
    """Base contact schema."""
    first_name: str = Field(..., max_length=100, description="Contact first name")
    last_name: str = Field(..., max_length=100, description="Contact last name")
    title: Optional[str] = Field(None, max_length=100, description="Job title")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    mobile: Optional[str] = Field(None, max_length=20, description="Mobile number")
    linkedin: Optional[str] = Field(None, max_length=255, description="LinkedIn URL")
    is_primary: bool = Field(default=False, description="Is primary contact")
    notes: Optional[str] = Field(None, description="Notes")


class ContactCreate(ContactBase):
    """Schema for creating a contact."""
    customer_id: UUID = Field(..., description="Associated customer ID")


class ContactUpdate(BaseModel):
    """Schema for updating a contact."""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    mobile: Optional[str] = Field(None, max_length=20)
    linkedin: Optional[str] = Field(None, max_length=255)
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class ContactResponse(BaseSchema):
    """Schema for contact response."""
    id: UUID
    customer_id: UUID
    first_name: str
    last_name: str
    full_name: str
    title: Optional[str] = None
    department: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    linkedin: Optional[str] = None
    is_primary: bool = False
    is_active: bool = True
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ========================================
# Address Schemas
# ========================================

class AddressBase(BaseModel):
    """Base address schema."""
    name: str = Field(..., max_length=100, description="Address name/label")
    address_line1: str = Field(..., max_length=255, description="Address line 1")
    address_line2: Optional[str] = Field(None, max_length=255, description="Address line 2")
    city: str = Field(..., max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=100, description="State/Province")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal code")
    country: str = Field(..., max_length=100, description="Country")
    country_code: Optional[str] = Field(None, max_length=3, description="Country code")
    is_billing: bool = Field(default=True, description="Can be used for billing")
    is_shipping: bool = Field(default=True, description="Can be used for shipping")
    is_default: bool = Field(default=False, description="Is default address")


class AddressCreate(AddressBase):
    """Schema for creating an address."""
    customer_id: UUID = Field(..., description="Associated customer ID")


class AddressUpdate(BaseModel):
    """Schema for updating an address."""
    name: Optional[str] = Field(None, max_length=100)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    country_code: Optional[str] = Field(None, max_length=3)
    is_billing: Optional[bool] = None
    is_shipping: Optional[bool] = None
    is_default: Optional[bool] = None


class AddressResponse(BaseSchema):
    """Schema for address response."""
    id: UUID
    customer_id: UUID
    name: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str
    country_code: Optional[str] = None
    is_billing: bool = True
    is_shipping: bool = True
    is_default: bool = False
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime


# ========================================
# Customer Schemas
# ========================================

class CustomerBriefResponse(BaseSchema):
    """Brief customer information for nested responses."""
    id: UUID
    code: str
    name: str
    customer_type: str
    status: str
    email: Optional[str] = None
    phone: Optional[str] = None


class CustomerBase(BaseModel):
    """Base customer schema."""
    code: Optional[str] = Field(None, max_length=50, description="Customer code (auto-generated if not provided)")
    name: str = Field(..., max_length=255, description="Customer name")
    customer_type: str = Field(default="company", description="Customer type")
    
    # Contact Information
    email: Optional[EmailStr] = Field(None, description="Primary email")
    email_secondary: Optional[EmailStr] = Field(None, description="Secondary email")
    phone: Optional[str] = Field(None, max_length=20, description="Primary phone")
    phone_secondary: Optional[str] = Field(None, max_length=20, description="Secondary phone")
    fax: Optional[str] = Field(None, max_length=20, description="Fax")
    website: Optional[str] = Field(None, max_length=255, description="Website URL")
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    country_code: Optional[str] = Field(None, max_length=3)
    
    # Business Information
    tax_id: Optional[str] = Field(None, max_length=50, description="Tax ID")
    registration_number: Optional[str] = Field(None, max_length=50, description="Registration number")
    industry_id: Optional[UUID] = Field(None, description="Industry ID")
    company_size: Optional[str] = Field(None, max_length=50)
    annual_revenue: Optional[Decimal] = Field(None, ge=0)
    employees_count: Optional[int] = Field(None, ge=0)
    
    # Financial Settings
    payment_terms_id: Optional[UUID] = Field(None, description="Payment terms ID")
    currency_id: Optional[UUID] = Field(None, description="Currency ID")
    price_list_id: Optional[UUID] = Field(None, description="Price list ID")
    credit_limit: Decimal = Field(default=Decimal("0"), ge=0, description="Credit limit")
    
    # Assignment
    parent_id: Optional[UUID] = Field(None, description="Parent customer ID")
    sales_rep_id: Optional[UUID] = Field(None, description="Sales representative ID")
    territory_id: Optional[UUID] = Field(None, description="Territory ID")
    customer_group_id: Optional[UUID] = Field(None, description="Customer group ID")
    
    # Additional
    notes: Optional[str] = Field(None, description="Notes")
    tags: List[str] = Field(default_factory=list, description="Tags")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Custom fields")
    
    @field_validator('customer_type')
    @classmethod
    def validate_customer_type(cls, v: str) -> str:
        allowed = ['individual', 'company', 'government', 'partner']
        if v.lower() not in allowed:
            raise ValueError(f'Customer type must be one of: {allowed}')
        return v.lower()


class CustomerCreate(CustomerBase):
    """Schema for creating a customer."""
    contacts: List[ContactCreate] = Field(
        default_factory=list,
        description="Initial contacts to create"
    )
    addresses: List[AddressCreate] = Field(
        default_factory=list,
        description="Initial addresses to create"
    )
    
    @model_validator(mode='after')
    def validate_contacts_addresses(self):
        # Ensure contacts and addresses reference the same customer
        for contact in self.contacts:
            contact.customer_id = UUID('00000000-0000-0000-0000-000000000000')  # Placeholder
        return self


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""
    name: Optional[str] = Field(None, max_length=255)
    customer_type: Optional[str] = None
    status: Optional[str] = None
    
    # Contact Information
    email: Optional[EmailStr] = None
    email_secondary: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    phone_secondary: Optional[str] = Field(None, max_length=20)
    fax: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    country_code: Optional[str] = Field(None, max_length=3)
    
    # Business Information
    tax_id: Optional[str] = Field(None, max_length=50)
    registration_number: Optional[str] = Field(None, max_length=50)
    industry_id: Optional[UUID] = None
    company_size: Optional[str] = Field(None, max_length=50)
    annual_revenue: Optional[Decimal] = Field(None, ge=0)
    employees_count: Optional[int] = Field(None, ge=0)
    
    # Financial Settings
    payment_terms_id: Optional[UUID] = None
    currency_id: Optional[UUID] = None
    price_list_id: Optional[UUID] = None
    credit_limit: Optional[Decimal] = Field(None, ge=0)
    
    # Assignment
    parent_id: Optional[UUID] = None
    sales_rep_id: Optional[UUID] = None
    territory_id: Optional[UUID] = None
    customer_group_id: Optional[UUID] = None
    
    # Additional
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None


class CustomerResponse(CustomerBriefResponse):
    """Full customer response schema."""
    email_secondary: Optional[str] = None
    phone_secondary: Optional[str] = None
    fax: Optional[str] = None
    website: Optional[str] = None
    
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    
    tax_id: Optional[str] = None
    registration_number: Optional[str] = None
    industry_id: Optional[UUID] = None
    company_size: Optional[str] = None
    annual_revenue: Optional[Decimal] = None
    employees_count: Optional[int] = None
    founded_year: Optional[int] = None
    
    payment_terms_id: Optional[UUID] = None
    currency_id: Optional[UUID] = None
    price_list_id: Optional[UUID] = None
    credit_limit: Decimal = Decimal("0")
    credit_used: Decimal = Decimal("0")
    credit_available: Decimal = Decimal("0")
    
    parent_id: Optional[UUID] = None
    sales_rep_id: Optional[UUID] = None
    territory_id: Optional[UUID] = None
    customer_group_id: Optional[UUID] = None
    
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    # Statistics
    total_orders: int = 0
    total_revenue: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")
    total_due: Decimal = Decimal("0")
    last_order_date: Optional[datetime] = None
    last_payment_date: Optional[datetime] = None
    lifetime_value: Decimal = Decimal("0")
    
    created_at: datetime
    updated_at: datetime
    
    # Nested
    contacts: List[ContactResponse] = Field(default_factory=list)
    addresses: List[AddressResponse] = Field(default_factory=list)


class CustomerListResponse(BaseModel):
    """Schema for paginated customer list."""
    items: List[CustomerResponse]
    total: int
    page: int
    page_size: int
    pages: int


class CustomerSearchParams(BaseModel):
    """Schema for customer search parameters."""
    query: Optional[str] = Field(None, description="Search query")
    customer_type: Optional[str] = None
    status: Optional[str] = None
    industry_id: Optional[UUID] = None
    sales_rep_id: Optional[UUID] = None
    territory_id: Optional[UUID] = None
    customer_group_id: Optional[UUID] = None
    city: Optional[str] = None
    country: Optional[str] = None
    tags: Optional[List[str]] = None
    has_credit: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    last_order_after: Optional[datetime] = None
    last_order_before: Optional[datetime] = None


# ========================================
# Lead Schemas
# ========================================

class LeadBriefResponse(BaseSchema):
    """Brief lead information."""
    id: UUID
    name: str
    company: Optional[str] = None
    status: str
    email: Optional[str] = None
    phone: Optional[str] = None


class LeadBase(BaseModel):
    """Base lead schema."""
    name: str = Field(..., max_length=255, description="Lead name")
    company: Optional[str] = Field(None, max_length=255, description="Company name")
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    mobile: Optional[str] = Field(None, max_length=20, description="Mobile number")
    website: Optional[str] = Field(None, max_length=255, description="Website")
    address: Optional[str] = Field(None, description="Full address")
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    source: Optional[str] = Field(None, description="Lead source")
    title: Optional[str] = Field(None, max_length=100, description="Lead title")
    description: Optional[str] = Field(None, description="Description")
    owner_id: Optional[UUID] = Field(None, description="Assigned owner ID")
    team_id: Optional[UUID] = Field(None, description="Assigned team ID")
    estimated_value: Optional[Decimal] = Field(None, ge=0)
    probability: int = Field(default=0, ge=0, le=100)
    next_follow_up: Optional[datetime] = Field(None, description="Next follow-up date")
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class LeadCreate(LeadBase):
    """Schema for creating a lead."""
    pass


class LeadUpdate(BaseModel):
    """Schema for updating a lead."""
    name: Optional[str] = Field(None, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    mobile: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None
    source: Optional[str] = None
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    owner_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    estimated_value: Optional[Decimal] = Field(None, ge=0)
    probability: Optional[int] = Field(None, ge=0, le=100)
    next_follow_up: Optional[datetime] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class LeadResponse(LeadBriefResponse):
    """Full lead response schema."""
    mobile: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    source: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    owner_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    
    score: int = 0
    rating: Optional[str] = None
    estimated_value: Optional[Decimal] = None
    probability: int = 0
    
    customer_id: Optional[UUID] = None
    contacted_at: Optional[datetime] = None
    qualified_at: Optional[datetime] = None
    converted_at: Optional[datetime] = None
    next_follow_up: Optional[datetime] = None
    
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    created_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    """Schema for lead list."""
    items: List[LeadResponse]
    total: int
    page: int
    page_size: int
    pages: int


class LeadConvertRequest(BaseModel):
    """Schema for converting lead to customer."""
    create_customer: bool = Field(default=True, description="Create new customer")
    customer_id: Optional[UUID] = Field(None, description="Existing customer ID")
    create_opportunity: bool = Field(default=True, description="Create opportunity")
    opportunity_name: Optional[str] = Field(None, description="Opportunity name")
    opportunity_amount: Optional[Decimal] = Field(None, ge=0)


# ========================================
# Opportunity Schemas
# ========================================

class OpportunityBriefResponse(BaseSchema):
    """Brief opportunity information."""
    id: UUID
    name: str
    number: str
    stage: str
    amount: Decimal
    probability: int
    expected_close_date: Optional[datetime] = None


class OpportunityBase(BaseModel):
    """Base opportunity schema."""
    name: str = Field(..., max_length=255, description="Opportunity name")
    description: Optional[str] = Field(None, description="Description")
    customer_id: UUID = Field(..., description="Customer ID")
    lead_id: Optional[UUID] = Field(None, description="Source lead ID")
    contact_id: Optional[UUID] = Field(None, description="Primary contact ID")
    amount: Decimal = Field(default=Decimal("0"), ge=0, description="Opportunity amount")
    currency_id: Optional[UUID] = Field(None, description="Currency ID")
    probability: int = Field(default=10, ge=0, le=100, description="Win probability")
    expected_close_date: Optional[datetime] = Field(None, description="Expected close date")
    owner_id: UUID = Field(..., description="Owner ID")
    team_id: Optional[UUID] = Field(None, description="Team ID")
    next_step: Optional[str] = Field(None, max_length=255, description="Next step")
    next_step_date: Optional[datetime] = Field(None, description="Next step date")
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class OpportunityCreate(OpportunityBase):
    """Schema for creating an opportunity."""
    pass


class OpportunityUpdate(BaseModel):
    """Schema for updating an opportunity."""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    customer_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    stage: Optional[str] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    currency_id: Optional[UUID] = None
    probability: Optional[int] = Field(None, ge=0, le=100)
    expected_close_date: Optional[datetime] = None
    owner_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    next_step: Optional[str] = Field(None, max_length=255)
    next_step_date: Optional[datetime] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class OpportunityResponse(OpportunityBriefResponse):
    """Full opportunity response schema."""
    description: Optional[str] = None
    customer_id: UUID
    lead_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    
    currency_id: Optional[UUID] = None
    weighted_amount: Decimal = Decimal("0")
    expected_revenue: Decimal = Decimal("0")
    cost_estimate: Optional[Decimal] = None
    margin: Optional[Decimal] = None
    
    owner_id: UUID
    team_id: Optional[UUID] = None
    
    actual_close_date: Optional[datetime] = None
    close_reason: Optional[str] = None
    competitors: Optional[str] = None
    
    next_step: Optional[str] = None
    next_step_date: Optional[datetime] = None
    
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    created_at: datetime
    updated_at: datetime
    
    # Nested
    customer: Optional[CustomerBriefResponse] = None


class OpportunityListResponse(BaseModel):
    """Schema for opportunity list."""
    items: List[OpportunityResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PipelineStageSummary(BaseModel):
    """Schema for pipeline stage summary."""
    stage: str
    count: int
    total_amount: Decimal
    weighted_amount: Decimal


class PipelineSummary(BaseModel):
    """Schema for sales pipeline summary."""
    total_opportunities: int
    total_amount: Decimal
    weighted_amount: Decimal
    by_stage: List[PipelineStageSummary]


# ========================================
# Interaction Schemas
# ========================================

class InteractionCreate(BaseModel):
    """Schema for creating a customer interaction."""
    customer_id: UUID
    contact_id: Optional[UUID] = None
    type: str = Field(..., max_length=50, description="Interaction type")
    subject: str = Field(..., max_length=255, description="Subject")
    description: Optional[str] = None
    direction: Optional[str] = Field(None, max_length=20)
    duration_minutes: Optional[int] = Field(None, ge=0)
    interaction_date: datetime
    opportunity_id: Optional[UUID] = None
    outcome: Optional[str] = Field(None, max_length=100)
    follow_up_required: bool = False
    follow_up_date: Optional[datetime] = None


class InteractionResponse(BaseSchema):
    """Schema for interaction response."""
    id: UUID
    customer_id: UUID
    contact_id: Optional[UUID] = None
    type: str
    subject: str
    description: Optional[str] = None
    direction: Optional[str] = None
    duration_minutes: Optional[int] = None
    interaction_date: datetime
    user_id: Optional[UUID] = None
    opportunity_id: Optional[UUID] = None
    outcome: Optional[str] = None
    follow_up_required: bool = False
    follow_up_date: Optional[datetime] = None
    created_at: datetime


# Update forward references
CustomerResponse.model_rebuild()
