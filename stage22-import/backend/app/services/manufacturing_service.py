"""
Nexus ERP - Manufacturing Service
==================================

Business logic for the Manufacturing (MRP) module including:
- Bill of Materials management
- Work Center management
- Manufacturing Order processing
- Production planning
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import logging

from app.models.manufacturing import (
    BillOfMaterial, BOMLine, BOMOperation, BOMType, BOMState,
    WorkCenter, WorkCenterState,
    Routing, RoutingStep,
    ManufacturingOrder, MOLine, MOFinish, MOOperation, MOState, MOOperationState,
    ProductionPlan, ProductionPlanLine
)
from app.models.inventory import Product, StockMove, StockMoveType, StockMoveState, StockQuantity, StockLocation
from app.models.accounting import Account
from app.services.integration_service import IntegrationService
from app.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class ManufacturingService:
    """
    Manufacturing Service
    
    Handles all manufacturing-related business logic.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.integration_svc = IntegrationService(db)
        self.inventory_svc = InventoryService(db)

    async def _require_tenant_record(self, model, record_id, tenant_id: UUID, label: str):
        """Load a tenant-owned record; reject missing, deleted, or cross-tenant IDs."""
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
    # Bill of Materials
    # ========================================
    
    async def create_bom(
        self,
        tenant_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> BillOfMaterial:
        """Create a new Bill of Material."""
        # Validate every tenant-owned reference before creating the BOM.
        await self._require_tenant_record(Product, data.get("product_id"), tenant_id, "BOM product")
        await self._require_tenant_record(Routing, data.get("routing_id"), tenant_id, "Routing")
        for line_data in data.get("lines", []):
            await self._require_tenant_record(Product, line_data.get("product_id"), tenant_id, "BOM component")
        for op_data in data.get("operations", []):
            await self._require_tenant_record(WorkCenter, op_data.get("workcenter_id"), tenant_id, "Work center")

        # Generate BOM code
        code = await self._generate_bom_code(tenant_id)
        
        bom = BillOfMaterial(
            tenant_id=tenant_id,
            code=data.get("code", code),
            name=data["name"],
            product_id=data["product_id"],
            product_qty=Decimal(str(data.get("product_qty", 1))),
            product_uom_id=data.get("product_uom_id"),
            bom_type=BOMType(data.get("bom_type", "manufacture")),
            state=BOMState.DRAFT,
            version=1,
            routing_id=data.get("routing_id"),
            notes=data.get("notes"),
            created_by_id=user_id
        )
        
        self.db.add(bom)
        await self.db.flush()
        
        # Create lines
        for line_data in data.get("lines", []):
            line = BOMLine(
                tenant_id=tenant_id,
                bom_id=bom.id,
                product_id=line_data["product_id"],
                product_qty=Decimal(str(line_data["quantity"])),
                product_uom_id=line_data.get("uom_id"),
                scrap_percent=Decimal(str(line_data.get("scrap_percent", 0))),
                unit_cost=Decimal(str(line_data.get("unit_cost", 0))),
                operation_id=line_data.get("operation_id"),
                notes=line_data.get("notes")
            )
            line.calculate_total()
            self.db.add(line)
        
        # Create operations
        for op_data in data.get("operations", []):
            operation = BOMOperation(
                tenant_id=tenant_id,
                bom_id=bom.id,
                sequence=op_data.get("sequence", 10),
                name=op_data["name"],
                workcenter_id=op_data.get("workcenter_id"),
                duration_expected=Decimal(str(op_data.get("duration", 0))),
                duration_per_unit=Decimal(str(op_data.get("duration_per_unit", 0))),
                labor_cost_per_hour=Decimal(str(op_data.get("labor_cost", 0))),
                machine_cost_per_hour=Decimal(str(op_data.get("machine_cost", 0))),
                description=op_data.get("description")
            )
            self.db.add(operation)
        
        # Calculate costs
        await self.db.flush()
        bom.calculate_costs()
        
        await self.db.commit()
        await self.db.refresh(bom)
        
        return bom
    
    async def update_bom(
        self,
        bom_id: UUID,
        tenant_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> BillOfMaterial:
        """Update an existing BOM."""
        bom = await self._get_bom(bom_id, tenant_id)
        
        # Validate tenant-owned references before updating.
        if "routing_id" in data:
            await self._require_tenant_record(Routing, data["routing_id"], tenant_id, "Routing")
        if "lines" in data:
            for line_data in data["lines"]:
                await self._require_tenant_record(Product, line_data.get("product_id"), tenant_id, "BOM component")

        # Update fields
        for field in ["name", "product_qty", "product_uom_id", "routing_id", "notes"]:
            if field in data:
                setattr(bom, field, data[field])
        
        # Update lines if provided
        if "lines" in data:
            # Remove existing lines
            for line in bom.lines:
                await self.db.delete(line)
            
            # Add new lines
            for line_data in data["lines"]:
                line = BOMLine(
                    tenant_id=tenant_id,
                    bom_id=bom.id,
                    product_id=line_data["product_id"],
                    product_qty=Decimal(str(line_data["quantity"])),
                    scrap_percent=Decimal(str(line_data.get("scrap_percent", 0))),
                    unit_cost=Decimal(str(line_data.get("unit_cost", 0)))
                )
                line.calculate_total()
                self.db.add(line)
        
        await self.db.flush()
        bom.calculate_costs()
        
        # Increment version
        bom.version += 1
        
        await self.db.commit()
        return bom
    
    async def activate_bom(
        self,
        bom_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> BillOfMaterial:
        """Activate a BOM for production."""
        bom = await self._get_bom(bom_id, tenant_id)
        
        if not bom.lines:
            raise ValueError("Cannot activate BOM without components")
        
        bom.state = BOMState.ACTIVE
        bom.active_date = date.today()
        
        await self.db.commit()
        return bom
    
    # ========================================
    # Work Center
    # ========================================
    
    async def create_workcenter(
        self,
        tenant_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> WorkCenter:
        """Create a new work center."""
        await self._require_tenant_record(StockLocation, data.get("location_id"), tenant_id, "Work center location")
        wc = WorkCenter(
            tenant_id=tenant_id,
            code=data["code"],
            name=data["name"],
            capacity_per_hour=Decimal(str(data.get("capacity_per_hour", 1))),
            efficiency=Decimal(str(data.get("efficiency", 100))),
            cost_per_hour=Decimal(str(data.get("cost_per_hour", 0))),
            labor_cost_per_hour=Decimal(str(data.get("labor_cost_per_hour", 0))),
            machine_cost_per_hour=Decimal(str(data.get("machine_cost_per_hour", 0))),
            state=WorkCenterState(data.get("state", "available")),
            available_from=data.get("available_from"),
            available_to=data.get("available_to"),
            working_days=data.get("working_days", ["mon", "tue", "wed", "thu", "fri"]),
            location_id=data.get("location_id"),
            notes=data.get("notes"),
            created_by_id=user_id
        )
        
        self.db.add(wc)
        await self.db.commit()
        await self.db.refresh(wc)
        
        return wc
    
    async def get_workcenter_availability(
        self,
        workcenter_id: UUID,
        from_date: date,
        to_date: date,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Get work center availability and scheduled work."""
        wc = await self._require_tenant_record(WorkCenter, workcenter_id, tenant_id, "Work center")
        
        # Get scheduled operations
        result = await self.db.execute(
            select(MOOperation)
            .join(ManufacturingOrder)
            .where(
                ManufacturingOrder.tenant_id == tenant_id,
                MOOperation.workcenter_id == workcenter_id,
                MOOperation.state.in_(["pending", "ready", "in_progress"]),
                ManufacturingOrder.planned_date >= from_date,
                ManufacturingOrder.planned_date <= to_date
            )
        )
        
        scheduled = result.scalars().all()
        
        total_minutes = sum(float(op.duration_expected) for op in scheduled)
        capacity_per_day = float(wc.capacity_per_hour) * 8  # 8-hour workday
        
        return {
            "workcenter": {"code": wc.code, "name": wc.name},
            "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
            "total_scheduled_minutes": total_minutes,
            "scheduled_operations": [
                {
                    "mo_number": op.mo.number if op.mo else None,
                    "operation": op.name,
                    "duration": float(op.duration_expected),
                    "state": op.state.value
                }
                for op in scheduled
            ],
            "utilization_percent": min(100, (total_minutes / capacity_per_day) * 100)
        }
    
    # ========================================
    # Manufacturing Order
    # ========================================
    
    async def create_manufacturing_order(
        self,
        tenant_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> ManufacturingOrder:
        """Create a new manufacturing order."""
        # Generate MO number
        number = await self._generate_mo_number(tenant_id)
        
        # Get BOM if provided
        bom = None
        if data.get("bom_id"):
            bom = await self._get_bom(data["bom_id"], tenant_id)
        
        product_id = data.get("product_id") or (bom.product_id if bom else None)
        if not product_id:
            raise ValueError("Product ID is required")
        product = await self._require_tenant_record(Product, product_id, tenant_id, "Manufactured product")
        await self._require_tenant_record(Routing, data.get("routing_id") or (bom.routing_id if bom else None), tenant_id, "Routing")
        source_location = await self._require_tenant_record(StockLocation, data.get("location_src_id"), tenant_id, "Source location")
        destination_location = await self._require_tenant_record(StockLocation, data.get("location_dest_id"), tenant_id, "Destination location")
        if bom and bom.lines and source_location is None:
            raise ValueError("A source location is required when the BOM has components")
        if destination_location is None:
            raise ValueError("A destination location is required for manufactured goods")
        if data.get("sale_order_id"):
            from app.models.sales import SaleOrder
            await self._require_tenant_record(SaleOrder, data["sale_order_id"], tenant_id, "Sales order")
        if bom:
            for bom_line in bom.lines:
                await self._require_tenant_record(Product, bom_line.product_id, tenant_id, "BOM component")
            for bom_op in bom.operations:
                await self._require_tenant_record(WorkCenter, bom_op.workcenter_id, tenant_id, "Work center")
        
        mo = ManufacturingOrder(
            tenant_id=tenant_id,
            number=number,
            name=data.get("name", f"MO {number}"),
            product_id=product_id,
            bom_id=data.get("bom_id"),
            routing_id=data.get("routing_id") or (bom.routing_id if bom else None),
            product_qty=Decimal(str(data["quantity"])),
            product_uom_id=data.get("uom_id"),
            state=MOState.DRAFT,
            planned_date=data.get("planned_date"),
            origin=data.get("origin"),
            sale_order_id=data.get("sale_order_id"),
            location_src_id=data.get("location_src_id"),
            location_dest_id=data.get("location_dest_id"),
            priority=data.get("priority", "normal"),
            notes=data.get("notes"),
            created_by_id=user_id
        )
        
        self.db.add(mo)
        await self.db.flush()
        
        # Create material lines from BOM
        if bom:
            for bom_line in bom.lines:
                # Calculate quantity needed
                qty_needed = bom_line.product_qty * (mo.product_qty / bom.product_qty)
                
                mo_line = MOLine(
                    tenant_id=tenant_id,
                    mo_id=mo.id,
                    product_id=bom_line.product_id,
                    product_qty=qty_needed,
                    product_uom_id=bom_line.product_uom_id,
                    location_id=data.get("location_src_id"),
                    unit_cost=bom_line.unit_cost
                )
                mo_line.total_cost = mo_line.product_qty * mo_line.unit_cost
                self.db.add(mo_line)
            
            # Create operations from BOM
            for bom_op in bom.operations:
                # Calculate duration for this quantity
                duration = bom_op.duration_expected + (
                    bom_op.duration_per_unit * float(mo.product_qty - bom.product_qty)
                )
                
                mo_op = MOOperation(
                    tenant_id=tenant_id,
                    mo_id=mo.id,
                    sequence=bom_op.sequence,
                    name=bom_op.name,
                    workcenter_id=bom_op.workcenter_id,
                    state=MOOperationState.PENDING,
                    duration_expected=Decimal(str(duration))
                )
                self.db.add(mo_op)
        
        # Create finished product line
        finish = MOFinish(
            tenant_id=tenant_id,
            mo_id=mo.id,
            product_id=product_id,
            product_qty=mo.product_qty,
            product_uom_id=mo.product_uom_id or (product.uom_id if product else None),
            location_id=data.get("location_dest_id")
        )
        self.db.add(finish)
        
        await self.db.commit()
        await self.db.refresh(mo)
        
        return mo
    
    async def confirm_mo(
        self,
        mo_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> ManufacturingOrder:
        """
        Confirm a manufacturing order.
        
        This reserves materials and prepares for production.
        """
        mo = await self._get_mo(mo_id, tenant_id)
        
        if mo.state != MOState.DRAFT:
            raise ValueError("Only draft MOs can be confirmed")
        
        # Check material availability
        availability = await self._check_material_availability(mo, tenant_id)
        if not availability["all_available"]:
            missing = [m for m in availability["details"] if not m["available"]]
            raise ValueError(f"Insufficient materials: {missing}")
        
        mo.state = MOState.CONFIRMED
        mo.confirmed_at = datetime.utcnow()
        mo.confirmed_by_id = user_id
        
        await self.db.commit()
        return mo
    
    async def start_mo(
        self,
        mo_id: UUID,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> ManufacturingOrder:
        """
        Start production on a manufacturing order.
        
        Consumes materials and starts operations.
        """
        mo = await self._get_mo(mo_id, tenant_id)
        
        if mo.state not in [MOState.CONFIRMED, MOState.PLANNED]:
            raise ValueError("MO must be confirmed or planned to start")
        if mo.date_start is not None:
            raise ValueError("Manufacturing order production has already started")
        
        mo.state = MOState.IN_PROGRESS
        mo.date_start = datetime.utcnow()
        
        # Consume materials (create stock moves)
        for line in mo.material_lines:
            if line.qty_consumed < line.product_qty:
                # Create stock move for material consumption
                move = await self._create_material_consumption_move(
                    mo, line, tenant_id, user_id
                )
                line.stock_move_id = move.id
                
                # Mark as consumed
                line.qty_consumed = line.product_qty
                line.total_cost = line.qty_consumed * line.unit_cost
        
        # Start first operation
        if mo.operations:
            first_op = sorted(mo.operations, key=lambda x: x.sequence)[0]
            first_op.state = MOOperationState.IN_PROGRESS
            first_op.date_start = datetime.utcnow()
        
        await self.db.commit()
        return mo
    
    async def finish_mo(
        self,
        mo_id: UUID,
        tenant_id: UUID,
        qty_produced: Optional[Decimal] = None,
        user_id: Optional[UUID] = None
    ) -> ManufacturingOrder:
        """
        Finish a manufacturing order.
        
        Creates finished goods stock and accounting entries.
        """
        mo = await self._get_mo(mo_id, tenant_id)
        
        if mo.state != MOState.IN_PROGRESS:
            raise ValueError("MO must be in progress to finish")
        
        qty = qty_produced if qty_produced is not None else (mo.product_qty - mo.qty_produced)
        if qty <= 0:
            raise ValueError("Produced quantity must be greater than zero")
        remaining_qty = mo.product_qty - mo.qty_produced
        if qty > remaining_qty:
            raise ValueError("Produced quantity exceeds the remaining manufacturing quantity")
        if not mo.finished_lines:
            raise ValueError("Manufacturing order has no finished goods line")
        
        # Update quantity produced only after validating the remaining quantity.
        mo.qty_produced += qty
        
        # Create stock move for finished goods
        for finish_line in mo.finished_lines:
            move = await self._create_finished_goods_move(
                mo, finish_line, qty, tenant_id, user_id
            )
            finish_line.stock_move_id = move.id
            
            # Update cost
            finish_line.product_qty = qty
            mo.unit_cost = mo.total_cost / mo.product_qty if mo.product_qty > 0 else Decimal("0")
            finish_line.unit_cost = mo.unit_cost
            finish_line.total_cost = qty * finish_line.unit_cost
        
        # Complete all operations
        for op in mo.operations:
            if op.state != MOOperationState.DONE:
                op.state = MOOperationState.DONE
                op.date_finished = datetime.utcnow()
                op.duration_actual = op.duration_expected
        
        # Calculate final costs
        mo.calculate_costs()
        
        # Update state
        if mo.qty_produced >= mo.product_qty:
            mo.state = MOState.DONE
            mo.date_finished = datetime.utcnow()
        
        # Create accounting entries
        await self.integration_svc.process_manufacturing_accounting(
            mo.id, tenant_id, user_id
        )
        
        await self.db.commit()
        return mo
    
    async def cancel_mo(
        self,
        mo_id: UUID,
        tenant_id: UUID,
        reason: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> ManufacturingOrder:
        """Cancel a manufacturing order."""
        mo = await self._get_mo(mo_id, tenant_id)
        
        if mo.state == MOState.DONE:
            raise ValueError("Cannot cancel completed MO")
        
        # Reverse any stock moves
        for line in mo.material_lines:
            if line.stock_move_id:
                # Create reversal move
                pass  # TODO: Implement reversal
        
        mo.state = MOState.CANCELLED
        mo.notes = (mo.notes or "") + f"\nCancelled: {reason or 'No reason'}"
        
        await self.db.commit()
        return mo
    
    # ========================================
    # Cost Calculation
    # ========================================
    
    async def calculate_mo_cost(
        self,
        mo_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Calculate manufacturing order costs."""
        mo = await self._get_mo(mo_id, tenant_id)
        
        # Material costs
        material_cost = sum(
            float(line.qty_consumed * line.unit_cost)
            for line in mo.material_lines
        )
        
        # Labor and machine costs
        labor_cost = sum(
            float(op.labor_cost)
            for op in mo.operations
            if op.state == MOOperationState.DONE
        )
        
        machine_cost = sum(
            float(op.machine_cost)
            for op in mo.operations
            if op.state == MOOperationState.DONE
        )
        
        # Overhead (could be percentage of labor/machine)
        overhead_cost = (labor_cost + machine_cost) * 0.1  # 10% overhead
        
        total_cost = material_cost + labor_cost + machine_cost + overhead_cost
        unit_cost = total_cost / float(mo.product_qty) if mo.product_qty > 0 else 0
        
        # Update MO
        mo.material_cost = Decimal(str(material_cost))
        mo.labor_cost = Decimal(str(labor_cost + machine_cost))
        mo.overhead_cost = Decimal(str(overhead_cost))
        mo.total_cost = Decimal(str(total_cost))
        mo.unit_cost = Decimal(str(unit_cost))
        
        await self.db.commit()
        
        return {
            "material_cost": material_cost,
            "labor_cost": labor_cost,
            "machine_cost": machine_cost,
            "overhead_cost": overhead_cost,
            "total_cost": total_cost,
            "unit_cost": unit_cost
        }
    
    # ========================================
    # Private Helper Methods
    # ========================================
    
    async def _get_bom(self, bom_id: UUID, tenant_id: UUID) -> BillOfMaterial:
        """Get BOM by ID."""
        result = await self.db.execute(
            select(BillOfMaterial)
            .options(
                selectinload(BillOfMaterial.lines),
                selectinload(BillOfMaterial.operations)
            )
            .where(
                BillOfMaterial.id == bom_id,
                BillOfMaterial.tenant_id == tenant_id
            )
        )
        bom = result.scalar_one_or_none()
        if not bom:
            raise ValueError(f"BOM {bom_id} not found")
        return bom
    
    async def _get_mo(self, mo_id: UUID, tenant_id: UUID) -> ManufacturingOrder:
        """Get MO by ID."""
        result = await self.db.execute(
            select(ManufacturingOrder)
            .options(
                selectinload(ManufacturingOrder.material_lines),
                selectinload(ManufacturingOrder.finished_lines),
                selectinload(ManufacturingOrder.operations)
            )
            .where(
                ManufacturingOrder.id == mo_id,
                ManufacturingOrder.tenant_id == tenant_id
            )
        )
        mo = result.scalar_one_or_none()
        if not mo:
            raise ValueError(f"Manufacturing Order {mo_id} not found")
        return mo
    
    async def _check_material_availability(
        self,
        mo: ManufacturingOrder,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Check if all materials are available."""
        details = []
        all_available = True
        
        for line in mo.material_lines:
            # Get stock quantity
            result = await self.db.execute(
                select(func.sum(StockQuantity.quantity))
                .where(
                    StockQuantity.product_id == line.product_id,
                    StockQuantity.tenant_id == tenant_id,
                    StockQuantity.is_deleted == False,
                    *([StockQuantity.location_id == mo.location_src_id] if mo.location_src_id else [])
                )
            )
            available_qty = result.scalar() or 0
            
            is_available = float(available_qty) >= float(line.product_qty)
            if not is_available:
                all_available = False
            
            details.append({
                "product_id": str(line.product_id),
                "required": float(line.product_qty),
                "available_quantity": float(available_qty),
                "available": is_available,
                "shortage": max(0, float(line.product_qty) - float(available_qty))
            })
        
        return {"all_available": all_available, "details": details}
    
    async def _create_material_consumption_move(
        self,
        mo: ManufacturingOrder,
        line: MOLine,
        tenant_id: UUID,
        user_id: Optional[UUID]
    ) -> StockMove:
        """Create stock move for material consumption."""
        product = await self._require_tenant_record(Product, line.product_id, tenant_id, "Material product")
        location = await self._require_tenant_record(StockLocation, line.location_id, tenant_id, "Material source location")
        if not location:
            raise ValueError("Material source location is required")
        
        move = await self.inventory_svc.create_stock_move(
            product_id=line.product_id,
            quantity=line.product_qty,
            uom_id=line.product_uom_id or product.uom_id,
            move_type=StockMoveType.OUT,
            warehouse_from_id=location.warehouse_id,
            location_from_id=line.location_id,
            unit_cost=line.unit_cost,
            move_date=date.today(),
            reference=mo.number,
            reference_id=mo.id,
            reference_type="manufacturing_order",
            notes=f"Material consumption for {mo.number}",
            tenant_id=tenant_id,
            created_by_id=user_id,
        )
        await self.inventory_svc.confirm_stock_move(move.id, tenant_id, line.product_qty)
        await self.inventory_svc.process_stock_move(move.id, tenant_id)
        return move
    
    async def _create_finished_goods_move(
        self,
        mo: ManufacturingOrder,
        finish_line: MOFinish,
        qty: Decimal,
        tenant_id: UUID,
        user_id: Optional[UUID]
    ) -> StockMove:
        """Create stock move for finished goods."""
        product = await self._require_tenant_record(Product, finish_line.product_id, tenant_id, "Finished product")
        location = await self._require_tenant_record(StockLocation, finish_line.location_id, tenant_id, "Finished goods destination")
        if not location:
            raise ValueError("Finished goods destination is required")
        
        # Calculate unit cost
        unit_cost = mo.unit_cost if mo.unit_cost > 0 else (
            product.average_cost if product else Decimal("0")
        )
        
        move = await self.inventory_svc.create_stock_move(
            product_id=finish_line.product_id,
            quantity=qty,
            uom_id=finish_line.product_uom_id or product.uom_id,
            move_type=StockMoveType.IN,
            warehouse_to_id=location.warehouse_id,
            location_to_id=finish_line.location_id,
            unit_cost=unit_cost,
            move_date=date.today(),
            reference=mo.number,
            reference_id=mo.id,
            reference_type="manufacturing_order",
            notes=f"Finished goods from {mo.number}",
            tenant_id=tenant_id,
            created_by_id=user_id,
        )
        await self.inventory_svc.confirm_stock_move(move.id, tenant_id, qty)
        await self.inventory_svc.process_stock_move(move.id, tenant_id)
        product.average_cost = unit_cost
        return move
    
    async def _generate_bom_code(self, tenant_id: UUID) -> str:
        """Generate unique BOM code."""
        prefix = "BOM"
        count = await self.db.scalar(
            select(func.count()).select_from(BillOfMaterial).where(
                BillOfMaterial.tenant_id == tenant_id
            )
        )
        return f"{prefix}{(count + 1):05d}"
    
    async def _generate_mo_number(self, tenant_id: UUID) -> str:
        """Generate unique MO number."""
        prefix = "MO"
        today = date.today()
        year_month = today.strftime("%Y%m")
        
        count = await self.db.scalar(
            select(func.count()).select_from(ManufacturingOrder).where(
                ManufacturingOrder.tenant_id == tenant_id,
                ManufacturingOrder.number.like(f"{prefix}{year_month}%")
            )
        )
        
        return f"{prefix}{year_month}{(count + 1):04d}"
    
    # ========================================
    # List/Query Methods
    # ========================================
    
    async def list_boms(
        self,
        tenant_id: UUID,
        product_id: Optional[UUID] = None,
        state: Optional[BOMState] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[BillOfMaterial], int]:
        """List BOMs with filters."""
        query = select(BillOfMaterial).where(
            BillOfMaterial.tenant_id == tenant_id,
            BillOfMaterial.is_deleted == False
        )
        
        if product_id:
            query = query.where(BillOfMaterial.product_id == product_id)
        if state:
            query = query.where(BillOfMaterial.state == state)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        query = query.order_by(BillOfMaterial.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0
    
    async def list_manufacturing_orders(
        self,
        tenant_id: UUID,
        state: Optional[MOState] = None,
        product_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[ManufacturingOrder], int]:
        """List manufacturing orders with filters."""
        query = select(ManufacturingOrder).where(
            ManufacturingOrder.tenant_id == tenant_id,
            ManufacturingOrder.is_deleted == False
        )
        
        if state:
            query = query.where(ManufacturingOrder.state == state)
        if product_id:
            query = query.where(ManufacturingOrder.product_id == product_id)
        if date_from:
            query = query.where(ManufacturingOrder.planned_date >= date_from)
        if date_to:
            query = query.where(ManufacturingOrder.planned_date <= date_to)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        query = query.order_by(ManufacturingOrder.planned_date.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0
