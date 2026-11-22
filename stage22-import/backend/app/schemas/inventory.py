"""
Nexus ERP - Inventory Schemas
==============================

Pydantic schemas for inventory module API validation and serialization.
"""

from datetime import datetime, date as Date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from uuid import UUID
from decimal import Decimal


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
# Unit of Measure Schemas
# ========================================

class UOMCreate(BaseModel):
    """Schema for creating a unit of measure."""
    code: str = Field(..., min_length=1, max_length=10, description="UOM code (e.g., PCS, KG)")
    name: str = Field(..., min_length=1, max_length=100, description="UOM name")
    name_ar: Optional[str] = Field(None, max_length=100)
    category: str = Field(default="unit", description="UOM category")
    base_uom_id: Optional[UUID] = Field(None, description="Base UOM for conversion")
    factor: Decimal = Field(default=Decimal("1"), gt=0, description="Conversion factor")
    rounding: Decimal = Field(default=Decimal("0.001"), ge=0)
    is_active: bool = Field(default=True)


class UOMResponse(BaseSchema):
    """UOM response schema."""
    id: UUID
    code: str
    name: str
    name_ar: Optional[str] = None
    category: str
    base_uom_id: Optional[UUID] = None
    factor: Decimal
    rounding: Decimal
    is_active: bool
    is_base: bool


class UOMListResponse(BaseModel):
    """UOM list response."""
    items: List[UOMResponse]
    total: int


# ========================================
# Product Category Schemas
# ========================================

class ProductCategoryBriefResponse(BaseSchema):
    """Brief product category response."""
    id: UUID
    code: str
    name: str


class ProductCategoryCreate(BaseModel):
    """Schema for creating a product category."""
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    name_ar: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    default_uom_id: Optional[UUID] = None
    income_account_id: Optional[UUID] = None
    expense_account_id: Optional[UUID] = None
    sequence: int = Field(default=10)


class ProductCategoryResponse(ProductCategoryBriefResponse):
    """Full product category response."""
    name_ar: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    sequence: int
    is_active: bool
    default_uom_id: Optional[UUID] = None
    income_account_id: Optional[UUID] = None
    expense_account_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


# ========================================
# Product Schemas
# ========================================

class ProductBriefResponse(BaseSchema):
    """Brief product information."""
    id: UUID
    sku: str
    name: str
    product_type: str
    status: str
    sale_price: Decimal
    cost_price: Decimal
    quantity_on_hand: Decimal
    barcode: Optional[str] = None


class ProductCreate(BaseModel):
    """Schema for creating a product."""
    sku: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    name_ar: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    description_sale: Optional[str] = None
    description_purchase: Optional[str] = None
    
    product_type: str = Field(default="product")
    status: str = Field(default="active")
    
    barcode: Optional[str] = Field(None, max_length=50)
    barcode_type: Optional[str] = Field(None, max_length=20)
    internal_reference: Optional[str] = Field(None, max_length=100)
    manufacturer_part_number: Optional[str] = Field(None, max_length=100)
    
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    tags: List[str] = Field(default_factory=list)
    
    uom_id: UUID = Field(..., description="Base unit of measure")
    uom_po_id: Optional[UUID] = None
    uom_so_id: Optional[UUID] = None
    
    cost_price: Decimal = Field(default=Decimal("0"), ge=0)
    sale_price: Decimal = Field(default=Decimal("0"), ge=0)
    list_price: Decimal = Field(default=Decimal("0"), ge=0)
    min_sale_price: Optional[Decimal] = Field(None, ge=0)
    currency_id: Optional[UUID] = None
    
    is_stockable: bool = Field(default=True)
    valuation_method: str = Field(default="average")
    track_inventory: bool = Field(default=True)
    allow_negative_stock: bool = Field(default=False)
    auto_reorder: bool = Field(default=False)
    reorder_point: Decimal = Field(default=Decimal("0"), ge=0)
    reorder_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    min_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    max_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    
    shelf_life_days: Optional[int] = Field(None, ge=0)
    track_expiration: bool = Field(default=False)
    track_serial: bool = Field(default=False)
    track_lot: bool = Field(default=False)
    
    weight: Optional[Decimal] = Field(None, ge=0)
    volume: Optional[Decimal] = Field(None, ge=0)
    length: Optional[Decimal] = Field(None, ge=0)
    width: Optional[Decimal] = Field(None, ge=0)
    height: Optional[Decimal] = Field(None, ge=0)
    
    purchasable: bool = Field(default=True)
    saleable: bool = Field(default=True)
    available_for_pos: bool = Field(default=True)
    available_online: bool = Field(default=False)
    requires_shipping: bool = Field(default=True)
    
    preferred_supplier_id: Optional[UUID] = None
    supplier_code: Optional[str] = Field(None, max_length=100)
    lead_time_days: int = Field(default=0, ge=0)
    
    image_url: Optional[str] = Field(None, max_length=500)
    
    income_account_id: Optional[UUID] = None
    expense_account_id: Optional[UUID] = None
    asset_account_id: Optional[UUID] = None
    
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('product_type')
    @classmethod
    def validate_product_type(cls, v: str) -> str:
        allowed = ['product', 'service', 'consumable', 'digital', 'bundle', 'template']
        if v.lower() not in allowed:
            raise ValueError(f'Product type must be one of: {allowed}')
        return v.lower()
    
    @field_validator('valuation_method')
    @classmethod
    def validate_valuation_method(cls, v: str) -> str:
        allowed = ['fifo', 'average', 'standard']
        if v.lower() not in allowed:
            raise ValueError(f'Valuation method must be one of: {allowed}')
        return v.lower()


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    name: Optional[str] = Field(None, max_length=255)
    name_ar: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    description_sale: Optional[str] = None
    description_purchase: Optional[str] = None
    status: Optional[str] = None
    barcode: Optional[str] = Field(None, max_length=50)
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    
    uom_id: Optional[UUID] = None
    uom_po_id: Optional[UUID] = None
    uom_so_id: Optional[UUID] = None
    
    cost_price: Optional[Decimal] = Field(None, ge=0)
    sale_price: Optional[Decimal] = Field(None, ge=0)
    list_price: Optional[Decimal] = Field(None, ge=0)
    
    track_inventory: Optional[bool] = None
    auto_reorder: Optional[bool] = None
    reorder_point: Optional[Decimal] = Field(None, ge=0)
    reorder_quantity: Optional[Decimal] = Field(None, ge=0)
    
    purchasable: Optional[bool] = None
    saleable: Optional[bool] = None
    available_for_pos: Optional[bool] = None
    
    weight: Optional[Decimal] = Field(None, ge=0)
    volume: Optional[Decimal] = Field(None, ge=0)
    length: Optional[Decimal] = Field(None, ge=0)
    width: Optional[Decimal] = Field(None, ge=0)
    height: Optional[Decimal] = Field(None, ge=0)
    
    image_url: Optional[str] = Field(None, max_length=500)
    images: Optional[List[str]] = None
    
    income_account_id: Optional[UUID] = None
    expense_account_id: Optional[UUID] = None
    asset_account_id: Optional[UUID] = None
    
    custom_fields: Optional[Dict[str, Any]] = None


class ProductResponse(ProductBriefResponse):
    """Full product response."""
    name_ar: Optional[str] = None
    description: Optional[str] = None
    description_sale: Optional[str] = None
    description_purchase: Optional[str] = None
    barcode_type: Optional[str] = None
    internal_reference: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    
    category_id: Optional[UUID] = None
    category: Optional[ProductCategoryBriefResponse] = None
    brand_id: Optional[UUID] = None
    tags: List[str] = []
    
    is_variant: bool = False
    template_id: Optional[UUID] = None
    variant_attributes: Dict[str, Any] = {}
    
    uom_id: UUID
    uom_po_id: Optional[UUID] = None
    uom_so_id: Optional[UUID] = None
    uom: Optional[UOMResponse] = None
    
    list_price: Decimal
    min_sale_price: Optional[Decimal] = None
    currency_id: Optional[UUID] = None
    
    is_stockable: bool
    valuation_method: str
    track_inventory: bool
    allow_negative_stock: bool
    auto_reorder: bool
    reorder_point: Decimal
    reorder_quantity: Decimal
    min_quantity: Decimal
    max_quantity: Decimal
    
    shelf_life_days: Optional[int] = None
    track_expiration: bool
    track_serial: bool
    track_lot: bool
    
    weight: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    length: Optional[Decimal] = None
    width: Optional[Decimal] = None
    height: Optional[Decimal] = None
    
    purchasable: bool
    saleable: bool
    available_for_pos: bool
    available_online: bool
    requires_shipping: bool
    
    preferred_supplier_id: Optional[UUID] = None
    supplier_code: Optional[str] = None
    lead_time_days: int
    
    image_url: Optional[str] = None
    images: List[str] = []
    
    income_account_id: Optional[UUID] = None
    expense_account_id: Optional[UUID] = None
    asset_account_id: Optional[UUID] = None
    
    quantity_available: Decimal
    quantity_reserved: Decimal
    quantity_incoming: Decimal
    quantity_outgoing: Decimal
    quantity_virtual: Decimal
    
    average_cost: Decimal
    standard_cost: Decimal
    last_purchase_price: Optional[Decimal] = None
    last_purchase_date: Optional[datetime] = None
    last_sale_date: Optional[datetime] = None
    
    total_sold: Decimal
    total_purchased: Decimal
    
    is_low_stock: bool
    is_out_of_stock: bool
    profit_margin: Decimal
    
    custom_fields: Dict[str, Any] = {}
    
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    """Paginated product list response."""
    items: List[ProductResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ProductSearchParams(BaseModel):
    """Product search parameters."""
    query: Optional[str] = None
    category_id: Optional[UUID] = None
    product_type: Optional[str] = None
    status: Optional[str] = None
    is_stockable: Optional[bool] = None
    saleable: Optional[bool] = None
    purchasable: Optional[bool] = None
    available_for_pos: Optional[bool] = None
    low_stock: Optional[bool] = None
    out_of_stock: Optional[bool] = None
    tags: Optional[List[str]] = None
    supplier_id: Optional[UUID] = None


# ========================================
# Warehouse Schemas
# ========================================

class WarehouseBriefResponse(BaseSchema):
    """Brief warehouse response."""
    id: UUID
    code: str
    name: str
    is_active: bool
    is_default: bool


class WarehouseCreate(BaseModel):
    """Schema for creating a warehouse."""
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    name_ar: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    
    is_active: bool = Field(default=True)
    is_default: bool = Field(default=False)
    allow_negative_stock: bool = Field(default=False)
    is_shop: bool = Field(default=False)
    
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    
    contact_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    
    inventory_account_id: Optional[UUID] = None


class WarehouseUpdate(BaseModel):
    """Schema for updating a warehouse."""
    name: Optional[str] = Field(None, max_length=255)
    name_ar: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    allow_negative_stock: Optional[bool] = None
    is_shop: Optional[bool] = None
    
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class WarehouseResponse(WarehouseBriefResponse):
    """Full warehouse response."""
    name_ar: Optional[str] = None
    description: Optional[str] = None
    allow_negative_stock: bool
    is_shop: bool
    
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    
    inventory_account_id: Optional[UUID] = None
    
    created_at: datetime
    updated_at: datetime
    
    locations: List["StockLocationResponse"] = []


class WarehouseListResponse(BaseModel):
    """Warehouse list response."""
    items: List[WarehouseResponse]
    total: int


# ========================================
# Stock Location Schemas
# ========================================

class StockLocationCreate(BaseModel):
    """Schema for creating a stock location."""
    warehouse_id: UUID
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    location_type: str = Field(default="internal")
    parent_id: Optional[UUID] = None
    
    corridor: Optional[str] = Field(None, max_length=20)
    row: Optional[str] = Field(None, max_length=20)
    shelf: Optional[str] = Field(None, max_length=20)
    bin: Optional[str] = Field(None, max_length=20)
    
    max_capacity: Optional[Decimal] = Field(None, ge=0)
    is_active: bool = Field(default=True)
    
    @field_validator('location_type')
    @classmethod
    def validate_location_type(cls, v: str) -> str:
        allowed = ['internal', 'input', 'output', 'inventory_loss']
        if v.lower() not in allowed:
            raise ValueError(f'Location type must be one of: {allowed}')
        return v.lower()


class StockLocationResponse(BaseSchema):
    """Stock location response."""
    id: UUID
    warehouse_id: UUID
    code: str
    name: str
    location_type: str
    parent_id: Optional[UUID] = None
    
    corridor: Optional[str] = None
    row: Optional[str] = None
    shelf: Optional[str] = None
    bin: Optional[str] = None
    
    max_capacity: Optional[Decimal] = None
    is_active: bool
    
    created_at: datetime
    updated_at: datetime


# ========================================
# Stock Quantity Schemas
# ========================================

class StockQuantityResponse(BaseSchema):
    """Stock quantity response."""
    id: UUID
    product_id: UUID
    product: Optional[ProductBriefResponse] = None
    warehouse_id: UUID
    warehouse: Optional[WarehouseBriefResponse] = None
    location_id: Optional[UUID] = None
    
    quantity: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal
    quantity_incoming: Decimal
    quantity_outgoing: Decimal
    
    value: Decimal
    average_cost: Decimal
    
    lot_id: Optional[UUID] = None
    serial_number: Optional[str] = None
    expiration_date: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime


class StockQuantitySearchParams(BaseModel):
    """Stock quantity search parameters."""
    product_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    location_id: Optional[UUID] = None
    low_stock: Optional[bool] = None
    out_of_stock: Optional[bool] = None
    expiring_before: Optional[Date] = None


class StockOnHandReport(BaseModel):
    """Stock on hand report item."""
    product_id: UUID
    product_sku: str
    product_name: str
    warehouse_id: UUID
    warehouse_name: str
    location_id: Optional[UUID] = None
    location_name: Optional[str] = None
    
    quantity: Decimal
    value: Decimal
    average_cost: Decimal
    
    lot_number: Optional[str] = None
    serial_number: Optional[str] = None
    expiration_date: Optional[Date] = None


# ========================================
# Stock Move Schemas
# ========================================

class StockMoveCreate(BaseModel):
    """Schema for creating a stock move."""
    product_id: UUID = Field(..., description="Product ID")
    quantity: Decimal = Field(..., gt=0, description="Move quantity")
    uom_id: UUID = Field(..., description="Unit of measure")
    
    location_from_id: Optional[UUID] = Field(None, description="Source location")
    location_to_id: Optional[UUID] = Field(None, description="Destination location")
    warehouse_from_id: Optional[UUID] = Field(None, description="Source warehouse")
    warehouse_to_id: Optional[UUID] = Field(None, description="Destination warehouse")
    
    move_type: str = Field(..., description="Move type")
    date: Date = Field(..., description="Move date")
    date_expected: Optional[Date] = Field(None, description="Expected date")
    
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)
    
    reference: Optional[str] = Field(None, max_length=100)
    reference_id: Optional[UUID] = None
    reference_type: Optional[str] = Field(None, max_length=50)
    
    partner_id: Optional[UUID] = None
    partner_type: Optional[str] = None
    
    lot_id: Optional[UUID] = None
    serial_number: Optional[str] = Field(None, max_length=100)
    expiration_date: Optional[datetime] = None
    
    reason: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_locations(self):
        if not self.location_from_id and not self.location_to_id:
            raise ValueError('At least one location must be specified')
        return self
    
    @field_validator('move_type')
    @classmethod
    def validate_move_type(cls, v: str) -> str:
        allowed = ['in', 'out', 'internal', 'adjustment', 'return_in', 'return_out', 'production', 'loss']
        if v.lower() not in allowed:
            raise ValueError(f'Move type must be one of: {allowed}')
        return v.lower()


class StockMoveUpdate(BaseModel):
    """Schema for updating a stock move."""
    quantity: Optional[Decimal] = Field(None, gt=0)
    date: Optional[Date] = None
    date_expected: Optional[Date] = None
    unit_cost: Optional[Decimal] = Field(None, ge=0)
    reason: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None


class StockMoveResponse(BaseSchema):
    """Stock move response."""
    id: UUID
    number: str
    reference: Optional[str] = None
    reference_id: Optional[UUID] = None
    reference_type: Optional[str] = None
    
    product_id: UUID
    product: Optional[ProductBriefResponse] = None
    
    quantity: Decimal
    quantity_done: Decimal
    uom_id: UUID
    uom: Optional[UOMResponse] = None
    
    location_from_id: Optional[UUID] = None
    location_from: Optional[StockLocationResponse] = None
    location_to_id: Optional[UUID] = None
    location_to: Optional[StockLocationResponse] = None
    warehouse_from_id: Optional[UUID] = None
    warehouse_to_id: Optional[UUID] = None
    
    move_type: str
    state: str
    
    date: Date
    date_expected: Optional[Date] = None
    date_done: Optional[datetime] = None
    
    unit_cost: Decimal
    total_cost: Decimal
    
    partner_id: Optional[UUID] = None
    partner_type: Optional[str] = None
    
    lot_id: Optional[UUID] = None
    serial_number: Optional[str] = None
    expiration_date: Optional[datetime] = None
    
    reason: Optional[str] = None
    notes: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime


class StockMoveListResponse(BaseModel):
    """Stock move list response."""
    items: List[StockMoveResponse]
    total: int
    page: int
    page_size: int
    pages: int


class StockMoveConfirmRequest(BaseModel):
    """Request to confirm a stock move."""
    quantity_done: Optional[Decimal] = Field(None, ge=0, description="Actual quantity moved")


class StockMoveCancelRequest(BaseModel):
    """Request to cancel a stock move."""
    reason: Optional[str] = Field(None, max_length=255)


# ========================================
# Inventory Adjustment Schemas
# ========================================

class AdjustmentLineCreate(BaseModel):
    """Schema for creating an adjustment line."""
    product_id: UUID
    actual_qty: Decimal = Field(..., ge=0, description="Counted quantity")
    expected_qty: Optional[Decimal] = Field(None, ge=0, description="Expected quantity (auto-filled)")
    unit_cost: Optional[Decimal] = Field(None, ge=0)
    lot_id: Optional[UUID] = None
    serial_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class AdjustmentLineResponse(BaseSchema):
    """Adjustment line response."""
    id: UUID
    adjustment_id: UUID
    product_id: UUID
    product: Optional[ProductBriefResponse] = None
    
    expected_qty: Decimal
    actual_qty: Decimal
    difference: Decimal
    
    unit_cost: Decimal
    value_difference: Decimal
    
    lot_id: Optional[UUID] = None
    serial_number: Optional[str] = None
    notes: Optional[str] = None


class InventoryAdjustmentCreate(BaseModel):
    """Schema for creating an inventory adjustment."""
    location_id: UUID = Field(..., description="Location to adjust")
    warehouse_id: UUID = Field(..., description="Warehouse")
    date: Date = Field(..., description="Adjustment date")
    reason: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    lines: List[AdjustmentLineCreate] = Field(..., min_length=1)


class InventoryAdjustmentResponse(BaseSchema):
    """Inventory adjustment response."""
    id: UUID
    number: str
    date: Date
    
    location_id: UUID
    location: Optional[StockLocationResponse] = None
    warehouse_id: UUID
    
    reason: Optional[str] = None
    state: str
    
    total_adjustments: int
    total_value: Decimal
    
    posted_at: Optional[datetime] = None
    posted_by_id: Optional[UUID] = None
    
    notes: Optional[str] = None
    
    lines: List[AdjustmentLineResponse] = []
    
    created_at: datetime
    updated_at: datetime


class InventoryAdjustmentListResponse(BaseModel):
    """Inventory adjustment list response."""
    items: List[InventoryAdjustmentResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ========================================
# Stock Valuation Schemas
# ========================================

class StockValuationResponse(BaseSchema):
    """Stock valuation response."""
    product_id: UUID
    product_sku: str
    product_name: str
    
    quantity: Decimal
    average_cost: Decimal
    total_value: Decimal
    
    last_purchase_price: Optional[Decimal] = None
    last_purchase_date: Optional[datetime] = None
    
    valuation_method: str


class StockValuationReport(BaseModel):
    """Stock valuation report."""
    date: Date
    warehouse_id: Optional[UUID] = None
    warehouse_name: Optional[str] = None
    
    total_value: Decimal
    total_items: int
    items: List[StockValuationResponse]


# Update forward references
WarehouseResponse.model_rebuild()
