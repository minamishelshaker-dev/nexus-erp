"""
Nexus ERP - Manufacturing API Endpoints
========================================

REST API endpoints for the Manufacturing (MRP) module.
"""

from datetime import date
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.user import User
from app.models.manufacturing import BOMState, MOState, WorkCenterState
from app.services.manufacturing_service import ManufacturingService

router = APIRouter(prefix="/manufacturing", tags=["Manufacturing"])


# ========================================
# Request/Response Schemas
# ========================================

class BOMLineCreate(BaseModel):
    product_id: UUID
    quantity: Decimal
    uom_id: Optional[UUID] = None
    scrap_percent: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")


class BOMCreate(BaseModel):
    name: str
    product_id: UUID
    product_qty: Decimal = Decimal("1")
    product_uom_id: Optional[UUID] = None
    bom_type: str = "manufacture"
    routing_id: Optional[UUID] = None
    lines: List[BOMLineCreate]
    notes: Optional[str] = None


class WorkCenterCreate(BaseModel):
    code: str
    name: str
    capacity_per_hour: Decimal = Decimal("1")
    efficiency: Decimal = Decimal("100")
    cost_per_hour: Decimal = Decimal("0")
    labor_cost_per_hour: Decimal = Decimal("0")
    machine_cost_per_hour: Decimal = Decimal("0")
    notes: Optional[str] = None


class MOCreate(BaseModel):
    name: Optional[str] = None
    product_id: Optional[UUID] = None
    bom_id: Optional[UUID] = None
    quantity: Decimal
    uom_id: Optional[UUID] = None
    planned_date: Optional[date] = None
    location_src_id: Optional[UUID] = None
    location_dest_id: Optional[UUID] = None
    priority: str = "normal"
    notes: Optional[str] = None


# ========================================
# BOM Endpoints
# ========================================

@router.get("/boms")
async def list_boms(
    product_id: Optional[UUID] = None,
    state: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List Bills of Materials."""
    await require_permission(current_user, "manufacturing.bom.read")
    
    service = ManufacturingService(db)
    
    state_enum = None
    if state:
        try:
            state_enum = BOMState(state)
        except ValueError:
            pass
    
    boms, total = await service.list_boms(
        tenant_id=current_user.tenant_id,
        product_id=product_id,
        state=state_enum,
        page=page,
        page_size=page_size
    )
    
    return {
        "items": [
            {
                "id": str(b.id),
                "code": b.code,
                "name": b.name,
                "product_id": str(b.product_id),
                "product_qty": float(b.product_qty),
                "bom_type": b.bom_type.value,
                "state": b.state.value,
                "version": b.version,
                "total_cost": float(b.total_cost),
                "line_count": len(b.lines) if b.lines else 0
            }
            for b in boms
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/boms", status_code=status.HTTP_201_CREATED)
async def create_bom(
    data: BOMCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new Bill of Material."""
    await require_permission(current_user, "manufacturing.bom.create")
    
    service = ManufacturingService(db)
    
    bom = await service.create_bom(
        tenant_id=current_user.tenant_id,
        data={
            "name": data.name,
            "product_id": data.product_id,
            "product_qty": data.product_qty,
            "product_uom_id": data.product_uom_id,
            "bom_type": data.bom_type,
            "routing_id": data.routing_id,
            "lines": [line.model_dump() for line in data.lines],
            "notes": data.notes
        },
        user_id=current_user.id
    )
    
    return {
        "id": str(bom.id),
        "code": bom.code,
        "name": bom.name,
        "state": bom.state.value
    }


@router.get("/boms/{bom_id}")
async def get_bom(
    bom_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get BOM details."""
    await require_permission(current_user, "manufacturing.bom.read")
    
    service = ManufacturingService(db)
    bom = await service._get_bom(bom_id, current_user.tenant_id)
    
    return {
        "id": str(bom.id),
        "code": bom.code,
        "name": bom.name,
        "product_id": str(bom.product_id),
        "product_qty": float(bom.product_qty),
        "bom_type": bom.bom_type.value,
        "state": bom.state.value,
        "version": bom.version,
        "material_cost": float(bom.material_cost),
        "labor_cost": float(bom.labor_cost),
        "total_cost": float(bom.total_cost),
        "lines": [
            {
                "id": str(line.id),
                "product_id": str(line.product_id),
                "quantity": float(line.product_qty),
                "scrap_percent": float(line.scrap_percent),
                "unit_cost": float(line.unit_cost),
                "total_cost": float(line.total_cost)
            }
            for line in bom.lines
        ],
        "operations": [
            {
                "id": str(op.id),
                "sequence": op.sequence,
                "name": op.name,
                "workcenter_id": str(op.workcenter_id) if op.workcenter_id else None,
                "duration_expected": float(op.duration_expected)
            }
            for op in bom.operations
        ]
    }


@router.post("/boms/{bom_id}/activate")
async def activate_bom(
    bom_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activate a BOM for production."""
    await require_permission(current_user, "manufacturing.bom.update")
    
    service = ManufacturingService(db)
    bom = await service.activate_bom(bom_id, current_user.tenant_id, current_user.id)
    
    return {"id": str(bom.id), "state": bom.state.value}


# ========================================
# Work Center Endpoints
# ========================================

@router.get("/work-centers")
async def list_work_centers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List work centers."""
    await require_permission(current_user, "manufacturing.workcenter.read")
    
    from app.models.manufacturing import WorkCenter
    from sqlalchemy import select
    
    result = await db.execute(
        select(WorkCenter).where(
            WorkCenter.tenant_id == current_user.tenant_id,
            WorkCenter.is_deleted == False
        )
    )
    
    wcs = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(wc.id),
                "code": wc.code,
                "name": wc.name,
                "capacity_per_hour": float(wc.capacity_per_hour),
                "efficiency": float(wc.efficiency),
                "cost_per_hour": float(wc.cost_per_hour),
                "state": wc.state.value,
                "is_active": wc.is_active
            }
            for wc in wcs
        ]
    }


@router.post("/work-centers", status_code=status.HTTP_201_CREATED)
async def create_work_center(
    data: WorkCenterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new work center."""
    await require_permission(current_user, "manufacturing.workcenter.create")
    
    service = ManufacturingService(db)
    
    wc = await service.create_workcenter(
        tenant_id=current_user.tenant_id,
        data=data.model_dump(),
        user_id=current_user.id
    )
    
    return {
        "id": str(wc.id),
        "code": wc.code,
        "name": wc.name
    }


@router.get("/work-centers/{wc_id}/availability")
async def get_workcenter_availability(
    wc_id: UUID,
    from_date: date,
    to_date: date,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get work center availability."""
    await require_permission(current_user, "manufacturing.workcenter.read")
    
    service = ManufacturingService(db)
    
    availability = await service.get_workcenter_availability(
        workcenter_id=wc_id,
        from_date=from_date,
        to_date=to_date,
        tenant_id=current_user.tenant_id
    )
    
    return availability


# ========================================
# Manufacturing Order Endpoints
# ========================================

@router.get("/orders")
async def list_manufacturing_orders(
    state: Optional[str] = None,
    product_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List manufacturing orders."""
    await require_permission(current_user, "manufacturing.order.read")
    
    service = ManufacturingService(db)
    
    state_enum = None
    if state:
        try:
            state_enum = MOState(state)
        except ValueError:
            pass
    
    orders, total = await service.list_manufacturing_orders(
        tenant_id=current_user.tenant_id,
        state=state_enum,
        product_id=product_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size
    )
    
    return {
        "items": [
            {
                "id": str(o.id),
                "number": o.number,
                "name": o.name,
                "product_id": str(o.product_id),
                "product_qty": float(o.product_qty),
                "qty_produced": float(o.qty_produced),
                "progress_percent": o.progress_percent,
                "state": o.state.value,
                "planned_date": o.planned_date.isoformat() if o.planned_date else None,
                "total_cost": float(o.total_cost)
            }
            for o in orders
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_manufacturing_order(
    data: MOCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new manufacturing order."""
    await require_permission(current_user, "manufacturing.order.create")
    
    service = ManufacturingService(db)
    
    mo = await service.create_manufacturing_order(
        tenant_id=current_user.tenant_id,
        data=data.model_dump(),
        user_id=current_user.id
    )
    
    return {
        "id": str(mo.id),
        "number": mo.number,
        "state": mo.state.value,
        "material_lines_count": len(mo.material_lines) if mo.material_lines else 0
    }


@router.get("/orders/{mo_id}")
async def get_manufacturing_order(
    mo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get manufacturing order details."""
    await require_permission(current_user, "manufacturing.order.read")
    
    service = ManufacturingService(db)
    mo = await service._get_mo(mo_id, current_user.tenant_id)
    
    return {
        "id": str(mo.id),
        "number": mo.number,
        "name": mo.name,
        "product_id": str(mo.product_id),
        "bom_id": str(mo.bom_id) if mo.bom_id else None,
        "product_qty": float(mo.product_qty),
        "qty_produced": float(mo.qty_produced),
        "qty_remaining": float(mo.qty_remaining),
        "progress_percent": mo.progress_percent,
        "state": mo.state.value,
        "planned_date": mo.planned_date.isoformat() if mo.planned_date else None,
        "date_start": mo.date_start.isoformat() if mo.date_start else None,
        "date_finished": mo.date_finished.isoformat() if mo.date_finished else None,
        "material_cost": float(mo.material_cost),
        "labor_cost": float(mo.labor_cost),
        "total_cost": float(mo.total_cost),
        "unit_cost": float(mo.unit_cost),
        "material_lines": [
            {
                "id": str(line.id),
                "product_id": str(line.product_id),
                "product_qty": float(line.product_qty),
                "qty_consumed": float(line.qty_consumed),
                "unit_cost": float(line.unit_cost),
                "total_cost": float(line.total_cost)
            }
            for line in mo.material_lines
        ],
        "operations": [
            {
                "id": str(op.id),
                "sequence": op.sequence,
                "name": op.name,
                "state": op.state.value,
                "duration_expected": float(op.duration_expected),
                "duration_actual": float(op.duration_actual)
            }
            for op in mo.operations
        ]
    }


@router.post("/orders/{mo_id}/confirm")
async def confirm_manufacturing_order(
    mo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm a manufacturing order."""
    await require_permission(current_user, "manufacturing.order.update")
    
    service = ManufacturingService(db)
    mo = await service.confirm_mo(mo_id, current_user.tenant_id, current_user.id)
    
    return {
        "id": str(mo.id),
        "number": mo.number,
        "state": mo.state.value
    }


@router.post("/orders/{mo_id}/start")
async def start_manufacturing_order(
    mo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start production on a manufacturing order."""
    await require_permission(current_user, "manufacturing.order.update")
    
    service = ManufacturingService(db)
    mo = await service.start_mo(mo_id, current_user.tenant_id, current_user.id)
    
    return {
        "id": str(mo.id),
        "number": mo.number,
        "state": mo.state.value,
        "date_start": mo.date_start.isoformat() if mo.date_start else None
    }


@router.post("/orders/{mo_id}/finish")
async def finish_manufacturing_order(
    mo_id: UUID,
    qty_produced: Optional[Decimal] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Finish a manufacturing order."""
    await require_permission(current_user, "manufacturing.order.update")
    
    service = ManufacturingService(db)
    mo = await service.finish_mo(
        mo_id, 
        current_user.tenant_id,
        qty_produced,
        current_user.id
    )
    
    return {
        "id": str(mo.id),
        "number": mo.number,
        "state": mo.state.value,
        "qty_produced": float(mo.qty_produced),
        "total_cost": float(mo.total_cost),
        "unit_cost": float(mo.unit_cost)
    }


@router.post("/orders/{mo_id}/cancel")
async def cancel_manufacturing_order(
    mo_id: UUID,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a manufacturing order."""
    await require_permission(current_user, "manufacturing.order.update")
    
    service = ManufacturingService(db)
    mo = await service.cancel_mo(mo_id, current_user.tenant_id, reason, current_user.id)
    
    return {
        "id": str(mo.id),
        "number": mo.number,
        "state": mo.state.value
    }


@router.get("/orders/{mo_id}/cost")
async def calculate_mo_cost(
    mo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate manufacturing order costs."""
    await require_permission(current_user, "manufacturing.order.read")
    
    service = ManufacturingService(db)
    costs = await service.calculate_mo_cost(mo_id, current_user.tenant_id)
    
    return costs
