"""
Nexus ERP - Inventory Service
==============================

Business logic for inventory management including:
- Stock movements and updates
- Inventory valuation (FIFO/Average)
- Stock adjustments
- Multi-warehouse operations
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
import logging

from app.models.inventory import (
    Product, Warehouse, StockLocation, StockQuantity, StockMove,
    StockMoveType, StockMoveState, InventoryAdjustment, AdjustmentLine,
    AdjustmentState, UnitOfMeasure, StockLot, StockValuation, ValuationMethod
)
from app.models.accounting import Partner

logger = logging.getLogger(__name__)


class InventoryService:
    """
    Inventory Service
    
    Handles all inventory-related business logic.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _require_tenant_record(self, model, record_id, tenant_id, label: str):
        """Load a tenant-owned record and reject cross-tenant references."""
        if record_id is None:
            return None
        record = await self.db.scalar(
            select(model).where(
                model.id == record_id,
                model.tenant_id == tenant_id,
                model.is_deleted == False
            )
        )
        if record is None:
            raise ValueError(f"{label} not found")
        return record

    # ========================================
    # Stock Quantity Operations
    # ========================================
    
    async def get_stock_quantity(
        self,
        product_id: UUID,
        warehouse_id: Optional[UUID] = None,
        location_id: Optional[UUID] = None,
        tenant_id: UUID = None
    ) -> Optional[StockQuantity]:
        """
        Get stock quantity for a product in a specific location.
        
        Args:
            product_id: Product ID
            warehouse_id: Warehouse ID (optional filter)
            location_id: Location ID (optional filter)
            
        Returns:
            StockQuantity record or None
        """
        if tenant_id is None:
            raise ValueError("tenant_id is required for stock quantity lookup")

        query = select(StockQuantity).where(
            StockQuantity.product_id == product_id,
            StockQuantity.tenant_id == tenant_id,
            StockQuantity.is_deleted == False
        )
        
        if location_id:
            query = query.where(StockQuantity.location_id == location_id)
        elif warehouse_id:
            query = query.where(StockQuantity.warehouse_id == warehouse_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_or_create_stock_quantity(
        self,
        product_id: UUID,
        warehouse_id: UUID,
        location_id: Optional[UUID] = None,
        tenant_id: UUID = None
    ) -> StockQuantity:
        """
        Get existing or create new stock quantity record.
        """
        if tenant_id is None:
            raise ValueError("tenant_id is required for stock quantity creation")
        stock_qty = await self.get_stock_quantity(
            product_id, warehouse_id, location_id, tenant_id
        )
        
        if not stock_qty:
            stock_qty = StockQuantity(
                product_id=product_id,
                warehouse_id=warehouse_id,
                location_id=location_id,
                tenant_id=tenant_id,
                quantity=Decimal("0"),
                quantity_reserved=Decimal("0"),
                quantity_available=Decimal("0"),
                value=Decimal("0")
            )
            self.db.add(stock_qty)
            await self.db.flush()
        
        return stock_qty
    
    async def get_product_stock(
        self,
        product_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """
        Get aggregated stock information for a product.
        
        Args:
            product_id: Product ID
            tenant_id: Tenant ID
            
        Returns:
            Dictionary with stock information
        """
        # Get all stock quantities for this product
        result = await self.db.execute(
            select(StockQuantity).where(
                StockQuantity.product_id == product_id,
                StockQuantity.tenant_id == tenant_id,
                StockQuantity.is_deleted == False
            )
        )
        stock_records = result.scalars().all()
        
        total_qty = sum(sq.quantity for sq in stock_records)
        total_reserved = sum(sq.quantity_reserved for sq in stock_records)
        total_available = sum(sq.quantity_available for sq in stock_records)
        total_value = sum(sq.value for sq in stock_records)
        
        return {
            "product_id": product_id,
            "quantity_on_hand": total_qty,
            "quantity_reserved": total_reserved,
            "quantity_available": total_available,
            "total_value": total_value,
            "warehouses": [
                {
                    "warehouse_id": sq.warehouse_id,
                    "location_id": sq.location_id,
                    "quantity": sq.quantity,
                    "value": sq.value
                }
                for sq in stock_records
            ]
        }
    
    # ========================================
    # Stock Movement Operations
    # ========================================
    
    async def create_stock_move(
        self,
        product_id: UUID,
        quantity: Decimal,
        uom_id: UUID,
        move_type: StockMoveType,
        warehouse_from_id: Optional[UUID] = None,
        warehouse_to_id: Optional[UUID] = None,
        location_from_id: Optional[UUID] = None,
        location_to_id: Optional[UUID] = None,
        unit_cost: Decimal = Decimal("0"),
        move_date: Optional[date] = None,
        reference: Optional[str] = None,
        reference_id: Optional[UUID] = None,
        reference_type: Optional[str] = None,
        partner_id: Optional[UUID] = None,
        lot_id: Optional[UUID] = None,
        serial_number: Optional[str] = None,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
        tenant_id: UUID = None,
        created_by_id: Optional[UUID] = None,
        auto_confirm: bool = False
    ) -> StockMove:
        """
        Create a new stock movement.
        
        Args:
            product_id: Product ID
            quantity: Quantity to move
            uom_id: Unit of measure ID
            move_type: Type of movement
            warehouse_from_id: Source warehouse
            warehouse_to_id: Destination warehouse
            location_from_id: Source location
            location_to_id: Destination location
            unit_cost: Unit cost for valuation
            move_date: Date of movement
            reference: Reference document number
            auto_confirm: Whether to automatically confirm the move
            
        Returns:
            Created StockMove record
        """
        # Generate move number
        move_number = await self._generate_move_number(move_type, tenant_id)
        
        # Resolve the product inside the caller's tenant only.
        if tenant_id is None:
            raise ValueError("tenant_id is required to create a stock move")
        product = await self._require_tenant_record(Product, product_id, tenant_id, "Product")
        await self._require_tenant_record(Warehouse, warehouse_from_id, tenant_id, "Source warehouse")
        await self._require_tenant_record(Warehouse, warehouse_to_id, tenant_id, "Destination warehouse")
        await self._require_tenant_record(StockLocation, location_from_id, tenant_id, "Source location")
        await self._require_tenant_record(StockLocation, location_to_id, tenant_id, "Destination location")
        await self._require_tenant_record(Partner, partner_id, tenant_id, "Partner")
        await self._require_tenant_record(StockLot, lot_id, tenant_id, "Stock lot")
        uom = await self.db.get(UnitOfMeasure, uom_id)
        if uom is None or uom.is_deleted:
            raise ValueError("Unit of measure not found")
        
        # Use product cost if not provided
        if unit_cost == Decimal("0"):
            unit_cost = product.average_cost or product.cost_price
        
        # Create stock move
        stock_move = StockMove(
            number=move_number,
            product_id=product_id,
            quantity=quantity,
            uom_id=uom_id,
            move_type=move_type,
            warehouse_from_id=warehouse_from_id,
            warehouse_to_id=warehouse_to_id,
            location_from_id=location_from_id,
            location_to_id=location_to_id,
            unit_cost=unit_cost,
            total_cost=unit_cost * quantity,
            date=move_date or date.today(),
            reference=reference,
            reference_id=reference_id,
            reference_type=reference_type,
            partner_id=partner_id,
            lot_id=lot_id,
            serial_number=serial_number,
            reason=reason,
            notes=notes,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            state=StockMoveState.DRAFT
        )
        
        self.db.add(stock_move)
        await self.db.flush()
        
        if auto_confirm:
            await self.confirm_stock_move(stock_move.id, tenant_id, quantity)
        
        return stock_move
    
    async def confirm_stock_move(
        self,
        move_id: UUID,
        tenant_id: UUID,
        quantity_done: Optional[Decimal] = None
    ) -> StockMove:
        """
        Confirm a stock movement and update stock quantities.
        
        Args:
            move_id: Stock move ID
            quantity_done: Actual quantity moved (defaults to planned quantity)
            
        Returns:
            Updated StockMove record
        """
        stock_move = await self.db.scalar(
            select(StockMove).where(
                StockMove.id == move_id,
                StockMove.tenant_id == tenant_id,
                StockMove.is_deleted == False
            )
        )
        if not stock_move:
            raise ValueError(f"Stock move {move_id} not found")
        
        if stock_move.state != StockMoveState.DRAFT:
            raise ValueError(f"Cannot confirm move in state {stock_move.state}")
        
        # Set actual quantity
        if quantity_done is None:
            quantity_done = stock_move.quantity
        
        stock_move.quantity_done = quantity_done
        stock_move.state = StockMoveState.CONFIRMED
        
        await self.db.flush()
        return stock_move
    
    async def process_stock_move(self, move_id: UUID, tenant_id: UUID) -> StockMove:
        """
        Process a confirmed stock movement.
        
        Updates stock quantities in source and destination locations.
        
        Args:
            move_id: Stock move ID
            
        Returns:
            Processed StockMove record
        """
        stock_move = await self.db.scalar(
            select(StockMove).where(
                StockMove.id == move_id,
                StockMove.tenant_id == tenant_id,
                StockMove.is_deleted == False
            )
        )
        if not stock_move:
            raise ValueError(f"Stock move {move_id} not found")
        
        if stock_move.state != StockMoveState.CONFIRMED:
            raise ValueError(f"Move must be confirmed before processing")
        
        quantity = stock_move.quantity_done
        
        # Update source location (deduct)
        if stock_move.location_from_id:
            source_qty = await self.get_stock_quantity(
                stock_move.product_id,
                stock_move.warehouse_from_id,
                stock_move.location_from_id,
                tenant_id
            )
            if source_qty:
                if source_qty.quantity < quantity and not source_qty.warehouse.allow_negative_stock:
                    raise ValueError(
                        f"Insufficient stock at source. Available: {source_qty.quantity}"
                    )
                source_qty.quantity -= quantity
                source_qty.quantity_available = source_qty.quantity - source_qty.quantity_reserved
                source_qty.value = source_qty.quantity * stock_move.unit_cost
        
        # Update destination location (add)
        if stock_move.location_to_id:
            dest_qty = await self.get_or_create_stock_quantity(
                stock_move.product_id,
                stock_move.warehouse_to_id,
                stock_move.location_to_id,
                tenant_id
            )
            dest_qty.quantity += quantity
            dest_qty.quantity_available = dest_qty.quantity - dest_qty.quantity_reserved
            dest_qty.value = dest_qty.quantity * stock_move.unit_cost
            dest_qty.average_cost = stock_move.unit_cost
        
        # Update product aggregates
        await self._update_product_quantities(stock_move.product_id, tenant_id)
        
        # Update valuation
        await self._create_valuation_record(stock_move)
        
        # Mark as done
        stock_move.state = StockMoveState.DONE
        stock_move.date_done = datetime.utcnow()
        
        await self.db.flush()
        return stock_move
    
    async def cancel_stock_move(
        self,
        move_id: UUID,
        tenant_id: UUID,
        reason: Optional[str] = None
    ) -> StockMove:
        """
        Cancel a stock movement.
        
        If the move was already processed, creates reversal moves.
        
        Args:
            move_id: Stock move ID
            reason: Cancellation reason
            
        Returns:
            Cancelled StockMove record
        """
        stock_move = await self.db.scalar(
            select(StockMove).where(
                StockMove.id == move_id,
                StockMove.tenant_id == tenant_id,
                StockMove.is_deleted == False
            )
        )
        if not stock_move:
            raise ValueError(f"Stock move {move_id} not found")
        
        if stock_move.state == StockMoveState.CANCELLED:
            raise ValueError("Move is already cancelled")
        
        if stock_move.state == StockMoveState.DONE:
            # Create reversal move
            await self.create_stock_move(
                product_id=stock_move.product_id,
                quantity=stock_move.quantity_done,
                uom_id=stock_move.uom_id,
                move_type=self._get_reversal_move_type(stock_move.move_type),
                warehouse_from_id=stock_move.warehouse_to_id,
                warehouse_to_id=stock_move.warehouse_from_id,
                location_from_id=stock_move.location_to_id,
                location_to_id=stock_move.location_from_id,
                unit_cost=stock_move.unit_cost,
                reference=f"REV-{stock_move.number}",
                reason=f"Reversal of {stock_move.number}: {reason or ''}",
                tenant_id=stock_move.tenant_id,
                auto_confirm=True
            )
        
        stock_move.state = StockMoveState.CANCELLED
        stock_move.reason = reason or stock_move.reason
        
        await self.db.flush()
        return stock_move
    
    # ========================================
    # Inventory Adjustment Operations
    # ========================================
    
    async def create_inventory_adjustment(
        self,
        location_id: UUID,
        warehouse_id: UUID,
        adjustment_date: date,
        lines: List[Dict[str, Any]],
        reason: Optional[str] = None,
        notes: Optional[str] = None,
        tenant_id: UUID = None,
        created_by_id: Optional[UUID] = None
    ) -> InventoryAdjustment:
        """
        Create an inventory adjustment (stock count).
        
        Args:
            location_id: Location being counted
            warehouse_id: Warehouse
            adjustment_date: Date of adjustment
            lines: List of adjustment lines with product_id and actual_qty
            reason: Adjustment reason
            notes: Additional notes
            
        Returns:
            Created InventoryAdjustment record
        """
        # Generate adjustment number
        adj_number = await self._generate_adjustment_number(tenant_id)
        
        if tenant_id is None:
            raise ValueError("tenant_id is required to create an inventory adjustment")
        await self._require_tenant_record(Warehouse, warehouse_id, tenant_id, "Warehouse")
        await self._require_tenant_record(StockLocation, location_id, tenant_id, "Stock location")

        adjustment = InventoryAdjustment(
            number=adj_number,
            date=adjustment_date,
            location_id=location_id,
            warehouse_id=warehouse_id,
            reason=reason,
            notes=notes,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            state=AdjustmentState.DRAFT
        )
        
        self.db.add(adjustment)
        await self.db.flush()
        
        total_value = Decimal("0")
        
        # Create adjustment lines
        for line_data in lines:
            product_id = line_data["product_id"]
            actual_qty = line_data["actual_qty"]
            
            # Get expected quantity
            stock_qty = await self.get_stock_quantity(
                product_id, warehouse_id, location_id, tenant_id
            )
            expected_qty = stock_qty.quantity if stock_qty else Decimal("0")
            
            # Get product cost
            product = await self.db.scalar(
                select(Product).where(
                    Product.id == product_id,
                    Product.tenant_id == tenant_id,
                    Product.is_deleted == False
                )
            )
            if product is None:
                raise ValueError(f"Product {product_id} not found")
            unit_cost = product.average_cost or Decimal("0")
            
            difference = actual_qty - expected_qty
            value_diff = difference * unit_cost
            
            line = AdjustmentLine(
                adjustment_id=adjustment.id,
                product_id=product_id,
                expected_qty=expected_qty,
                actual_qty=actual_qty,
                difference=difference,
                unit_cost=unit_cost,
                value_difference=value_diff,
                lot_id=line_data.get("lot_id"),
                serial_number=line_data.get("serial_number"),
                notes=line_data.get("notes"),
                tenant_id=tenant_id
            )
            
            self.db.add(line)
            total_value += value_diff
        
        adjustment.total_value = total_value
        adjustment.total_adjustments = len(lines)
        
        await self.db.flush()
        return adjustment
    
    async def confirm_adjustment(
        self, adjustment_id: UUID, tenant_id: UUID
    ) -> InventoryAdjustment:
        """
        Confirm an inventory adjustment and create stock moves.
        
        Args:
            adjustment_id: Adjustment ID
            
        Returns:
            Confirmed InventoryAdjustment record
        """
        adjustment = await self.db.scalar(
            select(InventoryAdjustment).where(
                InventoryAdjustment.id == adjustment_id,
                InventoryAdjustment.tenant_id == tenant_id,
                InventoryAdjustment.is_deleted == False
            )
        )
        if not adjustment:
            raise ValueError(f"Adjustment {adjustment_id} not found")
        
        if adjustment.state != AdjustmentState.DRAFT:
            raise ValueError(f"Cannot confirm adjustment in state {adjustment.state}")
        
        # Load lines
        result = await self.db.execute(
            select(AdjustmentLine).where(
                AdjustmentLine.adjustment_id == adjustment_id,
                AdjustmentLine.tenant_id == tenant_id
            )
        )
        lines = result.scalars().all()
        
        # Create stock moves for each line with difference
        for line in lines:
            if line.difference != 0:
                # Determine move type
                if line.difference > 0:
                    move_type = StockMoveType.ADJUSTMENT
                    location_to_id = adjustment.location_id
                    location_from_id = None
                else:
                    move_type = StockMoveType.ADJUSTMENT
                    location_from_id = adjustment.location_id
                    location_to_id = None
                
                # Create and process move
                move = await self.create_stock_move(
                    product_id=line.product_id,
                    quantity=abs(line.difference),
                    uom_id=(await self.db.scalar(
                        select(Product.uom_id).where(
                            Product.id == line.product_id,
                            Product.tenant_id == tenant_id,
                            Product.is_deleted == False
                        )
                    )),
                    move_type=move_type,
                    warehouse_from_id=adjustment.warehouse_id if line.difference < 0 else None,
                    warehouse_to_id=adjustment.warehouse_id if line.difference > 0 else None,
                    location_from_id=location_from_id,
                    location_to_id=location_to_id,
                    unit_cost=line.unit_cost,
                    move_date=adjustment.date,
                    reference=f"ADJ-{adjustment.number}",
                    reference_id=adjustment.id,
                    reference_type="inventory_adjustment",
                    reason=adjustment.reason,
                    tenant_id=adjustment.tenant_id,
                    auto_confirm=True
                )
                
                # Process the move
                await self.process_stock_move(move.id, tenant_id)
        
        adjustment.state = AdjustmentState.CONFIRMED
        adjustment.posted_at = datetime.utcnow()
        
        await self.db.flush()
        return adjustment
    
    # ========================================
    # Valuation Operations
    # ========================================
    
    async def calculate_average_cost(
        self,
        product_id: UUID,
        new_quantity: Decimal,
        new_cost: Decimal,
        tenant_id: UUID
    ) -> Decimal:
        """
        Calculate new average cost after a purchase.
        
        Args:
            product_id: Product ID
            new_quantity: Quantity being added
            new_cost: Unit cost of new quantity
            
        Returns:
            New average cost
        """
        product = await self._require_tenant_record(Product, product_id, tenant_id, "Product")
        
        current_qty = product.quantity_on_hand
        current_cost = product.average_cost
        
        if current_qty + new_quantity == 0:
            return current_cost
        
        # Weighted average calculation
        total_value = (current_qty * current_cost) + (new_quantity * new_cost)
        total_qty = current_qty + new_quantity
        
        new_average = total_value / total_qty if total_qty > 0 else Decimal("0")
        
        return new_average.quantize(Decimal("0.0001"))
    
    async def update_product_cost(
        self,
        product_id: UUID,
        new_cost: Decimal,
        quantity: Decimal = Decimal("1"),
        valuation_method: ValuationMethod = ValuationMethod.AVERAGE,
        tenant_id: UUID = None
    ) -> Product:
        """
        Update product cost based on valuation method.
        
        Args:
            product_id: Product ID
            new_cost: New unit cost
            quantity: Quantity at this cost
            valuation_method: Valuation method to use
            
        Returns:
            Updated Product record
        """
        if tenant_id is None:
            raise ValueError("tenant_id is required to update product cost")
        product = await self._require_tenant_record(Product, product_id, tenant_id, "Product")
        
        if valuation_method == ValuationMethod.AVERAGE:
            product.average_cost = await self.calculate_average_cost(
                product_id, quantity, new_cost, tenant_id
            )
            product.cost_price = product.average_cost
        elif valuation_method == ValuationMethod.STANDARD:
            product.standard_cost = new_cost
            product.cost_price = new_cost
        
        product.last_purchase_price = new_cost
        product.last_purchase_date = datetime.utcnow()
        
        await self.db.flush()
        return product
    
    # ========================================
    # Helper Methods
    # ========================================
    
    async def _generate_move_number(self, move_type: StockMoveType, tenant_id: UUID) -> str:
        """Generate a unique stock move number."""
        prefix_map = {
            StockMoveType.IN: "IN",
            StockMoveType.OUT: "OUT",
            StockMoveType.INTERNAL: "TRF",
            StockMoveType.ADJUSTMENT: "ADJ",
            StockMoveType.RETURN_IN: "RTI",
            StockMoveType.RETURN_OUT: "RTO",
            StockMoveType.PRODUCTION: "PRD",
            StockMoveType.LOSS: "LOS"
        }
        
        prefix = prefix_map.get(move_type, "MOV")
        
        result = await self.db.execute(
            select(func.count()).select_from(StockMove).where(
                StockMove.tenant_id == tenant_id
            )
        )
        count = result.scalar() or 0
        
        return f"{prefix}-{date.today().year}-{count + 1:06d}"
    
    async def _generate_adjustment_number(self, tenant_id: UUID) -> str:
        """Generate a unique adjustment number."""
        result = await self.db.execute(
            select(func.count()).select_from(InventoryAdjustment).where(
                InventoryAdjustment.tenant_id == tenant_id
            )
        )
        count = result.scalar() or 0
        
        return f"ADJ-{date.today().year}-{count + 1:06d}"
    
    async def _update_product_quantities(self, product_id: UUID, tenant_id: UUID):
        """Update product aggregate quantities from this tenant's stock records."""
        result = await self.db.execute(
            select(
                func.sum(StockQuantity.quantity).label("total_qty"),
                func.sum(StockQuantity.quantity_reserved).label("total_reserved"),
                func.sum(StockQuantity.value).label("total_value")
            ).where(
                StockQuantity.product_id == product_id,
                StockQuantity.tenant_id == tenant_id,
                StockQuantity.is_deleted == False
            )
        )
        
        row = result.one()
        
        product = await self.db.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
                Product.is_deleted == False
            )
        )
        if product:
            product.quantity_on_hand = row.total_qty or Decimal("0")
            product.quantity_reserved = row.total_reserved or Decimal("0")
            product.quantity_available = product.quantity_on_hand - product.quantity_reserved
            product.quantity_virtual = (
                product.quantity_on_hand + 
                product.quantity_incoming - 
                product.quantity_outgoing
            )
    
    async def _create_valuation_record(self, stock_move: StockMove):
        """Create a valuation history record."""
        valuation = StockValuation(
            product_id=stock_move.product_id,
            date=datetime.utcnow(),
            quantity_change=stock_move.quantity_done,
            cost_after=stock_move.unit_cost,
            value_change=stock_move.total_cost,
            move_id=stock_move.id,
            move_type=stock_move.move_type,
            tenant_id=stock_move.tenant_id
        )
        
        self.db.add(valuation)
    
    def _get_reversal_move_type(self, original_type: StockMoveType) -> StockMoveType:
        """Get the reversal move type for a given move type."""
        reversal_map = {
            StockMoveType.IN: StockMoveType.OUT,
            StockMoveType.OUT: StockMoveType.IN,
            StockMoveType.INTERNAL: StockMoveType.INTERNAL,
            StockMoveType.ADJUSTMENT: StockMoveType.ADJUSTMENT,
            StockMoveType.RETURN_IN: StockMoveType.RETURN_OUT,
            StockMoveType.RETURN_OUT: StockMoveType.RETURN_IN,
        }
        return reversal_map.get(original_type, StockMoveType.ADJUSTMENT)
    
    # ========================================
    # Reporting Methods
    # ========================================
    
    async def get_stock_valuation_report(
        self,
        warehouse_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        tenant_id: UUID = None
    ) -> List[Dict[str, Any]]:
        """
        Generate a stock valuation report.
        
        Args:
            warehouse_id: Filter by warehouse (optional)
            category_id: Filter by category (optional)
            tenant_id: Tenant ID
            
        Returns:
            List of valuation records
        """
        query = select(StockQuantity).options(
            selectinload(StockQuantity.product)
        ).where(
            StockQuantity.tenant_id == tenant_id,
            StockQuantity.is_deleted == False,
            StockQuantity.quantity > 0
        )
        
        if warehouse_id:
            query = query.where(StockQuantity.warehouse_id == warehouse_id)
        
        if category_id:
            query = query.join(Product).where(Product.category_id == category_id)
        
        result = await self.db.execute(query)
        stock_records = result.scalars().all()
        
        report = []
        for sq in stock_records:
            report.append({
                "product_id": sq.product_id,
                "product_sku": sq.product.sku if sq.product else None,
                "product_name": sq.product.name if sq.product else None,
                "warehouse_id": sq.warehouse_id,
                "location_id": sq.location_id,
                "quantity": sq.quantity,
                "average_cost": sq.average_cost,
                "value": sq.value
            })
        
        return report
    
    async def get_low_stock_products(
        self,
        tenant_id: UUID,
        warehouse_id: Optional[UUID] = None
    ) -> List[Product]:
        """
        Get products below reorder point.
        
        Args:
            tenant_id: Tenant ID
            warehouse_id: Filter by warehouse (optional)
            
        Returns:
            List of products with low stock
        """
        query = select(Product).where(
            Product.tenant_id == tenant_id,
            Product.is_deleted == False,
            Product.is_stockable == True,
            Product.quantity_on_hand <= Product.reorder_point,
            Product.reorder_point > 0
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
