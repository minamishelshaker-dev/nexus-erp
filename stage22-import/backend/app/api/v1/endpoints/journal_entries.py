"""
Nexus ERP - Journal Entries API Endpoints
==========================================

API endpoints for Journal Entry management.
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
from app.models.accounting import JournalEntry, JournalItem, EntryState
from app.schemas.accounting import (
    JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse,
    JournalEntryListResponse, JournalEntryPostRequest, JournalEntryReverseRequest
)
from app.services.accounting_service import AccountingService

router = APIRouter(prefix="/journal-entries", tags=["Accounting - Journal Entries"])


@router.get(
    "",
    response_model=JournalEntryListResponse,
    summary="List Journal Entries",
    description="Get paginated list of journal entries"
)
async def list_journal_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    state: Optional[str] = Query(None, description="Filter by state"),
    move_type: Optional[str] = Query(None, description="Filter by move type"),
    search: Optional[str] = Query(None, description="Search in number, ref, description"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get paginated list of journal entries.
    """
    query = select(JournalEntry).where(
        JournalEntry.tenant_id == current_user.tenant_id,
        JournalEntry.is_deleted == False
    )
    
    # Apply filters
    if date_from:
        query = query.where(JournalEntry.date >= date_from)
    
    if date_to:
        query = query.where(JournalEntry.date <= date_to)
    
    if state:
        try:
            query = query.where(JournalEntry.state == EntryState(state.lower()))
        except ValueError:
            pass
    
    if move_type:
        query = query.where(JournalEntry.move_type == move_type.lower())
    
    if search:
        from sqlalchemy import or_
        search_term = f"%{search}%"
        query = query.where(
            or_(
                JournalEntry.number.ilike(search_term),
                JournalEntry.ref.ilike(search_term),
                JournalEntry.description.ilike(search_term)
            )
        )
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(JournalEntry.date.desc(), JournalEntry.number.desc())
    query = query.offset(offset).limit(page_size)
    
    # Execute with lines
    from sqlalchemy.orm import selectinload
    query = query.options(
        selectinload(JournalEntry.lines).selectinload(JournalItem.account)
    )
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    return JournalEntryListResponse(
        items=[JournalEntryResponse.model_validate(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post(
    "",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Journal Entry",
    description="Create a new journal entry"
)
async def create_journal_entry(
    entry_data: JournalEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("accounting.journal.create"))
):
    """
    Create a new journal entry.
    
    The entry must be balanced (total debits = total credits).
    """
    from app.models.accounting import MoveType
    
    try:
        move_type = MoveType(entry_data.move_type.lower())
    except ValueError:
        move_type = MoveType.MANUAL
    
    svc = AccountingService(db)
    
    # Convert lines to dict
    lines = [
        {
            "account_id": line.account_id,
            "debit": line.debit,
            "credit": line.credit,
            "name": line.name,
            "partner_id": line.partner_id,
            "analytic_account_id": line.analytic_account_id
        }
        for line in entry_data.lines
    ]
    
    try:
        entry = await svc.create_journal_entry(
            date=entry_data.date,
            lines=lines,
            description=entry_data.description,
            ref=entry_data.ref,
            move_type=move_type,
            journal_id=entry_data.journal_id,
            tenant_id=current_user.tenant_id,
            created_by_id=current_user.id
        )
        
        await db.commit()
        await db.refresh(entry)
        
        return JournalEntryResponse.model_validate(entry)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{entry_id}",
    response_model=JournalEntryResponse,
    summary="Get Journal Entry",
    description="Get journal entry details"
)
async def get_journal_entry(
    entry_id: UUID = Path(..., description="Journal Entry ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get journal entry details with all lines."""
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.tenant_id == current_user.tenant_id,
            JournalEntry.is_deleted == False
        ).options(
            selectinload(JournalEntry.lines).selectinload(JournalItem.account)
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found"
        )
    
    return JournalEntryResponse.model_validate(entry)


@router.put(
    "/{entry_id}",
    response_model=JournalEntryResponse,
    summary="Update Journal Entry",
    description="Update a draft journal entry"
)
async def update_journal_entry(
    entry_id: UUID,
    entry_data: JournalEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("accounting.journal.update"))
):
    """Update a journal entry (only drafts can be updated)."""
    entry = await db.get(JournalEntry, entry_id)
    
    if not entry or entry.tenant_id != current_user.tenant_id or entry.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found"
        )
    
    if entry.state != EntryState.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft entries can be updated"
        )
    
    # Update basic fields
    update_data = entry_data.model_dump(exclude_unset=True, exclude={"lines"})
    for field, value in update_data.items():
        setattr(entry, field, value)
    
    # Update lines if provided
    if entry_data.lines:
        # Delete existing lines
        from sqlalchemy import delete
        await db.execute(
            delete(JournalItem).where(JournalItem.entry_id == entry_id)
        )
        
        # Create new lines
        total_debit = sum(line.debit for line in entry_data.lines)
        total_credit = sum(line.credit for line in entry_data.lines)
        
        if abs(total_debit - total_credit) > 0.01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Entry must be balanced. Debit: {total_debit}, Credit: {total_credit}"
            )
        
        for idx, line_data in enumerate(entry_data.lines):
            line = JournalItem(
                entry_id=entry.id,
                account_id=line_data.account_id,
                sequence=(idx + 1) * 10,
                debit=line_data.debit,
                credit=line_data.credit,
                date=entry.date,
                name=line_data.name,
                partner_id=line_data.partner_id,
                analytic_account_id=line_data.analytic_account_id,
                tenant_id=current_user.tenant_id
            )
            db.add(line)
        
        entry.total_debit = total_debit
        entry.total_credit = total_credit
    
    await db.commit()
    await db.refresh(entry)
    
    return JournalEntryResponse.model_validate(entry)


@router.post(
    "/{entry_id}/post",
    response_model=JournalEntryResponse,
    summary="Post Journal Entry",
    description="Post a draft journal entry"
)
async def post_journal_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("accounting.journal.post"))
):
    """
    Post a journal entry.
    
    This will update all account balances.
    """
    svc = AccountingService(db)
    
    try:
        entry = await svc.post_journal_entry(entry_id, current_user.id, current_user.tenant_id)
        await db.commit()
        return JournalEntryResponse.model_validate(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{entry_id}/reverse",
    response_model=JournalEntryResponse,
    summary="Reverse Journal Entry",
    description="Create a reversal entry"
)
async def reverse_journal_entry(
    entry_id: UUID,
    reversal_data: JournalEntryReverseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("accounting.journal.reverse"))
):
    """
    Reverse a posted journal entry.
    
    Creates a new entry with reversed debits and credits.
    """
    svc = AccountingService(db)
    
    try:
        entry = await svc.reverse_journal_entry(
            entry_id,
            reversal_date=reversal_data.date,
            reason=reversal_data.reason,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id
        )
        await db.commit()
        return JournalEntryResponse.model_validate(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Journal Entry",
    description="Delete a draft journal entry"
)
async def delete_journal_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("accounting.journal.delete"))
):
    """Delete a draft journal entry."""
    entry = await db.get(JournalEntry, entry_id)
    
    if not entry or entry.tenant_id != current_user.tenant_id or entry.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found"
        )
    
    if entry.state != EntryState.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft entries can be deleted"
        )
    
    entry.soft_delete(current_user.id)
    await db.commit()
