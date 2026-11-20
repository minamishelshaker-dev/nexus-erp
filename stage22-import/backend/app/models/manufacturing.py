"""
Nexus ERP - Manufacturing Module Models
========================================

This module implements comprehensive manufacturing (MRP) functionality including:
- Bill of Materials (BOM)
- Work Centers
- Routings
- Manufacturing Orders
- Production Planning
"""

from datetime import datetime, date, time
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
    Float,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, Mapped
from typing import Optional, List
from decimal import Decimal
import enum
import uuid

from app.models.base import BaseModel, TenantMixin


# ========================================
# Enums
# ========================================

class BOMType(str, enum.Enum):
    """Bill of Material type enumeration."""
    MANUFACTURE = "manufacture"      # تصنيع
    ASSEMBLY = "assembly"            # تجميع
    KIT = "kit"                      # طقم
    SUBCONTRACTING = "subcontracting"  # تعاقد من الباطن


class BOMState(str, enum.Enum):
    """BOM state enumeration."""
    DRAFT = "draft"                  # مسودة
    ACTIVE = "active"                # نشط
    INACTIVE = "inactive"            # غير نشط


class WorkCenterState(str, enum.Enum):
    """Work center state enumeration."""
    AVAILABLE = "available"          # متاح
    BUSY = "busy"                    # مشغول
    MAINTENANCE = "maintenance"      # صيانة
    UNAVAILABLE = "unavailable"      # غير متاح


class MOState(str, enum.Enum):
    """Manufacturing Order state enumeration."""
    DRAFT = "draft"                  # مسودة
    CONFIRMED = "confirmed"          # مؤكد
    PLANNED = "planned"              # مخطط
    IN_PROGRESS = "in_progress"      # قيد التنفيذ
    DONE = "done"                    # منجز
    CANCELLED = "cancelled"          # ملغي


class MOOperationState(str, enum.Enum):
    """MO Operation state enumeration."""
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


# ========================================
# Bill of Materials
# ========================================

class BillOfMaterial(BaseModel, TenantMixin):
    """
    Bill of Material Model (قائمة المواد)
    
    Defines the components and operations needed to produce a product.
    """
    __tablename__ = "bills_of_materials"
    __table_args__ = (
        Index("ix_boms_product", "product_id"),
        Index("ix_boms_code", "code"),
        Index("ix_boms_company", "tenant_id"),
        UniqueConstraint("code", "tenant_id", name="uq_bom_code"),
    )
    
    # Identification
    code: str = Column(
        String(50),
        nullable=False,
        doc="BOM code"
    )
    name: str = Column(
        String(255),
        nullable=False,
        doc="BOM name"
    )
    
    # Product being produced
    product_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        doc="Product being manufactured"
    )
    
    # Quantity produced
    product_qty: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("1"),
        nullable=False,
        doc="Quantity of product produced by this BOM"
    )
    product_uom_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Unit of measure for product quantity"
    )
    
    # Type
    bom_type: BOMType = Column(
        SQLEnum(BOMType),
        default=BOMType.MANUFACTURE,
        nullable=False,
        doc="Type of BOM"
    )
    
    # State
    state: BOMState = Column(
        SQLEnum(BOMState),
        default=BOMState.DRAFT,
        nullable=False
    )
    
    # Versioning
    version: int = Column(
        Integer,
        default=1,
        nullable=False,
        doc="BOM version number"
    )
    active_date: Optional[date] = Column(
        Date,
        nullable=True,
        doc="Date when this version became active"
    )
    
    # Routing
    routing_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("routings.id", ondelete="SET NULL"),
        nullable=True,
        doc="Associated routing"
    )
    
    # Costs
    material_cost: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Total material cost"
    )
    labor_cost: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Total labor cost"
    )
    overhead_cost: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Total overhead cost"
    )
    total_cost: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Total BOM cost"
    )
    
    # Additional Info
    notes: Optional[str] = Column(Text, nullable=True)
    attachments: List[str] = Column(ARRAY(String), default=list, nullable=False)
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    lines: Mapped[List["BOMLine"]] = relationship(
        "BOMLine",
        back_populates="bom",
        cascade="all, delete-orphan",
        order_by="BOMLine.sequence"
    )
    operations: Mapped[List["BOMOperation"]] = relationship(
        "BOMOperation",
        back_populates="bom",
        cascade="all, delete-orphan",
        order_by="BOMOperation.sequence"
    )
    manufacturing_orders: Mapped[List["ManufacturingOrder"]] = relationship(
        "ManufacturingOrder",
        back_populates="bom"
    )
    
    # ========================================
    # Methods
    # ========================================
    
    def calculate_costs(self):
        """Calculate total BOM costs from lines and operations."""
        self.material_cost = sum(
            line.total_cost for line in self.lines
        ) if self.lines else Decimal("0")
        
        self.labor_cost = sum(
            op.total_cost for op in self.operations
        ) if self.operations else Decimal("0")
        
        self.total_cost = self.material_cost + self.labor_cost + self.overhead_cost


class BOMLine(BaseModel, TenantMixin):
    """
    BOM Line Model (بند قائمة المواد)
    
    A single component in a Bill of Material.
    """
    __tablename__ = "bom_lines"
    __table_args__ = (
        Index("ix_bom_lines_bom", "bom_id"),
        Index("ix_bom_lines_product", "product_id"),
    )
    
    bom_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("bills_of_materials.id", ondelete="CASCADE"),
        nullable=False
    )
    
    sequence: int = Column(Integer, default=10, nullable=False)
    
    # Component Product
    product_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        doc="Component product"
    )
    
    # Quantity
    product_qty: Decimal = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Quantity needed per BOM unit"
    )
    product_uom_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Loss/Scrap
    scrap_percent: Decimal = Column(
        Numeric(5, 2),
        default=Decimal("0"),
        nullable=False,
        doc="Expected scrap percentage"
    )
    scrap_qty: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Calculated scrap quantity"
    )
    
    # Cost
    unit_cost: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Unit cost at time of BOM creation"
    )
    total_cost: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Total cost for this line"
    )
    
    # Source
    source_location_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Source location for materials"
    )
    
    # Additional
    operation_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Related operation (if consumed at specific operation)"
    )
    notes: Optional[str] = Column(Text, nullable=True)
    
    # ========================================
    # Relationships
    # ========================================
    bom: Mapped["BillOfMaterial"] = relationship("BillOfMaterial", back_populates="lines")
    
    # ========================================
    # Methods
    # ========================================
    
    def calculate_total(self):
        """Calculate total quantity and cost."""
        self.scrap_qty = self.product_qty * (self.scrap_percent / 100)
        total_qty = self.product_qty + self.scrap_qty
        self.total_cost = total_qty * self.unit_cost


class BOMOperation(BaseModel, TenantMixin):
    """
    BOM Operation Model (عملية تصنيع)
    
    An operation step in the manufacturing process.
    """
    __tablename__ = "bom_operations"
    __table_args__ = (
        Index("ix_bom_operations_bom", "bom_id"),
        Index("ix_bom_operations_workcenter", "workcenter_id"),
    )
    
    bom_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("bills_of_materials.id", ondelete="CASCADE"),
        nullable=False
    )
    
    sequence: int = Column(Integer, default=10, nullable=False)
    name: str = Column(String(255), nullable=False)
    
    # Work Center
    workcenter_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("work_centers.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Duration
    duration_expected: Decimal = Column(
        Numeric(10, 2),
        default=Decimal("0"),
        nullable=False,
        doc="Expected duration in minutes"
    )
    duration_per_unit: Decimal = Column(
        Numeric(10, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Duration per unit produced"
    )
    
    # Costs
    labor_cost_per_hour: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False
    )
    machine_cost_per_hour: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False
    )
    total_cost: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False
    )
    
    # Additional
    description: Optional[str] = Column(Text, nullable=True)
    instructions: Optional[str] = Column(Text, nullable=True)
    
    # ========================================
    # Relationships
    # ========================================
    bom: Mapped["BillOfMaterial"] = relationship("BillOfMaterial", back_populates="operations")


# ========================================
# Work Center
# ========================================

class WorkCenter(BaseModel, TenantMixin):
    """
    Work Center Model (مركز العمل)
    
    A production resource (machine, workstation, or labor group).
    """
    __tablename__ = "work_centers"
    __table_args__ = (
        Index("ix_work_centers_code", "code"),
        Index("ix_work_centers_company", "tenant_id"),
        UniqueConstraint("code", "tenant_id", name="uq_workcenter_code"),
    )
    
    # Identification
    code: str = Column(String(50), nullable=False)
    name: str = Column(String(255), nullable=False)
    
    # Capacity
    capacity_per_hour: Decimal = Column(
        Numeric(10, 2),
        default=Decimal("1"),
        nullable=False,
        doc="Production capacity per hour"
    )
    efficiency: Decimal = Column(
        Numeric(5, 2),
        default=Decimal("100"),
        nullable=False,
        doc="Efficiency percentage"
    )
    
    # Costs
    cost_per_hour: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Operating cost per hour"
    )
    labor_cost_per_hour: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False
    )
    machine_cost_per_hour: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False
    )
    
    # State
    state: WorkCenterState = Column(
        SQLEnum(WorkCenterState),
        default=WorkCenterState.AVAILABLE,
        nullable=False
    )
    
    # Availability
    available_from: Optional[time] = Column(String(5), nullable=True)  # HH:MM
    available_to: Optional[time] = Column(String(5), nullable=True)    # HH:MM
    working_days: List[str] = Column(
        ARRAY(String),
        default=["mon", "tue", "wed", "thu", "fri"],
        nullable=False
    )
    
    # Location
    location_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Additional
    is_active: bool = Column(Boolean, default=True, nullable=False)
    notes: Optional[str] = Column(Text, nullable=True)
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    operations: Mapped[List["MOOperation"]] = relationship(
        "MOOperation", back_populates="workcenter"
    )


# Need to import time for column type
from datetime import time


# ========================================
# Routing
# ========================================

class Routing(BaseModel, TenantMixin):
    """
    Routing Model (مسار الإنتاج)
    
    Defines the sequence of operations for production.
    """
    __tablename__ = "routings"
    __table_args__ = (
        Index("ix_routings_code", "code"),
        Index("ix_routings_company", "tenant_id"),
    )
    
    code: str = Column(String(50), nullable=False)
    name: str = Column(String(255), nullable=False)
    
    # Total time
    total_duration: Decimal = Column(
        Numeric(10, 2),
        default=Decimal("0"),
        nullable=False,
        doc="Total production time in minutes"
    )
    
    is_active: bool = Column(Boolean, default=True, nullable=False)
    notes: Optional[str] = Column(Text, nullable=True)
    
    # ========================================
    # Relationships
    # ========================================
    steps: Mapped[List["RoutingStep"]] = relationship(
        "RoutingStep",
        back_populates="routing",
        cascade="all, delete-orphan",
        order_by="RoutingStep.sequence"
    )


class RoutingStep(BaseModel, TenantMixin):
    """
    Routing Step Model (خطوة المسار)
    
    A single step in a routing.
    """
    __tablename__ = "routing_steps"
    __table_args__ = (
        Index("ix_routing_steps_routing", "routing_id"),
        Index("ix_routing_steps_workcenter", "workcenter_id"),
    )
    
    routing_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("routings.id", ondelete="CASCADE"),
        nullable=False
    )
    
    sequence: int = Column(Integer, default=10, nullable=False)
    name: str = Column(String(255), nullable=False)
    
    workcenter_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("work_centers.id", ondelete="SET NULL"),
        nullable=True
    )
    
    duration_expected: Decimal = Column(
        Numeric(10, 2),
        default=Decimal("0"),
        nullable=False
    )
    duration_per_unit: Decimal = Column(
        Numeric(10, 4),
        default=Decimal("0")
    )
    
    description: Optional[str] = Column(Text, nullable=True)
    
    # ========================================
    # Relationships
    # ========================================
    routing: Mapped["Routing"] = relationship("Routing", back_populates="steps")


# ========================================
# Manufacturing Order
# ========================================

class ManufacturingOrder(BaseModel, TenantMixin):
    """
    Manufacturing Order Model (أمر التصنيع)
    
    Order to produce a specific quantity of a product.
    """
    __tablename__ = "manufacturing_orders"
    __table_args__ = (
        Index("ix_mos_number", "number"),
        Index("ix_mos_product", "product_id"),
        Index("ix_mos_state", "state"),
        Index("ix_mos_date", "planned_date"),
        Index("ix_mos_company", "tenant_id"),
        UniqueConstraint("number", "tenant_id", name="uq_mo_number"),
    )
    
    # Identification
    number: str = Column(
        String(50),
        nullable=False,
        doc="MO number (auto-generated)"
    )
    name: str = Column(
        String(255),
        nullable=False,
        doc="MO name/reference"
    )
    
    # Product to Produce
    product_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False
    )
    bom_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("bills_of_materials.id", ondelete="SET NULL"),
        nullable=True
    )
    routing_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("routings.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Quantity
    product_qty: Decimal = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Quantity to produce"
    )
    product_uom_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    qty_produced: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Quantity already produced"
    )
    
    # State
    state: MOState = Column(
        SQLEnum(MOState),
        default=MOState.DRAFT,
        nullable=False
    )
    
    # Dates
    planned_date: Optional[date] = Column(
        Date,
        nullable=True,
        doc="Planned production date"
    )
    date_start: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Actual start date"
    )
    date_finished: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Actual finish date"
    )
    
    # Source
    origin: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Origin document reference"
    )
    sale_order_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Location
    location_src_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Source location for materials"
    )
    location_dest_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Destination location for finished goods"
    )
    
    # Costs
    material_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    labor_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    overhead_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    total_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    unit_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    
    # Priority
    priority: str = Column(
        String(20),
        default="normal",
        nullable=False
    )
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # Tracking
    confirmed_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    confirmed_by_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # ========================================
    # Relationships
    # ========================================
    material_lines: Mapped[List["MOLine"]] = relationship(
        "MOLine",
        back_populates="mo",
        cascade="all, delete-orphan",
        foreign_keys="MOLine.mo_id"
    )
    finished_lines: Mapped[List["MOFinish"]] = relationship(
        "MOFinish",
        back_populates="mo",
        cascade="all, delete-orphan"
    )
    operations: Mapped[List["MOOperation"]] = relationship(
        "MOOperation",
        back_populates="mo",
        cascade="all, delete-orphan",
        order_by="MOOperation.sequence"
    )
    bom: Mapped[Optional["BillOfMaterial"]] = relationship(
        "BillOfMaterial", back_populates="manufacturing_orders"
    )
    
    # ========================================
    # Properties
    # ========================================
    
    @property
    def qty_remaining(self) -> Decimal:
        """Get remaining quantity to produce."""
        return self.product_qty - self.qty_produced
    
    @property
    def progress_percent(self) -> float:
        """Get production progress percentage."""
        if self.product_qty > 0:
            return float(self.qty_produced / self.product_qty * 100)
        return 0.0
    
    @property
    def is_finished(self) -> bool:
        """Check if MO is fully produced."""
        return self.qty_produced >= self.product_qty


class MOLine(BaseModel, TenantMixin):
    """
    MO Line Model (بند أمر التصنيع - المواد)
    
    Material consumption line in a manufacturing order.
    """
    __tablename__ = "mo_lines"
    __table_args__ = (
        Index("ix_mo_lines_mo", "mo_id"),
        Index("ix_mo_lines_product", "product_id"),
    )
    
    mo_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("manufacturing_orders.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Product
    product_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    # Quantity
    product_qty: Decimal = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Planned quantity to consume"
    )
    qty_consumed: Decimal = Column(
        Numeric(18, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Actually consumed quantity"
    )
    product_uom_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Source
    location_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    stock_move_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Cost
    unit_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    total_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    
    # ========================================
    # Relationships
    # ========================================
    mo: Mapped["ManufacturingOrder"] = relationship(
        "ManufacturingOrder", back_populates="material_lines"
    )


class MOFinish(BaseModel, TenantMixin):
    """
    MO Finish Model (المنتج النهائي)
    
    Finished product from a manufacturing order.
    """
    __tablename__ = "mo_finishes"
    __table_args__ = (
        Index("ix_mo_finishes_mo", "mo_id"),
        Index("ix_mo_finishes_product", "product_id"),
    )
    
    mo_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("manufacturing_orders.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Product
    product_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    # Quantity
    product_qty: Decimal = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Quantity produced"
    )
    product_uom_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Destination
    location_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    lot_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    lot_name: Optional[str] = Column(String(100), nullable=True)
    
    # Stock Move
    stock_move_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Cost
    unit_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    total_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    
    # ========================================
    # Relationships
    # ========================================
    mo: Mapped["ManufacturingOrder"] = relationship(
        "ManufacturingOrder", back_populates="finished_lines"
    )


class MOOperation(BaseModel, TenantMixin):
    """
    MO Operation Model (عملية الإنتاج)
    
    Operation execution in a manufacturing order.
    """
    __tablename__ = "mo_operations"
    __table_args__ = (
        Index("ix_mo_operations_mo", "mo_id"),
        Index("ix_mo_operations_workcenter", "workcenter_id"),
    )
    
    mo_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("manufacturing_orders.id", ondelete="CASCADE"),
        nullable=False
    )
    
    sequence: int = Column(Integer, default=10, nullable=False)
    name: str = Column(String(255), nullable=False)
    
    # Work Center
    workcenter_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("work_centers.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # State
    state: MOOperationState = Column(
        SQLEnum(MOOperationState),
        default=MOOperationState.PENDING,
        nullable=False
    )
    
    # Duration
    duration_expected: Decimal = Column(
        Numeric(10, 2),
        default=Decimal("0"),
        nullable=False,
        doc="Expected duration in minutes"
    )
    duration_actual: Decimal = Column(
        Numeric(10, 2),
        default=Decimal("0"),
        nullable=False,
        doc="Actual duration in minutes"
    )
    
    # Costs
    labor_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    machine_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    total_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    
    # Tracking
    date_start: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    date_finished: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    
    # Additional
    notes: Optional[str] = Column(Text, nullable=True)
    
    # ========================================
    # Relationships
    # ========================================
    mo: Mapped["ManufacturingOrder"] = relationship(
        "ManufacturingOrder", back_populates="operations"
    )
    workcenter: Mapped[Optional["WorkCenter"]] = relationship(
        "WorkCenter", back_populates="operations"
    )


# ========================================
# Production Plan
# ========================================

class ProductionPlan(BaseModel, TenantMixin):
    """
    Production Plan Model (خطة الإنتاج)
    
    Planning document for production scheduling.
    """
    __tablename__ = "production_plans"
    __table_args__ = (
        Index("ix_production_plans_date", "planned_date"),
        Index("ix_production_plans_company", "tenant_id"),
    )
    
    name: str = Column(String(255), nullable=False)
    planned_date: date = Column(Date, nullable=False)
    
    state: str = Column(
        String(20),
        default="draft",
        nullable=False
    )
    
    # Summary
    total_orders: int = Column(Integer, default=0)
    total_products: int = Column(Integer, default=0)
    total_quantity: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    total_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"))
    
    notes: Optional[str] = Column(Text, nullable=True)
    
    # ========================================
    # Relationships
    # ========================================
    lines: Mapped[List["ProductionPlanLine"]] = relationship(
        "ProductionPlanLine",
        back_populates="plan",
        cascade="all, delete-orphan"
    )


class ProductionPlanLine(BaseModel, TenantMixin):
    """
    Production Plan Line Model
    """
    __tablename__ = "production_plan_lines"
    __table_args__ = (
        Index("ix_production_plan_lines_plan", "plan_id"),
    )
    
    plan_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("production_plans.id", ondelete="CASCADE"),
        nullable=False
    )
    
    product_id: uuid.UUID = Column(UUID(as_uuid=True), nullable=False)
    mo_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    quantity: Decimal = Column(Numeric(18, 4), nullable=False)
    workcenter_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    planned_start: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    planned_end: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    
    # ========================================
    # Relationships
    # ========================================
    plan: Mapped["ProductionPlan"] = relationship("ProductionPlan", back_populates="lines")
