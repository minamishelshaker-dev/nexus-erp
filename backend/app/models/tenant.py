"""
Nexus ERP - Tenant Model for Multi-Tenancy
===========================================

This module implements the Tenant model for SaaS multi-tenant architecture
with subscription tracking and plan management.

Features:
- Tenant isolation with unique subdomains
- Subscription plan tracking
- Trial period management
- Usage quotas and limits
- Billing status tracking
- Audit logging for all actions
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
    Enum as SQLEnum,
    Integer,
    Numeric,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, List, Dict, Any
import enum
import uuid

from app.models.base import BaseModel


class TenantStatus(str, enum.Enum):
    """Tenant account status enumeration."""
    TRIAL = "trial"              # In trial period
    ACTIVE = "active"            # Active subscription
    PAST_DUE = "past_due"        # Payment failed, grace period
    SUSPENDED = "suspended"      # Subscription suspended
    CANCELLED = "cancelled"      # Subscription cancelled
    CHURNED = "churned"          # Customer left


class PlanType(str, enum.Enum):
    """Subscription plan types."""
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class AuditAction(str, enum.Enum):
    """Audit log action types."""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_RESET = "password_reset"
    PASSWORD_CHANGED = "password_changed"
    
    # CRUD Operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    BULK_CREATE = "bulk_create"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"
    
    # Export/Import
    EXPORT = "export"
    IMPORT = "import"
    
    # System
    SYSTEM_CONFIG = "system_config"
    BACKUP = "backup"
    RESTORE = "restore"
    
    # User Management
    USER_INVITE = "user_invite"
    USER_ACTIVATE = "user_activate"
    USER_DEACTIVATE = "user_deactivate"
    USER_ROLE_CHANGE = "user_role_change"
    
    # Billing
    SUBSCRIPTION_CREATE = "subscription_create"
    SUBSCRIPTION_UPDATE = "subscription_update"
    SUBSCRIPTION_CANCEL = "subscription_cancel"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    
    # Tenant
    TENANT_CREATE = "tenant_create"
    TENANT_UPDATE = "tenant_update"
    TENANT_SUSPEND = "tenant_suspend"
    TENANT_REACTIVATE = "tenant_reactivate"


class Tenant(BaseModel):
    """
    Tenant Model
    
    Represents a tenant (organization/company) in the multi-tenant SaaS system.
    Each tenant has complete data isolation and their own subscription.
    """
    
    __tablename__ = "tenants"
    __table_args__ = (
        Index("ix_tenants_subdomain", "subdomain", unique=True),
        Index("ix_tenants_status", "status"),
        Index("ix_tenants_plan", "plan_type"),
    )
    
    # ========================================
    # Basic Information
    # ========================================
    name: str = Column(
        String(255),
        nullable=False,
        doc="Tenant/Company name"
    )
    
    subdomain: str = Column(
        String(100),
        nullable=False,
        unique=True,
        doc="Unique subdomain for tenant (e.g., acme.nexus-erp.com)"
    )
    
    slug: str = Column(
        String(100),
        nullable=False,
        unique=True,
        doc="URL-safe identifier for tenant"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Tenant description"
    )
    
    logo_url: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="URL to tenant logo"
    )
    
    # ========================================
    # Contact Information
    # ========================================
    contact_email: str = Column(
        String(255),
        nullable=False,
        doc="Primary contact email"
    )
    
    contact_phone: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Primary contact phone"
    )
    
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
    
    state: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="State/Province"
    )
    
    country: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Country"
    )
    
    postal_code: Optional[str] = Column(
        String(20),
        nullable=True,
        doc="Postal/ZIP code"
    )
    
    # ========================================
    # Subscription & Billing
    # ========================================
    status: TenantStatus = Column(
        SQLEnum(TenantStatus),
        default=TenantStatus.TRIAL,
        nullable=False,
        doc="Current tenant status"
    )
    
    plan_type: PlanType = Column(
        SQLEnum(PlanType),
        default=PlanType.BASIC,
        nullable=False,
        doc="Subscription plan type"
    )
    
    stripe_customer_id: Optional[str] = Column(
        String(100),
        nullable=True,
        unique=True,
        doc="Stripe customer ID"
    )
    
    stripe_subscription_id: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Stripe subscription ID"
    )
    
    subscription_start: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When subscription started"
    )
    
    subscription_end: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When current subscription period ends"
    )
    
    trial_start: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When trial period started"
    )
    
    trial_end: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When trial period ends"
    )
    
    # ========================================
    # Usage & Limits
    # ========================================
    max_users: int = Column(
        Integer,
        default=5,
        nullable=False,
        doc="Maximum number of users allowed"
    )
    
    current_users: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Current number of active users"
    )
    
    max_storage_mb: int = Column(
        Integer,
        default=1024,  # 1GB
        nullable=False,
        doc="Maximum storage in MB"
    )
    
    current_storage_mb: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Current storage used in MB"
    )
    
    max_products: int = Column(
        Integer,
        default=100,
        nullable=False,
        doc="Maximum number of products"
    )
    
    current_products: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Current number of products"
    )
    
    max_customers: int = Column(
        Integer,
        default=500,
        nullable=False,
        doc="Maximum number of customers"
    )
    
    current_customers: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Current number of customers"
    )
    
    api_calls_limit: int = Column(
        Integer,
        default=10000,
        nullable=False,
        doc="Monthly API calls limit"
    )
    
    api_calls_used: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="API calls used this month"
    )
    
    # ========================================
    # Features & Settings
    # ========================================
    features: dict = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Enabled features for this tenant"
    )
    
    settings: dict = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Tenant-specific settings"
    )
    
    # ========================================
    # Database Schema (for schema-based isolation)
    # ========================================
    schema_name: Optional[str] = Column(
        String(100),
        nullable=True,
        unique=True,
        doc="Database schema name for this tenant"
    )
    
    # ========================================
    # Status Flags
    # ========================================
    is_active: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether tenant is active"
    )
    
    is_verified: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether tenant email is verified"
    )
    
    onboarding_completed: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether initial onboarding is complete"
    )
    
    # ========================================
    # Timestamps
    # ========================================
    last_activity_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last activity timestamp"
    )
    
    suspended_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When tenant was suspended"
    )
    
    cancelled_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When subscription was cancelled"
    )
    
    # ========================================
    # Relationships
    # ========================================
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="tenant",
        lazy="dynamic",
        doc="Users belonging to this tenant"
    )
    
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription",
        back_populates="tenant",
        uselist=False,
        lazy="selectin",
        doc="Current subscription"
    )
    
    invoices: Mapped[List["BillingInvoice"]] = relationship(
        "BillingInvoice",
        back_populates="tenant",
        lazy="dynamic",
        doc="Billing invoices"
    )
    
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="tenant",
        lazy="dynamic",
        doc="Audit logs for this tenant"
    )
    
    @property
    def is_trial(self) -> bool:
        """Check if tenant is in trial period."""
        return self.status == TenantStatus.TRIAL
    
    @property
    def is_subscription_active(self) -> bool:
        """Check if subscription is active."""
        return self.status in [TenantStatus.TRIAL, TenantStatus.ACTIVE]
    
    @property
    def trial_days_remaining(self) -> int:
        """Get remaining trial days."""
        if not self.trial_end:
            return 0
        delta = self.trial_end - datetime.utcnow()
        return max(0, delta.days)
    
    @property
    def users_available(self) -> int:
        """Get number of available user slots."""
        return max(0, self.max_users - self.current_users)
    
    @property
    def storage_available_mb(self) -> int:
        """Get available storage in MB."""
        return max(0, self.max_storage_mb - self.current_storage_mb)
    
    def can_add_user(self) -> bool:
        """Check if tenant can add more users."""
        return self.current_users < self.max_users
    
    def can_add_product(self) -> bool:
        """Check if tenant can add more products."""
        return self.current_products < self.max_products
    
    def can_add_customer(self) -> bool:
        """Check if tenant can add more products."""
        return self.current_products < self.max_products
    
    def can_add_customer(self) -> bool:
        """Check if tenant can add more customers."""
        return self.current_customers < self.max_customers
    
    def has_feature(self, feature_name: str) -> bool:
        """Check if tenant has access to a specific feature."""
        return self.features.get(feature_name, False)
    
    def get_plan_limits(self) -> dict:
        """Get limits based on current plan."""
        limits = {
            PlanType.BASIC: {
                "max_users": 5,
                "max_storage_mb": 1024,  # 1GB
                "max_products": 100,
                "max_customers": 500,
                "api_calls_limit": 10000,
                "features": {
                    "inventory": True,
                    "sales": True,
                    "purchase": True,
                    "accounting": True,
                    "crm": True,
                    "manufacturing": False,
                    "ai_features": False,
                    "api_access": False,
                    "custom_reports": False,
                    "multi_warehouse": False,
                }
            },
            PlanType.PRO: {
                "max_users": 25,
                "max_storage_mb": 10240,  # 10GB
                "max_products": 1000,
                "max_customers": 5000,
                "api_calls_limit": 100000,
                "features": {
                    "inventory": True,
                    "sales": True,
                    "purchase": True,
                    "accounting": True,
                    "crm": True,
                    "manufacturing": True,
                    "ai_features": True,
                    "api_access": True,
                    "custom_reports": True,
                    "multi_warehouse": True,
                }
            },
            PlanType.ENTERPRISE: {
                "max_users": -1,  # Unlimited
                "max_storage_mb": -1,  # Unlimited
                "max_products": -1,  # Unlimited
                "max_customers": -1,  # Unlimited
                "api_calls_limit": -1,  # Unlimited
                "features": {
                    "inventory": True,
                    "sales": True,
                    "purchase": True,
                    "accounting": True,
                    "crm": True,
                    "manufacturing": True,
                    "ai_features": True,
                    "api_access": True,
                    "custom_reports": True,
                    "multi_warehouse": True,
                    "white_label": True,
                    "dedicated_support": True,
                    "custom_integrations": True,
                    "sla": True,
                }
            }
        }
        return limits.get(self.plan_type, limits[PlanType.BASIC])
    
    def apply_plan_limits(self):
        """Apply plan limits to tenant."""
        limits = self.get_plan_limits()
        self.max_users = limits["max_users"]
        self.max_storage_mb = limits["max_storage_mb"]
        self.max_products = limits["max_products"]
        self.max_customers = limits["max_customers"]
        self.api_calls_limit = limits["api_calls_limit"]
        self.features = limits["features"]


class Subscription(BaseModel):
    """
    Subscription Model
    
    Tracks subscription details and billing history.
    """
    
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_tenant", "tenant_id"),
        Index("ix_subscriptions_status", "status"),
        Index("ix_subscriptions_stripe", "stripe_subscription_id"),
    )
    
    tenant_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to tenant"
    )
    
    plan_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reference to plan"
    )
    
    status: str = Column(
        String(50),
        nullable=False,
        default="active",
        doc="Subscription status (active, past_due, cancelled, etc.)"
    )
    
    stripe_subscription_id: Optional[str] = Column(
        String(100),
        nullable=True,
        unique=True,
        doc="Stripe subscription ID"
    )
    
    stripe_price_id: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Stripe price ID"
    )
    
    current_period_start: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Start of current billing period"
    )
    
    current_period_end: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="End of current billing period"
    )
    
    cancel_at_period_end: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether subscription will cancel at period end"
    )
    
    cancelled_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When subscription was cancelled"
    )
    
    # Pricing
    quantity: int = Column(
        Integer,
        default=1,
        nullable=False,
        doc="Number of seats/units"
    )
    
    unit_price: float = Column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=0,
        doc="Price per unit"
    )
    
    # Trial
    trial_start: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Trial period start"
    )
    
    trial_end: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Trial period end"
    )
    
    # Discount
    coupon_id: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Applied coupon ID"
    )
    
    discount_percent: Optional[int] = Column(
        Integer,
        nullable=True,
        doc="Discount percentage"
    )
    
    # Metadata
    metadata_json: dict = Column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
        doc="Additional subscription metadata"
    )
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="subscription"
    )
    
    plan: Mapped[Optional["Plan"]] = relationship(
        "Plan",
        back_populates="subscriptions"
    )
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status in ["active", "trialing"]
    
    @property
    def is_trialing(self) -> bool:
        """Check if subscription is in trial."""
        return self.status == "trialing"
    
    @property
    def monthly_amount(self) -> float:
        """Calculate monthly subscription amount."""
        return self.quantity * float(self.unit_price)


class Plan(BaseModel):
    """
    Plan Model
    
    Defines available subscription plans.
    """
    
    __tablename__ = "plans"
    __table_args__ = (
        Index("ix_plans_code", "code", unique=True),
    )
    
    code: str = Column(
        String(50),
        nullable=False,
        unique=True,
        doc="Unique plan code (e.g., 'basic', 'pro', 'enterprise')"
    )
    
    name: str = Column(
        String(100),
        nullable=False,
        doc="Plan display name"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Plan description"
    )
    
    plan_type: PlanType = Column(
        SQLEnum(PlanType),
        nullable=False,
        doc="Plan type classification"
    )
    
    is_active: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether plan is available for signup"
    )
    
    is_public: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether plan is publicly visible"
    )
    
    # Pricing
    monthly_price: float = Column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=0,
        doc="Monthly price"
    )
    
    yearly_price: float = Column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=0,
        doc="Yearly price (discounted)"
    )
    
    stripe_price_id_monthly: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Stripe price ID for monthly billing"
    )
    
    stripe_price_id_yearly: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Stripe price ID for yearly billing"
    )
    
    # Limits
    max_users: int = Column(
        Integer,
        default=5,
        nullable=False,
        doc="Maximum users included"
    )
    
    max_storage_mb: int = Column(
        Integer,
        default=1024,
        nullable=False,
        doc="Maximum storage in MB"
    )
    
    max_products: int = Column(
        Integer,
        default=100,
        nullable=False,
        doc="Maximum products"
    )
    
    max_customers: int = Column(
        Integer,
        default=500,
        nullable=False,
        doc="Maximum customers"
    )
    
    # Trial
    trial_days: int = Column(
        Integer,
        default=14,
        nullable=False,
        doc="Trial period length in days"
    )
    
    # Features
    features: dict = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Feature flags for this plan"
    )
    
    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription",
        back_populates="plan"
    )
    
    @property
    def yearly_discount_percent(self) -> int:
        """Calculate yearly discount percentage."""
        if self.monthly_price == 0:
            return 0
        yearly_at_monthly = float(self.monthly_price) * 12
        return int((1 - float(self.yearly_price) / yearly_at_monthly) * 100)


class BillingInvoice(BaseModel):
    """
    Invoice Model
    
    Tracks billing invoices.
    """
    
    __tablename__ = "billing_invoices"
    __table_args__ = (
        Index("ix_billing_invoices_tenant", "tenant_id"),
        Index("ix_billing_invoices_status", "status"),
        Index("ix_billing_invoices_stripe", "stripe_invoice_id"),
    )
    
    tenant_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to tenant"
    )
    
    subscription_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reference to subscription"
    )
    
    stripe_invoice_id: Optional[str] = Column(
        String(100),
        nullable=True,
        unique=True,
        doc="Stripe invoice ID"
    )
    
    invoice_number: str = Column(
        String(50),
        nullable=False,
        unique=True,
        doc="Human-readable invoice number"
    )
    
    status: str = Column(
        String(50),
        nullable=False,
        default="draft",
        doc="Invoice status (draft, open, paid, void, uncollectible)"
    )
    
    # Amounts
    subtotal: float = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=0,
        doc="Subtotal before tax/discount"
    )
    
    tax: float = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=0,
        doc="Tax amount"
    )
    
    discount: float = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=0,
        doc="Discount amount"
    )
    
    total: float = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=0,
        doc="Total amount"
    )
    
    amount_paid: float = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=0,
        doc="Amount paid"
    )
    
    amount_due: float = Column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=0,
        doc="Amount remaining"
    )
    
    # Currency
    currency: str = Column(
        String(3),
        nullable=False,
        default="USD",
        doc="Currency code (ISO 4217)"
    )
    
    # Dates
    invoice_date: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="Invoice date"
    )
    
    due_date: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Payment due date"
    )
    
    paid_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When invoice was paid"
    )
    
    # Payment
    payment_method: Optional[str] = Column(
        String(50),
        nullable=True,
        doc="Payment method used"
    )
    
    charge_id: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Stripe charge ID"
    )
    
    # Invoice items (stored as JSON)
    line_items: dict = Column(
        JSONB,
        default=list,
        nullable=False,
        doc="Invoice line items"
    )
    
    # Metadata
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Invoice description"
    )
    
    notes: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Internal notes"
    )
    
    metadata_json: dict = Column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
        doc="Additional metadata"
    )
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="invoices"
    )
    
    @property
    def is_paid(self) -> bool:
        """Check if invoice is paid."""
        return self.status == "paid"
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        if self.due_date and self.status == "open":
            return datetime.utcnow() > self.due_date
        return False


class AuditLog(BaseModel):
    """
    Audit Log Model
    
    Tracks all actions and changes in the system for compliance and debugging.
    Provides a comprehensive audit trail for security and accountability.
    """
    
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_tenant", "tenant_id"),
        Index("ix_audit_logs_user", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )
    
    # ========================================
    # Tenant and User Context
    # ========================================
    tenant_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        doc="Tenant this log belongs to"
    )
    
    user_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who performed the action"
    )
    
    # ========================================
    # Action Details
    # ========================================
    action: AuditAction = Column(
        SQLEnum(AuditAction),
        nullable=False,
        doc="Type of action performed"
    )
    
    resource_type: str = Column(
        String(100),
        nullable=False,
        doc="Type of resource (e.g., 'user', 'invoice', 'product')"
    )
    
    resource_id: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="ID of the affected resource"
    )
    
    resource_name: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Human-readable name of the resource"
    )
    
    # ========================================
    # Change Details
    # ========================================
    old_values: Optional[dict] = Column(
        JSONB,
        nullable=True,
        doc="Previous values before change"
    )
    
    new_values: Optional[dict] = Column(
        JSONB,
        nullable=True,
        doc="New values after change"
    )
    
    changes: Optional[dict] = Column(
        JSONB,
        nullable=True,
        doc="Summary of what changed"
    )
    
    # ========================================
    # Request Context
    # ========================================
    ip_address: Optional[str] = Column(
        String(45),
        nullable=True,
        doc="IP address of the request"
    )
    
    user_agent: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="User agent string"
    )
    
    request_method: Optional[str] = Column(
        String(10),
        nullable=True,
        doc="HTTP method (GET, POST, PUT, DELETE)"
    )
    
    request_path: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="API endpoint path"
    )
    
    request_id: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Unique request identifier for tracing"
    )
    
    # ========================================
    # Additional Context
    # ========================================
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Human-readable description of the action"
    )
    
    metadata_json: dict = Column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
        doc="Additional metadata about the action"
    )
    
    # ========================================
    # Status
    # ========================================
    status: str = Column(
        String(20),
        default="success",
        nullable=False,
        doc="Status of the action (success, failure, pending)"
    )
    
    error_message: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Error message if action failed"
    )
    
    # ========================================
    # Duration tracking
    # ========================================
    duration_ms: Optional[int] = Column(
        Integer,
        nullable=True,
        doc="Duration of the action in milliseconds"
    )
    
    # ========================================
    # Relationships
    # ========================================
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="audit_logs"
    )
    
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="audit_logs"
    )
    
    @property
    def is_successful(self) -> bool:
        """Check if the action was successful."""
        return self.status == "success"
    
    @property
    def is_failure(self) -> bool:
        """Check if the action failed."""
        return self.status == "failure"
    
    def to_dict(self, exclude: Optional[list] = None) -> dict:
        """
        Convert audit log to dictionary representation.
        
        Args:
            exclude: List of fields to exclude
            
        Returns:
            Dictionary representation
        """
        result = super().to_dict(exclude)
        result["action"] = self.action.value if self.action else None
        return result


# Import User at the end to avoid circular import
from app.models.user import User
