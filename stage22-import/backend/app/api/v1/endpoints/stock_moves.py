"""
Nexus ERP - Stock Moves API Endpoints
======================================

API endpoints for stock movement management.
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.user import User
from app.models.inventory import StockMove, StockMoveState, StockMoveType
from app.schemas.inventory import (
    StockMoveCreate, StockMoveUpdate, StockMoveResponse,
    StockMoveListResponse, StockMoveConfirmRequest, StockMoveCancelRequest
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/stock-moves", tags=["Inventory - Stock Moves"])


@router.get(
    "",
    response_model=StockMoveListResponse,
    summary="List Stock Moves",
    description="Get paginated list of stock movements"
)
async def list_stock_moves(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    move_type: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    product_id: Optional[UUID] = Query(None),
    warehouse_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get paginated list of stock moves."""
    query = select(StockMove).where(
        StockMove.tenant_id == current_user.tenant_id,
        StockMove.is_deleted == False
    )
    
    # Filters
    if date_from:
        query = query.where(StockMove.date >= date_from)
    if date_to:
        query = query.where(StockMove.date <= date_to)
    if move_type:
        try:
            query = query.where(StockMove.move_type == StockMoveType(move_type.lower()))
        except ValueError:
            pass
    if state:
        try:
            query = query.where(StockMove.state == StockMoveState(state.lower()))
        except ValueError:
            pass
    if product_id:
        query = query.where(StockMove.product_id == product_id)
    if warehouse_id:
        query = query.where(
            (StockMove.warehouse_from_id == warehouse_id) |
            (StockMove.warehouse_to_id == warehouse_id)
        )
    if search:
        from sqlalchemy import or_
        search_term = f"%{search}%"
        query = query.where(
            or_(
                StockMove.number.ilike(search_term),
                StockMove.reference.ilike(search_term)
            )
        )
    
    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(StockMove.date.desc(), StockMove.number.desc())
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    moves = result.scalars().all()
    
    return StockMoveListResponse(
        items=[StockMoveResponse.model_validate(m) for m in moves],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post(
    "",
    response_model=StockMoveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Stock Move",
    description="Create a new stock movement"
)
async def create_stock_move(
    move_data: StockMoveCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("inventory.stock.create"))
):
    """Create a new stock movement."""
    svc = InventoryService(db)
    
    try:
        move_type = StockMoveType(move_data.move_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid move type: {move_data.move_type}"
        )
    
    try:
        move = await svc.create_stock_move(
            product_id=move_data.product_id,
            quantity=move_data.quantity,
            uom_id=move_data.uom_id,
            move_type=move_type,
            warehouse_from_id=move_data.warehouse_from_id,
            warehouse_to_id=move_data.warehouse_to_id,
            location_from_id=move_data.location_from_id,
            location_to_id=move_data.location_to_id,
            unit_cost=move_data.unit_cost,
            move_date=move_data.date,
            reference=move_data.reference,
            reference_id=move_data.reference_id,
            reference_type=move_data.reference_type,
            partner_id=move_data.partner_id,
            lot_id=move_data.lot_id,
            serial_number=move_data.serial_number,
            reason=move_data.reason,
            notes=move_data.notes,
            tenant_id=current_user.tenant_id,
            created_by_id=current_user.id
        )
        
        await db.commit()
        await db.refresh(move)
        
        return StockMoveResponse.model_validate(move)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{move_id}",
    response_model=StockMoveResponse,
    summary="Get Stock Move",
    description="Get stock move details"
)
async def get_stock_move(
    move_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get stock move details."""
    move = await db.get(StockMove, move_id)
    
    if not move or move.tenant_id != current_user.tenant_id or move.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock move not found"
        )
    
    return StockMoveResponse.model_validate(move)


@router.post(
    "/{move_id}/confirm",
    response_model=StockMoveResponse,
    summary="Confirm Stock Move",
    description="Confirm a draft stock move"
)
async def confirm_stock_move(
    move_id: UUID,
    request: StockMoveConfirmRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("inventory.stock.confirm"))
):
    """Confirm a stock move."""
    svc = InventoryService(db)
    
    quantity = request.quantity_done if request else None
    
    try:
        move = await svc.confirm_stock_move(move_id, current_user.tenant_id, quantity)
        await db.commit()
        return StockMoveResponse.model_validate(move)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{move_id}/process",
    response_model=StockMoveResponse,
    summary="Process Stock Move",
    description="Process a confirmed stock move to update stock quantities"
)
async def process_stock_move(
    move_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("inventory.stock.process"))
):
    """Process a stock move."""
    svc = InventoryService(db)
    
    try:
        move = await svc.process_stock_move(move_id, current_user.tenant_id)
        await db.commit()
        return StockMoveResponse.model_validate(move)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{move_id}/cancel",
    response_model=StockMoveResponse,
    summary="Cancel Stock Move",
    description="Cancel a stock move"
)
async def cancel_stock_move(
    move_id: UUID,
    request: StockMoveCancelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("inventory.stock.cancel"))
):
    """Cancel a stock move."""
    svc = InventoryService(db)
    
    try:
        move = await svc.cancel_stock_move(move_id, current_user.tenant_id, request.reason)
        await db.commit()
        return StockMoveResponse.model_validate(move)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{move_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Stock Move",
    description="Delete a draft stock move"
)
async def delete_stock_move(
    move_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("inventory.stock.delete"))
):
    """Delete a draft stock move."""
    move = await db.get(StockMove, move_id)
    
    if not move or move.tenant_id != current_user.tenant_id or move.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock move not found"
        )
    
    if move.state != StockMoveState.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft moves can be deleted"
        )
    
    move.soft_delete(current_user.id)
    await db.commit()
