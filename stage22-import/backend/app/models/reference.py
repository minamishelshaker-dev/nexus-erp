"""Tenant-scoped commercial and organization reference data models.

These are first-class master-data entities referenced by CRM and user records.
They intentionally contain real business attributes rather than placeholder tables.
"""
import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Column, ForeignKey, Index, Integer, Numeric,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import BaseModel, TenantMixin


class Industry(BaseModel, TenantMixin):
    __tablename__ = "industries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_industries_tenant_code"),
        Index("ix_industries_tenant_name", "tenant_id", "name"),
    )
    code = Column(String(40), nullable=False)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class PaymentTerm(BaseModel, TenantMixin):
    __tablename__ = "payment_terms"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_payment_terms_tenant_code"),
        CheckConstraint("due_days >= 0", name="ck_payment_terms_due_days_nonnegative"),
        CheckConstraint("discount_days >= 0", name="ck_payment_terms_discount_days_nonnegative"),
        CheckConstraint("discount_percent >= 0 AND discount_percent <= 100", name="ck_payment_terms_discount_percent_range"),
        Index("ix_payment_terms_tenant_name", "tenant_id", "name"),
    )
    code = Column(String(40), nullable=False)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    due_days = Column(Integer, default=0, nullable=False)
    discount_days = Column(Integer, default=0, nullable=False)
    discount_percent = Column(Numeric(5, 2), default=Decimal("0"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class PriceList(BaseModel, TenantMixin):
    __tablename__ = "price_lists"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_price_lists_tenant_code"),
        Index("ix_price_lists_tenant_name", "tenant_id", "name"),
        Index("ix_price_lists_currency", "currency_id"),
    )
    code = Column(String(40), nullable=False)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    currency_id = Column(UUID(as_uuid=True), ForeignKey("currencies.id", ondelete="RESTRICT"), nullable=True)
    price_list_type = Column(String(30), default="sales", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(JSONB, default=dict, nullable=False)


class Territory(BaseModel, TenantMixin):
    __tablename__ = "territories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_territories_tenant_code"),
        Index("ix_territories_parent", "parent_id"),
        Index("ix_territories_tenant_name", "tenant_id", "name"),
    )
    code = Column(String(40), nullable=False)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("territories.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class CustomerGroup(BaseModel, TenantMixin):
    __tablename__ = "customer_groups"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_customer_groups_tenant_code"),
        CheckConstraint("credit_limit >= 0", name="ck_customer_groups_credit_limit_nonnegative"),
        Index("ix_customer_groups_tenant_name", "tenant_id", "name"),
    )
    code = Column(String(40), nullable=False)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    credit_limit = Column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    payment_terms_id = Column(UUID(as_uuid=True), ForeignKey("payment_terms.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class Team(BaseModel, TenantMixin):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_teams_tenant_code"),
        Index("ix_teams_leader", "leader_id"),
        Index("ix_teams_tenant_name", "tenant_id", "name"),
    )
    code = Column(String(40), nullable=False)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    team_type = Column(String(40), default="sales", nullable=False)
    leader_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL", use_alter=True, name="fk_departments_manager_id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class Department(BaseModel, TenantMixin):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_departments_tenant_code"),
        Index("ix_departments_parent", "parent_id"),
        Index("ix_departments_tenant_name", "tenant_id", "name"),
    )
    code = Column(String(40), nullable=False)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    manager_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
