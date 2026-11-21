"""
Nexus ERP - Inventory and Product Models (Enhanced)
===================================================

This module implements comprehensive inventory management with:
- Product management with variants and UOM
- Multi-warehouse and location support
- Stock movements and adjustments
- Inventory valuation (FIFO/Average)
- Integration with accounting
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
    event,
    func,
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

class ProductType(str, enum.Enum):
    """Product type enumeration."""
    PRODUCT = "product"            # منتج مادي
    SERVICE = "service"            # خدمة
    CONSUMABLE = "consumable"      # مستهلك
    DIGITAL = "digital"            # رقمي
    BUNDLE = "bundle"              # حزمة
    TEMPLATE = "template"          # قالب للمتغيرات


class ProductStatus(str, enum.Enum):
    """Product status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"
    OUT_OF_STOCK = "out_of_stock"


class StockMoveType(str, enum.Enum):
    """Stock movement type enumeration."""
    IN = "in"                      # استلام
    OUT = "out"                    # صرف
    INTERNAL = "internal"          # تحويل داخلي
    ADJUSTMENT = "adjustment"      # تسوية جرد
    RETURN_IN = "return_in"        # إرجاع من عميل
    RETURN_OUT = "return_out"      # إرجاع لمورد
    PRODUCTION = "production"      # إنتاج
    LOSS = "loss"                  # هالك/تالف


class StockMoveState(str, enum.Enum):
    """Stock movement state."""
    DRAFT = "draft"                # مقترح
    CONFIRMED = "confirmed"        # مؤكد
    DONE = "done"                  # تم
    CANCELLED = "cancelled"        # ملغي


class ValuationMethod(str, enum.Enum):
    """Inventory valuation method."""
    FIFO = "fifo"                  # الوارد أولاً يصرف أولاً
    AVERAGE = "average"            # متوسط التكلفة المتحرك
    STANDARD = "standard"          # التكلفة المعيارية


class AdjustmentState(str, enum.Enum):
    """Inventory adjustment state."""
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class UOMCategory(str, enum.Enum):
    """Unit of measure category."""
    UNIT = "unit"                  # وحدة
    LENGTH = "length"              # طول
    WEIGHT = "weight"              # وزن
    VOLUME = "volume"              # حجم
    TIME = "time"                  # وقت
    AREA = "area"                  # مساحة


# ========================================
# Unit of Measure (UOM)
# ========================================

class UnitOfMeasure(BaseModel):
    """
    Unit of Measure Model
    
    Supports unit conversions (e.g., 1 box = 12 units).
    """
    __tablename__ = "unit_of_measures"
    __table_args__ = (
        Index("ix_uom_code", "code", unique=True),
        Index("ix_uom_category", "category"),
    )
    
    code: str = Column(String(10), nullable=False, unique=True, doc="UOM code (e.g., 'PCS', 'KG')")
    name: str = Column(String(100), nullable=False, doc="UOM name")
    name_ar: Optional[str] = Column(String(100), nullable=True, doc="Arabic name")
    
    category: UOMCategory = Column(
        SQLEnum(UOMCategory),
        default=UOMCategory.UNIT,
        nullable=False,
        doc="UOM category"
    )
    
    # Base UOM for conversion
    base_uom_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("unit_of_measures.id", ondelete="SET NULL"),
        nullable=True,
        doc="Base UOM for conversions"
    )
    
    # Conversion factor: 1 of this = factor of base
    # Example: If base is 'PCS' and this is 'BOX' with 12 pieces
    # factor = 12 (1 BOX = 12 PCS)
    factor: Decimal = Column(
        Numeric(18, 6),
        default=Decimal("1"),
        nullable=False,
        doc="Conversion factor to base UOM"
    )
    
    rounding: Decimal = Column(
        Numeric(10, 4),
        default=Decimal("0.001"),
        nullable=False,
        doc="Rounding precision"
    )
    
    is_active: bool = Column(Boolean, default=True, nullable=False)
    is_base: bool = Column(Boolean, default=False, nullable=False, doc="Is base unit for category")
    
    # Relationships
    products: Mapped[List["Product"]] = relationship(
        "Product",
        foreign_keys="Product.uom_id",
        back_populates="uom"
    )
    
    def convert_to_base(self, quantity: Decimal) -> Decimal:
        """Convert quantity to base UOM."""
        return quantity * self.factor
    
    def convert_from_base(self, quantity: Decimal) -> Decimal:
        """Convert quantity from base UOM."""
        if self.factor == 0:
            return quantity
        return quantity / self.factor


# ========================================
# Product Category
# ========================================

class ProductCategory(BaseModel, TenantMixin):
    """
    Product Category Model
    
    Hierarchical categorization of products.
    """
    __tablename__ = "product_categories"
    __table_args__ = (
        Index("ix_product_categories_code_tenant", "code", "tenant_id", unique=True),
        Index("ix_product_categories_parent", "parent_id"),
    )
    
    code: str = Column(String(50), nullable=False, doc="Unique category code")
    name: str = Column(String(255), nullable=False, doc="Category name")
    name_ar: Optional[str] = Column(String(255), nullable=True)
    description: Optional[str] = Column(Text, nullable=True)
    
    parent_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("product_categories.id", ondelete="SET NULL"),
        nullable=True
    )
    
    sequence: int = Column(Integer, default=10, nullable=False)
    is_active: bool = Column(Boolean, default=True, nullable=False)
    
    # Default settings
    default_uom_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("unit_of_measures.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Accounting links
    income_account_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    expense_account_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Relationships
    products: Mapped[List["Product"]] = relationship(
        "Product", back_populates="category", lazy="dynamic"
    )
    parent: Mapped[Optional["ProductCategory"]] = relationship(
        "ProductCategory", remote_side="ProductCategory.id", backref="children"
    )


# ========================================
# Product
# ========================================

class Product(BaseModel, TenantMixin):
    """
    Product Model (Enhanced)
    
    Represents a product or service with full inventory tracking.
    """
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_sku_tenant", "sku", "tenant_id", unique=True),
        Index("ix_products_barcode", "barcode"),
        Index("ix_products_category", "category_id"),
        Index("ix_products_status", "status"),
        Index("ix_products_type", "product_type"),
        CheckConstraint("sale_price >= 0", name="ck_products_sale_price"),
        CheckConstraint("cost_price >= 0", name="ck_products_cost_price"),
    )
    
    # ========================================
    # Basic Information
    # ========================================
    sku: str = Column(String(100), nullable=False, doc="Stock Keeping Unit")
    name: str = Column(String(255), nullable=False, doc="Product name")
    name_ar: Optional[str] = Column(String(255), nullable=True)
    description: Optional[str] = Column(Text, nullable=True)
    description_sale: Optional[str] = Column(Text, nullable=True, doc="Description for sales")
    description_purchase: Optional[str] = Column(Text, nullable=True, doc="Description for purchases")
    
    product_type: ProductType = Column(
        SQLEnum(ProductType),
        default=ProductType.PRODUCT,
        nullable=False
    )
    status: ProductStatus = Column(
        SQLEnum(ProductStatus),
        default=ProductStatus.ACTIVE,
        nullable=False
    )
    
    # ========================================
    # Identification
    # ========================================
    barcode: Optional[str] = Column(String(50), nullable=True, index=True)
    barcode_type: Optional[str] = Column(String(20), nullable=True)
    internal_reference: Optional[str] = Column(String(100), nullable=True)
    manufacturer_part_number: Optional[str] = Column(String(100), nullable=True)
    
    # ========================================
    # Categorization
    # ========================================
    category_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("product_categories.id", ondelete="SET NULL"),
        nullable=True
    )
    brand_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    tags: List[str] = Column(ARRAY(String), default=list, nullable=False)
    
    # ========================================
    # Variant Support
    # ========================================
    is_variant: bool = Column(Boolean, default=False, nullable=False)
    template_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=True
    )
    variant_attributes: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Unit of Measure
    # ========================================
    uom_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("unit_of_measures.id"),
        nullable=False
    )
    uom_po_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("unit_of_measures.id", ondelete="SET NULL"),
        nullable=True
    )
    uom_so_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("unit_of_measures.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # ========================================
    # Pricing
    # ========================================
    cost_price: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    sale_price: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    list_price: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    min_sale_price: Optional[Decimal] = Column(Numeric(18, 4), nullable=True)
    currency_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # ========================================
    # Inventory Settings
    # ========================================
    is_stockable: bool = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether product is tracked in inventory"
    )
    valuation_method: ValuationMethod = Column(
        SQLEnum(ValuationMethod),
        default=ValuationMethod.AVERAGE,
        nullable=False
    )
    track_inventory: bool = Column(Boolean, default=True, nullable=False)
    allow_negative_stock: bool = Column(Boolean, default=False, nullable=False)
    auto_reorder: bool = Column(Boolean, default=False, nullable=False)
    
    reorder_point: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    reorder_quantity: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    min_quantity: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    max_quantity: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    shelf_life_days: Optional[int] = Column(Integer, nullable=True)
    track_expiration: bool = Column(Boolean, default=False, nullable=False)
    track_serial: bool = Column(Boolean, default=False, nullable=False)
    track_lot: bool = Column(Boolean, default=False, nullable=False)
    
    # ========================================
    # Dimensions & Weight
    # ========================================
    weight: Optional[Decimal] = Column(Numeric(12, 4), nullable=True, doc="Weight in kg")
    weight_uom_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    volume: Optional[Decimal] = Column(Numeric(12, 4), nullable=True, doc="Volume in m³")
    length: Optional[Decimal] = Column(Numeric(10, 4), nullable=True)
    width: Optional[Decimal] = Column(Numeric(10, 4), nullable=True)
    height: Optional[Decimal] = Column(Numeric(10, 4), nullable=True)
    dimension_uom_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # ========================================
    # Purchase/Sale Settings
    # ========================================
    purchasable: bool = Column(Boolean, default=True, nullable=False)
    saleable: bool = Column(Boolean, default=True, nullable=False)
    available_for_pos: bool = Column(Boolean, default=True, nullable=False)
    available_online: bool = Column(Boolean, default=False, nullable=False)
    requires_shipping: bool = Column(Boolean, default=True, nullable=False)
    
    preferred_supplier_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    supplier_code: Optional[str] = Column(String(100), nullable=True)
    lead_time_days: int = Column(Integer, default=0, nullable=False)
    
    # ========================================
    # Media
    # ========================================
    image_url: Optional[str] = Column(String(500), nullable=True)
    images: List[str] = Column(ARRAY(String), default=list, nullable=False)
    
    # ========================================
    # Accounting Links
    # ========================================
    income_account_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Revenue account for this product"
    )
    expense_account_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="COGS account for this product"
    )
    asset_account_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Inventory asset account"
    )
    
    # ========================================
    # Statistics (Computed/Updated)
    # ========================================
    quantity_on_hand: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    quantity_available: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    quantity_reserved: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    quantity_incoming: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    quantity_outgoing: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    quantity_virtual: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    average_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    standard_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    last_purchase_price: Optional[Decimal] = Column(Numeric(18, 4), nullable=True)
    last_purchase_date: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    last_sale_date: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    
    total_sold: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total_purchased: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # ========================================
    # Custom Fields
    # ========================================
    custom_fields: dict = Column(JSONB, default=dict, nullable=False)
    
    # ========================================
    # Relationships
    # ========================================
    category: Mapped[Optional["ProductCategory"]] = relationship(
        "ProductCategory", back_populates="products"
    )
    uom: Mapped["UnitOfMeasure"] = relationship(
        "UnitOfMeasure", foreign_keys=[uom_id]
    )
    variants: Mapped[List["Product"]] = relationship(
        "Product", back_populates="template", foreign_keys="Product.template_id", lazy="dynamic"
    )
    template: Mapped[Optional["Product"]] = relationship(
        "Product", back_populates="variants", remote_side="Product.id", foreign_keys="Product.template_id"
    )
    stock_quantities: Mapped[List["StockQuantity"]] = relationship(
        "StockQuantity", back_populates="product", cascade="all, delete-orphan", lazy="dynamic"
    )
    stock_moves: Mapped[List["StockMove"]] = relationship(
        "StockMove", back_populates="product", lazy="dynamic"
    )
    
    # ========================================
    # Properties
    # ========================================
    
    @property
    def is_low_stock(self) -> bool:
        """Check if product is below reorder point."""
        return self.quantity_on_hand <= self.reorder_point
    
    @property
    def is_out_of_stock(self) -> bool:
        """Check if product is out of stock."""
        return self.quantity_on_hand <= 0
    
    @property
    def profit_margin(self) -> Decimal:
        """Calculate profit margin percentage."""
        if self.sale_price > 0:
            return ((self.sale_price - self.cost_price) / self.sale_price) * 100
        return Decimal("0")


# ========================================
# Warehouse
# ========================================

class Warehouse(BaseModel, TenantMixin):
    """
    Warehouse Model
    
    Represents a storage location for inventory.
    """
    __tablename__ = "warehouses"
    __table_args__ = (
        Index("ix_warehouses_code_tenant", "code", "tenant_id", unique=True),
    )
    
    code: str = Column(String(50), nullable=False, doc="Warehouse code")
    name: str = Column(String(255), nullable=False, doc="Warehouse name")
    name_ar: Optional[str] = Column(String(255), nullable=True)
    description: Optional[str] = Column(Text, nullable=True)
    
    is_active: bool = Column(Boolean, default=True, nullable=False)
    is_default: bool = Column(Boolean, default=False, nullable=False)
    allow_negative_stock: bool = Column(Boolean, default=False, nullable=False)
    is_shop: bool = Column(Boolean, default=False, nullable=False)
    
    # Address
    address_line1: Optional[str] = Column(String(255), nullable=True)
    address_line2: Optional[str] = Column(String(255), nullable=True)
    city: Optional[str] = Column(String(100), nullable=True)
    state: Optional[str] = Column(String(100), nullable=True)
    postal_code: Optional[str] = Column(String(20), nullable=True)
    country: Optional[str] = Column(String(100), nullable=True)
    
    # Contact
    contact_name: Optional[str] = Column(String(100), nullable=True)
    phone: Optional[str] = Column(String(20), nullable=True)
    email: Optional[str] = Column(String(255), nullable=True)
    
    # Accounting
    inventory_account_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Inventory account for this warehouse"
    )
    
    # Relationships
    locations: Mapped[List["StockLocation"]] = relationship(
        "StockLocation", back_populates="warehouse", cascade="all, delete-orphan", lazy="dynamic"
    )
    stock_quantities: Mapped[List["StockQuantity"]] = relationship(
        "StockQuantity", back_populates="warehouse", lazy="dynamic"
    )


# ========================================
# Stock Location
# ========================================

class StockLocation(BaseModel, TenantMixin):
    """
    Stock Location Model
    
    Represents a specific location within a warehouse (shelf, bin, etc.)
    """
    __tablename__ = "stock_locations"
    __table_args__ = (
        Index("ix_stock_locations_warehouse", "warehouse_id"),
        UniqueConstraint("warehouse_id", "code", name="uq_location_code"),
    )
    
    warehouse_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False
    )
    
    code: str = Column(String(50), nullable=False, doc="Location code (e.g., A-01-01)")
    name: str = Column(String(255), nullable=False, doc="Location name")
    
    location_type: str = Column(
        String(20),
        default="internal",
        nullable=False,
        doc="Location type: internal, input, output, inventory_loss"
    )
    
    parent_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("stock_locations.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Physical location
    corridor: Optional[str] = Column(String(20), nullable=True)
    row: Optional[str] = Column(String(20), nullable=True)
    shelf: Optional[str] = Column(String(20), nullable=True)
    bin: Optional[str] = Column(String(20), nullable=True)
    
    max_capacity: Optional[Decimal] = Column(Numeric(10, 2), nullable=True)
    is_active: bool = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="locations")
    parent: Mapped[Optional["StockLocation"]] = relationship(
        "StockLocation", remote_side="StockLocation.id", backref="children"
    )


# ========================================
# Stock Quantity
# ========================================

class StockQuantity(BaseModel, TenantMixin):
    """
    Stock Quantity Model
    
    Tracks stock levels per product per location.
    """
    __tablename__ = "stock_quantities"
    __table_args__ = (
        Index("ix_stock_quantities_product", "product_id"),
        Index("ix_stock_quantities_warehouse", "warehouse_id"),
        Index("ix_stock_quantities_location", "location_id"),
        UniqueConstraint("product_id", "location_id", name="uq_stock_product_location"),
    )
    
    product_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    
    warehouse_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False
    )
    
    location_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("stock_locations.id", ondelete="SET NULL"),
        nullable=True
    )
    
    quantity: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    quantity_reserved: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    quantity_available: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    quantity_incoming: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    quantity_outgoing: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Valuation
    value: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    average_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Tracking
    lot_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    serial_number: Optional[str] = Column(String(100), nullable=True)
    expiration_date: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="stock_quantities")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="stock_quantities")
    location: Mapped[Optional["StockLocation"]] = relationship("StockLocation")


# ========================================
# Stock Move
# ========================================

class StockMove(BaseModel, TenantMixin):
    """
    Stock Move Model
    
    Records all inventory movements with full tracking.
    """
    __tablename__ = "stock_moves"
    __table_args__ = (
        Index("ix_stock_moves_product", "product_id"),
        Index("ix_stock_moves_location_from", "location_from_id"),
        Index("ix_stock_moves_location_to", "location_to_id"),
        Index("ix_stock_moves_date", "date"),
        Index("ix_stock_moves_state", "state"),
        Index("ix_stock_moves_reference", "reference"),
    )
    
    # Identification
    number: str = Column(String(50), nullable=False, doc="Move number")
    reference: Optional[str] = Column(String(100), nullable=True, doc="Reference document")
    reference_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    reference_type: Optional[str] = Column(String(50), nullable=True)
    
    # Product & Quantity
    product_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    quantity: Decimal = Column(Numeric(18, 4), nullable=False)
    quantity_done: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    uom_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("unit_of_measures.id"), nullable=False)
    
    # Locations
    location_from_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("stock_locations.id", ondelete="SET NULL"),
        nullable=True,
        doc="Source location"
    )
    location_to_id: Optional[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("stock_locations.id", ondelete="SET NULL"),
        nullable=True,
        doc="Destination location"
    )
    warehouse_from_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    warehouse_to_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    # Move Details
    move_type: StockMoveType = Column(SQLEnum(StockMoveType), nullable=False)
    state: StockMoveState = Column(
        SQLEnum(StockMoveState),
        default=StockMoveState.DRAFT,
        nullable=False
    )
    
    date_expected: Optional[date] = Column(Date, nullable=True)
    date: date = Column(Date, nullable=False, doc="Move date")
    date_done: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    
    # Cost & Valuation
    unit_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Partner
    partner_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    partner_type: Optional[str] = Column(String(20), nullable=True)
    
    # Tracking
    lot_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    serial_number: Optional[str] = Column(String(100), nullable=True)
    expiration_date: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    
    # Additional
    reason: Optional[str] = Column(String(255), nullable=True)
    notes: Optional[str] = Column(Text, nullable=True)
    
    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="stock_moves")
    uom: Mapped["UnitOfMeasure"] = relationship("UnitOfMeasure")
    location_from: Mapped[Optional["StockLocation"]] = relationship(
        "StockLocation", foreign_keys=[location_from_id]
    )
    location_to: Mapped[Optional["StockLocation"]] = relationship(
        "StockLocation", foreign_keys=[location_to_id]
    )


# ========================================
# Inventory Adjustment
# ========================================

class InventoryAdjustment(BaseModel, TenantMixin):
    """
    Inventory Adjustment Model
    
    For periodic stock counts and corrections.
    """
    __tablename__ = "inventory_adjustments"
    __table_args__ = (
        Index("ix_inventory_adjustments_number", "number"),
        Index("ix_inventory_adjustments_date", "date"),
        Index("ix_inventory_adjustments_state", "state"),
    )
    
    number: str = Column(String(50), nullable=False, doc="Adjustment number")
    date: date = Column(Date, nullable=False)
    
    location_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("stock_locations.id"),
        nullable=False
    )
    warehouse_id: uuid.UUID = Column(UUID(as_uuid=True), nullable=False)
    
    reason: Optional[str] = Column(String(255), nullable=True)
    state: AdjustmentState = Column(
        SQLEnum(AdjustmentState),
        default=AdjustmentState.DRAFT,
        nullable=False
    )
    
    # Summary
    total_adjustments: int = Column(Integer, default=0, nullable=False)
    total_value: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    # Posting
    posted_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    posted_by_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    
    notes: Optional[str] = Column(Text, nullable=True)
    
    # Relationships
    lines: Mapped[List["AdjustmentLine"]] = relationship(
        "AdjustmentLine", back_populates="adjustment", cascade="all, delete-orphan"
    )
    location: Mapped["StockLocation"] = relationship("StockLocation")


class AdjustmentLine(BaseModel, TenantMixin):
    """
    Adjustment Line Model
    
    Individual product adjustments within an inventory count.
    """
    __tablename__ = "adjustment_lines"
    __table_args__ = (
        Index("ix_adjustment_lines_adjustment", "adjustment_id"),
        Index("ix_adjustment_lines_product", "product_id"),
    )
    
    adjustment_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("inventory_adjustments.id", ondelete="CASCADE"),
        nullable=False
    )
    
    product_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    
    expected_qty: Decimal = Column(Numeric(18, 4), nullable=False, doc="Expected quantity")
    actual_qty: Decimal = Column(Numeric(18, 4), nullable=False, doc="Actual counted quantity")
    difference: Decimal = Column(Numeric(18, 4), nullable=False, doc="Difference (actual - expected)")
    
    unit_cost: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    value_difference: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    lot_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    serial_number: Optional[str] = Column(String(100), nullable=True)
    
    notes: Optional[str] = Column(Text, nullable=True)
    
    # Relationships
    adjustment: Mapped["InventoryAdjustment"] = relationship(
        "InventoryAdjustment", back_populates="lines"
    )


# ========================================
# Stock Lot
# ========================================

class StockLot(BaseModel, TenantMixin):
    """
    Stock Lot Model
    
    Tracks products by lot/batch number.
    """
    __tablename__ = "stock_lots"
    __table_args__ = (
        Index("ix_stock_lots_name", "name"),
        Index("ix_stock_lots_product", "product_id"),
    )
    
    name: str = Column(String(100), nullable=False, doc="Lot number")
    product_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    
    quantity: Decimal = Column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    production_date: Optional[date] = Column(Date, nullable=True)
    expiration_date: Optional[date] = Column(Date, nullable=True)
    use_by_date: Optional[date] = Column(Date, nullable=True)
    best_before_date: Optional[date] = Column(Date, nullable=True)
    
    supplier_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    supplier_lot: Optional[str] = Column(String(100), nullable=True)
    
    notes: Optional[str] = Column(Text, nullable=True)


# ========================================
# Stock Valuation History
# ========================================

class StockValuation(BaseModel, TenantMixin):
    """
    Stock Valuation History
    
    Records cost changes for valuation purposes.
    """
    __tablename__ = "stock_valuations"
    __table_args__ = (
        Index("ix_stock_valuations_product", "product_id"),
        Index("ix_stock_valuations_date", "date"),
    )
    
    product_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    date: datetime = Column(DateTime(timezone=True), nullable=False)
    
    quantity_before: Decimal = Column(Numeric(18, 4), nullable=False)
    quantity_after: Decimal = Column(Numeric(18, 4), nullable=False)
    quantity_change: Decimal = Column(Numeric(18, 4), nullable=False)
    
    cost_before: Decimal = Column(Numeric(18, 4), nullable=False)
    cost_after: Decimal = Column(Numeric(18, 4), nullable=False)
    
    value_before: Decimal = Column(Numeric(18, 4), nullable=False)
    value_after: Decimal = Column(Numeric(18, 4), nullable=False)
    value_change: Decimal = Column(Numeric(18, 4), nullable=False)
    
    move_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), nullable=True)
    move_type: Optional[str] = Column(String(50), nullable=True)


# ========================================
# SQLAlchemy Events
# ========================================

@event.listens_for(StockMove, 'after_insert')
def on_stock_move_insert(mapper, connection, target):
    """Update stock quantities after a stock move is inserted."""
    if target.state != StockMoveState.DONE:
        return
    
    # This would be handled in the service layer for async operations
    pass


@event.listens_for(AdjustmentLine, 'after_insert')
def on_adjustment_line_insert(mapper, connection, target):
    """Calculate difference after adjustment line is inserted."""
    target.difference = target.actual_qty - target.expected_qty
    target.value_difference = target.difference * target.unit_cost
