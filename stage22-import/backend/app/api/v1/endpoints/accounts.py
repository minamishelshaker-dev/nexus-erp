"""
Nexus ERP - Accounts API Endpoints
===================================

API endpoints for Chart of Accounts management.
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.user import User
from app.models.accounting import Account, AccountType
from app.schemas.accounting import (
    AccountCreate, AccountUpdate, AccountResponse, AccountListResponse,
    AccountTreeResponse, AccountBriefResponse
)
from app.services.accounting_service import AccountingService

router = APIRouter(prefix="/accounts", tags=["Accounting - Chart of Accounts"])


@router.get(
    "",
    response_model=AccountListResponse,
    summary="List Accounts",
    description="Get paginated list of accounts with optional filters"
)
async def list_accounts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in code and name"),
    account_type: Optional[str] = Query(None, description="Filter by account type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    parent_id: Optional[UUID] = Query(None, description="Filter by parent account"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get paginated list of accounts.
    
    - **page**: Page number (starts from 1)
    - **page_size**: Number of items per page
    - **search**: Search in account code and name
    - **account_type**: Filter by account type (asset, liability, equity, revenue, expense)
    - **is_active**: Filter by active status
    - **parent_id**: Filter by parent account
    """
    query = select(Account).where(
        Account.tenant_id == current_user.tenant_id,
        Account.is_deleted == False
    )
    
    # Apply filters
    if search:
        from sqlalchemy import or_
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Account.code.ilike(search_term),
                Account.name.ilike(search_term)
            )
        )
    
    if account_type:
        try:
            acc_type = AccountType(account_type.lower())
            query = query.where(Account.account_type == acc_type)
        except ValueError:
            pass
    
    if is_active is not None:
        query = query.where(Account.is_active == is_active)
    
    if parent_id:
        query = query.where(Account.parent_id == parent_id)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Account.code).offset(offset).limit(page_size)
    
    # Execute
    result = await db.execute(query)
    accounts = result.scalars().all()
    
    return AccountListResponse(
        items=[AccountResponse.model_validate(a) for a in accounts],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Account",
    description="Create a new account in the chart of accounts"
)
async def create_account(
    account_data: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("accounting.account.create"))
):
    """
    Create a new account.
    
    Required permission: accounting.account.create
    """
    svc = AccountingService(db)
    
    try:
        account_type = AccountType(account_data.account_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid account type: {account_data.account_type}"
        )
    
    account = await svc.create_account(
        code=account_data.code,
        name=account_data.name,
        account_type=account_type,
        parent_id=account_data.parent_id,
        category=account_data.category,
        is_header=account_data.is_header,
        is_reconcilable=account_data.is_reconcilable,
        currency_id=account_data.currency_id,
        opening_debit=account_data.opening_debit,
        opening_credit=account_data.opening_credit,
        notes=account_data.notes,
        tenant_id=current_user.tenant_id,
        created_by_id=current_user.id
    )
    
    await db.commit()
    await db.refresh(account)
    
    return AccountResponse.model_validate(account)


@router.get(
    "/tree",
    response_model=List[AccountTreeResponse],
    summary="Get Account Tree",
    description="Get hierarchical chart of accounts tree"
)
async def get_account_tree(
    account_type: Optional[str] = Query(None, description="Filter by account type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get chart of accounts as a hierarchical tree.
    
    - **account_type**: Filter by account type (optional)
    """
    svc = AccountingService(db)
    
    acc_type = None
    if account_type:
        try:
            acc_type = AccountType(account_type.lower())
        except ValueError:
            pass
    
    trees = await svc.get_account_tree(current_user.tenant_id, acc_type)
    return trees


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Get Account",
    description="Get account details by ID"
)
async def get_account(
    account_id: UUID = Path(..., description="Account ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get account details."""
    account = await db.get(Account, account_id)
    
    if not account or account.tenant_id != current_user.tenant_id or account.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    return AccountResponse.model_validate(account)


@router.put(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Update Account",
    description="Update account information"
)
async def update_account(
    account_id: UUID,
    account_data: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("accounting.account.update"))
):
    """Update account."""
    account = await db.get(Account, account_id)
    
    if not account or account.tenant_id != current_user.tenant_id or account.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Update fields
    update_data = account_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)
    
    await db.commit()
    await db.refresh(account)
    
    return AccountResponse.model_validate(account)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Account",
    description="Soft delete an account"
)
async def delete_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("accounting.account.delete"))
):
    """Soft delete an account."""
    account = await db.get(Account, account_id)
    
    if not account or account.tenant_id != current_user.tenant_id or account.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Check for journal items
    from app.models.accounting import JournalItem
    result = await db.execute(
        select(func.count()).select_from(JournalItem).where(
            JournalItem.account_id == account_id,
            JournalItem.is_deleted == False
        )
    )
    if result.scalar() > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete account with journal entries"
        )
    
    account.soft_delete(current_user.id)
    await db.commit()


@router.get(
    "/{account_id}/balance",
    summary="Get Account Balance",
    description="Get current balance of an account"
)
async def get_account_balance(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get account balance."""
    account = await db.get(Account, account_id)
    
    if not account or account.tenant_id != current_user.tenant_id or account.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    return {
        "account_id": account.id,
        "code": account.code,
        "name": account.name,
        "debit_balance": account.debit_balance,
        "credit_balance": account.credit_balance,
        "balance": account.balance,
        "normal_balance": account.normal_balance
    }


# ========================================
# Bank Reconciliation API
# ========================================

from app.schemas.accounting import BankStatementCreate, BankStatementLineCreate, BankStatementMatch
from app.services.bank_reconciliation_service import BankReconciliationService
from app.models.accounting import BankStatement, BankStatementLine


@router.post("/bank-statements", status_code=status.HTTP_201_CREATED)
async def create_bank_statement(
    payload: BankStatementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("accounting.journal.create")),
):
    service = BankReconciliationService(db)
    try:
        statement = await service.create_statement(
            **payload.model_dump(), tenant_id=current_user.tenant_id,
            created_by_id=current_user.id,
        )
        await db.commit()
        await db.refresh(statement)
        return {"id": str(statement.id), "statement_number": statement.statement_number,
                "state": statement.state.value, "account_id": str(statement.account_id)}
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate or conflicting bank reconciliation record") from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bank-statements/{statement_id}/lines", status_code=status.HTTP_201_CREATED)
async def add_bank_statement_line(
    statement_id: UUID,
    payload: BankStatementLineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("accounting.journal.create")),
):
    service = BankReconciliationService(db)
    try:
        line = await service.add_line(
            statement_id=statement_id, tenant_id=current_user.tenant_id,
            created_by_id=current_user.id, **payload.model_dump(),
        )
        await db.commit()
        await db.refresh(line)
        return {"id": str(line.id), "line_number": line.line_number,
                "debit": str(line.debit), "credit": str(line.credit), "matched": False}
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate or conflicting bank reconciliation record") from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bank-statements/{statement_id}/lines/{line_id}/match")
async def match_bank_statement_line(
    statement_id: UUID,
    line_id: UUID,
    payload: BankStatementMatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("accounting.journal.update")),
):
    service = BankReconciliationService(db)
    try:
        line = await service.match_line(
            statement_id=statement_id, line_id=line_id,
            journal_item_id=payload.journal_item_id,
            tenant_id=current_user.tenant_id, user_id=current_user.id,
        )
        await db.commit()
        return {"id": str(line.id), "matched": True,
                "journal_item_id": str(line.matched_journal_item_id)}
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate or conflicting bank reconciliation record") from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bank-statements/{statement_id}/finalize")
async def finalize_bank_statement(
    statement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("accounting.journal.post")),
):
    service = BankReconciliationService(db)
    try:
        statement = await service.finalize_statement(
            statement_id=statement_id, tenant_id=current_user.tenant_id,
        )
        await db.commit()
        return {"id": str(statement.id), "state": statement.state.value,
                "total_debits": str(statement.total_debits),
                "total_credits": str(statement.total_credits)}
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate or conflicting bank reconciliation record") from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
