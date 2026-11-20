"""
Nexus ERP - Accounting Service
==============================

Business logic for accounting operations including:
- Chart of Accounts management
- Journal entry processing
- Financial reporting
- Balance calculations
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
import logging

from app.models.accounting import (
    Account, AccountType, AccountCategory,
    JournalEntry, JournalItem, EntryState, MoveType,
    FiscalYear, FiscalPeriod, Journal, AnalyticAccount, Partner
)

logger = logging.getLogger(__name__)


class AccountingService:
    """
    Accounting Service
    
    Handles all accounting-related business logic.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _tenant_record(self, model, record_id: UUID, tenant_id: UUID, label: str):
        if tenant_id is None:
            raise ValueError("tenant_id is required for accounting operations")
        record = await self.db.scalar(select(model).where(
            model.id == record_id,
            model.tenant_id == tenant_id,
            model.is_deleted == False
        ))
        if record is None:
            raise ValueError(f"{label} not found")
        return record
    
    # ========================================
    # Chart of Accounts Operations
    # ========================================
    
    async def create_account(
        self,
        code: str,
        name: str,
        account_type: AccountType,
        parent_id: Optional[UUID] = None,
        category: Optional[AccountCategory] = None,
        is_header: bool = False,
        is_reconcilable: bool = False,
        currency_id: Optional[UUID] = None,
        opening_debit: Decimal = Decimal("0"),
        opening_credit: Decimal = Decimal("0"),
        notes: Optional[str] = None,
        tenant_id: UUID = None,
        created_by_id: Optional[UUID] = None
    ) -> Account:
        """
        Create a new account in the chart of accounts.
        
        Args:
            code: Unique account code
            name: Account name
            account_type: Type of account (asset, liability, etc.)
            parent_id: Parent account for hierarchy
            category: Account category for reporting
            is_header: Whether this is a header account
            is_reconcilable: Whether account supports reconciliation
            currency_id: Currency for multi-currency accounts
            opening_debit: Opening debit balance
            opening_credit: Opening credit balance
            notes: Additional notes
            tenant_id: Tenant ID
            created_by_id: User creating the account
            
        Returns:
            Created Account record
        """
        # Check for duplicate code
        existing = await self.db.execute(
            select(Account).where(
                Account.code == code,
                Account.tenant_id == tenant_id,
                Account.is_deleted == False
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Account with code '{code}' already exists")
        
        # Calculate level based on parent
        level = 0
        if tenant_id is None:
            raise ValueError("tenant_id is required to create an account")
        if parent_id:
            parent = await self._tenant_record(Account, parent_id, tenant_id, "Parent account")
            level = parent.level + 1
            parent.is_parent = True
        
        # Create account
        account = Account(
            code=code,
            name=name,
            account_type=account_type,
            category=category,
            parent_id=parent_id,
            level=level,
            is_header=is_header,
            is_reconcilable=is_reconcilable,
            currency_id=currency_id,
            opening_debit=opening_debit,
            opening_credit=opening_credit,
            debit_balance=opening_debit,
            credit_balance=opening_credit,
            notes=notes,
            tenant_id=tenant_id,
            created_by_id=created_by_id
        )
        
        # Calculate initial balance
        if account.is_debit_account:
            account.balance = opening_debit - opening_credit
        else:
            account.balance = opening_credit - opening_debit
        
        self.db.add(account)
        await self.db.flush()
        
        return account
    
    async def get_account_tree(
        self,
        tenant_id: UUID,
        account_type: Optional[AccountType] = None
    ) -> List[Dict[str, Any]]:
        """
        Get chart of accounts as a hierarchical tree.
        
        Args:
            tenant_id: Tenant ID
            account_type: Filter by account type (optional)
            
        Returns:
            List of account trees
        """
        query = select(Account).where(
            Account.tenant_id == tenant_id,
            Account.is_deleted == False,
            Account.parent_id == None  # Root accounts only
        ).order_by(Account.code)
        
        if account_type:
            query = query.where(Account.account_type == account_type)
        
        result = await self.db.execute(query)
        root_accounts = result.scalars().all()
        
        trees = []
        for account in root_accounts:
            trees.append(await self._build_account_tree(account, tenant_id))
        
        return trees
    
    async def _build_account_tree(self, account: Account, tenant_id: UUID) -> Dict[str, Any]:
        """Build account tree recursively."""
        tree = {
            "id": account.id,
            "code": account.code,
            "name": account.name,
            "account_type": account.account_type,
            "balance": account.balance,
            "is_header": account.is_header,
            "children": []
        }
        
        # Get children
        result = await self.db.execute(
            select(Account).where(
                Account.parent_id == account.id,
                Account.tenant_id == tenant_id,
                Account.is_deleted == False
            ).order_by(Account.code)
        )
        children = result.scalars().all()
        
        for child in children:
            tree["children"].append(await self._build_account_tree(child, tenant_id))
        
        return tree
    
    async def update_account_balance(
        self,
        account_id: UUID,
        debit: Decimal,
        credit: Decimal,
        tenant_id: UUID
    ) -> Account:
        """
        Update account balance with new amounts.
        
        Args:
            account_id: Account ID
            debit: Debit amount to add
            credit: Credit amount to add
            
        Returns:
            Updated Account record
        """
        account = await self._tenant_record(Account, account_id, tenant_id, "Account")
        
        account.debit_balance += debit
        account.credit_balance += credit
        
        # Calculate net balance based on account type
        if account.is_debit_account:
            account.balance = account.debit_balance - account.credit_balance
        else:
            account.balance = account.credit_balance - account.debit_balance
        
        await self.db.flush()
        return account
    
    # ========================================
    # Journal Entry Operations
    # ========================================
    
    async def create_journal_entry(
        self,
        date: date,
        lines: List[Dict[str, Any]],
        description: Optional[str] = None,
        ref: Optional[str] = None,
        move_type: MoveType = MoveType.MANUAL,
        journal_id: Optional[UUID] = None,
        partner_id: Optional[UUID] = None,
        source_model: Optional[str] = None,
        source_id: Optional[UUID] = None,
        tenant_id: UUID = None,
        created_by_id: Optional[UUID] = None
    ) -> JournalEntry:
        """
        Create a new journal entry.
        
        Args:
            date: Entry date
            lines: List of line items with account_id, debit, credit
            description: Entry description
            ref: Reference number
            move_type: Type of entry
            journal_id: Journal ID
            partner_id: Partner ID
            source_model: Source model name
            source_id: Source document ID
            tenant_id: Tenant ID
            created_by_id: User creating the entry
            
        Returns:
            Created JournalEntry record
            
        Raises:
            ValueError: If entry is not balanced or lines are invalid
        """
        if tenant_id is None:
            raise ValueError("tenant_id is required to create a journal entry")
        if journal_id:
            await self._tenant_record(Journal, journal_id, tenant_id, "Journal")
        if partner_id:
            await self._tenant_record(Partner, partner_id, tenant_id, "Partner")

        # Validate lines
        if len(lines) < 2:
            raise ValueError("Journal entry must have at least 2 lines")
        
        # Normalize and validate monetary values before creating any records.
        normalized_lines = []
        for line_data in lines:
            try:
                debit = Decimal(str(line_data.get("debit", "0")))
                credit = Decimal(str(line_data.get("credit", "0")))
            except Exception as exc:
                raise ValueError("Journal line amounts must be valid decimal numbers") from exc
            if not debit.is_finite() or not credit.is_finite():
                raise ValueError("Journal line amounts must be finite numbers")
            if debit < 0 or credit < 0:
                raise ValueError("Journal line amounts cannot be negative")
            if debit > 0 and credit > 0:
                raise ValueError("A journal line cannot contain both debit and credit")
            normalized_lines.append({**line_data, "debit": debit, "credit": credit})

        total_debit = sum((line["debit"] for line in normalized_lines), Decimal("0"))
        total_credit = sum((line["credit"] for line in normalized_lines), Decimal("0"))

        # The database constraint requires exact equality; do not silently accept a cent difference.
        if total_debit != total_credit:
            raise ValueError(
                f"Journal entry must be exactly balanced. "
                f"Debit: {total_debit}, Credit: {total_credit}"
            )
        
        # Validate every referenced record BEFORE flushing the parent entry. This
        # prevents a bad account/partner/analytic reference from leaving a partial
        # draft journal in the caller's transaction when an integration catches the
        # exception and continues.
        if (source_model is None) != (source_id is None):
            raise ValueError("source_model and source_id must be supplied together")
        if source_model is not None:
            duplicate_source = await self.db.scalar(select(JournalEntry.id).where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.source_model == source_model,
                JournalEntry.source_id == source_id,
                JournalEntry.is_deleted == False
            ).limit(1))
            if duplicate_source is not None:
                raise ValueError("A journal entry already exists for this source document")

        for line_data in normalized_lines:
            account_id = line_data.get("account_id")
            if not account_id:
                raise ValueError("Every journal line must reference an account")
            account = await self._tenant_record(Account, account_id, tenant_id, "Account")
            if account.is_header:
                raise ValueError(f"Cannot post to header account {account.code}")
            line_partner_id = line_data.get("partner_id")
            analytic_account_id = line_data.get("analytic_account_id")
            if line_partner_id:
                await self._tenant_record(Partner, line_partner_id, tenant_id, "Partner")
            if analytic_account_id:
                await self._tenant_record(AnalyticAccount, analytic_account_id, tenant_id, "Analytic account")

        # Generate entry number
        entry_number = await self._generate_entry_number(move_type, tenant_id)
        
        # Get fiscal period
        fiscal_period = await self._get_fiscal_period(date, tenant_id)
        
        # Create entry
        entry = JournalEntry(
            number=entry_number,
            date=date,
            ref=ref,
            description=description,
            move_type=move_type,
            journal_id=journal_id,
            fiscal_period_id=fiscal_period.id if fiscal_period else None,
            total_debit=total_debit,
            total_credit=total_credit,
            source_model=source_model,
            source_id=source_id,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            state=EntryState.DRAFT
        )
        
        self.db.add(entry)
        await self.db.flush()
        
        # Create lines after all referenced records have been validated.
        for idx, line_data in enumerate(normalized_lines):
            account_id = line_data["account_id"]
            line = JournalItem(
                entry_id=entry.id,
                account_id=account_id,
                sequence=(idx + 1) * 10,
                debit=line_data.get("debit", Decimal("0")),
                credit=line_data.get("credit", Decimal("0")),
                date=date,
                name=line_data.get("name"),
                partner_id=line_data.get("partner_id"),
                analytic_account_id=line_data.get("analytic_account_id"),
                tenant_id=tenant_id
            )
            
            self.db.add(line)
        
        await self.db.flush()
        return entry
    
    async def post_journal_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
        tenant_id: UUID
    ) -> JournalEntry:
        """
        Post a journal entry.
        
        Updates account balances and marks entry as posted.
        
        Args:
            entry_id: Journal entry ID
            user_id: User posting the entry
            
        Returns:
            Posted JournalEntry record
        """
        if tenant_id is None:
            raise ValueError("tenant_id is required to post a journal entry")
        # Serialize concurrent posting attempts; a second transaction must see POSTED.
        entry = await self.db.scalar(select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.is_deleted == False
        ).with_for_update())
        if entry is None:
            raise ValueError("Journal entry not found")

        if entry.state != EntryState.DRAFT:
            raise ValueError(f"Cannot post entry in state {entry.state}")
        
        # Load lines
        result = await self.db.execute(
            select(JournalItem).where(
                JournalItem.entry_id == entry_id,
                JournalItem.tenant_id == tenant_id
            )
        )
        lines = result.scalars().all()
        if len(lines) < 2:
            raise ValueError("Journal entry must contain at least two lines")
        total_debit = sum((line.debit or Decimal("0")) for line in lines)
        total_credit = sum((line.credit or Decimal("0")) for line in lines)
        if total_debit != total_credit:
            raise ValueError("Journal entry is not balanced; posting was rejected")
        if (total_debit != (entry.total_debit or Decimal("0")) or
                total_credit != (entry.total_credit or Decimal("0"))):
            raise ValueError("Journal entry totals do not match its lines")

        # Update account balances only after all structural validations pass.
        for line in lines:
            await self.update_account_balance(
                line.account_id,
                line.debit,
                line.credit,
                tenant_id
            )
        
        # Update entry state
        entry.state = EntryState.POSTED
        entry.posted_at = datetime.utcnow()
        entry.posted_by_id = user_id
        
        await self.db.flush()
        return entry
    
    async def reverse_journal_entry(
        self,
        entry_id: UUID,
        reversal_date: Optional[date] = None,
        reason: Optional[str] = None,
        user_id: UUID = None,
        tenant_id: UUID = None
    ) -> JournalEntry:
        """
        Create a reversal entry for a posted entry.
        
        Args:
            entry_id: Original entry ID
            reversal_date: Date for reversal entry
            reason: Reversal reason
            user_id: User creating reversal
            
        Returns:
            New reversal JournalEntry record
        """
        if tenant_id is None:
            raise ValueError("tenant_id is required to reverse a journal entry")
        # Lock the source entry to prevent two concurrent reversal requests.
        original = await self.db.scalar(select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.is_deleted == False
        ).with_for_update())
        if original is None:
            raise ValueError("Journal entry not found")

        if original.state != EntryState.POSTED:
            raise ValueError("Can only reverse posted entries")
        
        existing_reversal = await self.db.scalar(select(JournalEntry.id).where(
            JournalEntry.original_entry_id == original.id,
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.is_reversal == True,
            JournalEntry.is_deleted == False
        ).limit(1))
        if existing_reversal is not None:
            raise ValueError("This journal entry has already been reversed")

        # Load original lines
        result = await self.db.execute(
            select(JournalItem).where(
                JournalItem.entry_id == entry_id,
                JournalItem.tenant_id == tenant_id
            )
        )
        original_lines = result.scalars().all()
        
        # Create reversal lines (swap debit/credit)
        reversal_lines = []
        for line in original_lines:
            reversal_lines.append({
                "account_id": line.account_id,
                "debit": line.credit,  # Swap
                "credit": line.debit,  # Swap
                "name": f"Reversal: {line.name}" if line.name else "Reversal",
                "partner_id": line.partner_id,
                "analytic_account_id": line.analytic_account_id
            })
        
        # Create reversal entry
        reversal = await self.create_journal_entry(
            date=reversal_date or date.today(),
            lines=reversal_lines,
            description=f"Reversal of {original.number}: {reason or ''}",
            move_type=original.move_type,
            journal_id=original.journal_id,
            tenant_id=original.tenant_id,
            created_by_id=user_id
        )
        
        # Mark as reversal
        reversal.is_reversal = True
        reversal.original_entry_id = original.id
        
        # Post the reversal
        await self.post_journal_entry(reversal.id, user_id, tenant_id)
        
        return reversal
    
    # ========================================
    # Financial Reports
    # ========================================
    
    async def get_trial_balance(
        self,
        date_from: date,
        date_to: date,
        tenant_id: UUID,
        include_zero_balances: bool = False
    ) -> Dict[str, Any]:
        """
        Generate trial balance report.
        
        Args:
            date_from: Start date
            date_to: End date
            tenant_id: Tenant ID
            include_zero_balances: Include accounts with zero balance
            
        Returns:
            Trial balance report data
        """
        # Get all active accounts
        query = select(Account).where(
            Account.tenant_id == tenant_id,
            Account.is_deleted == False,
            Account.is_header == False
        ).order_by(Account.code)
        
        result = await self.db.execute(query)
        accounts = result.scalars().all()
        
        lines = []
        total_opening_debit = Decimal("0")
        total_opening_credit = Decimal("0")
        total_period_debit = Decimal("0")
        total_period_credit = Decimal("0")
        total_closing_debit = Decimal("0")
        total_closing_credit = Decimal("0")
        
        for account in accounts:
            # Opening balance (from previous entries)
            opening_result = await self.db.execute(
                select(
                    func.coalesce(func.sum(JournalItem.debit), Decimal("0")).label("debit"),
                    func.coalesce(func.sum(JournalItem.credit), Decimal("0")).label("credit")
                ).join(JournalEntry).where(
                    JournalItem.account_id == account.id,
                    JournalEntry.date < date_from,
                    JournalEntry.state == EntryState.POSTED,
                    JournalEntry.tenant_id == tenant_id
                )
            )
            opening = opening_result.one()
            
            # Period movements
            period_result = await self.db.execute(
                select(
                    func.coalesce(func.sum(JournalItem.debit), Decimal("0")).label("debit"),
                    func.coalesce(func.sum(JournalItem.credit), Decimal("0")).label("credit")
                ).join(JournalEntry).where(
                    JournalItem.account_id == account.id,
                    JournalEntry.date >= date_from,
                    JournalEntry.date <= date_to,
                    JournalEntry.state == EntryState.POSTED,
                    JournalEntry.tenant_id == tenant_id
                )
            )
            period = period_result.one()
            
            # Calculate closing balance
            closing_debit = opening.debit + period.debit
            closing_credit = opening.credit + period.credit
            
            # Skip if zero balances not included
            if not include_zero_balances:
                if closing_debit == 0 and closing_credit == 0:
                    continue
            
            lines.append({
                "account_id": account.id,
                "account_code": account.code,
                "account_name": account.name,
                "account_type": account.account_type,
                "opening_debit": opening.debit,
                "opening_credit": opening.credit,
                "period_debit": period.debit,
                "period_credit": period.credit,
                "closing_debit": closing_debit,
                "closing_credit": closing_credit
            })
            
            total_opening_debit += opening.debit
            total_opening_credit += opening.credit
            total_period_debit += period.debit
            total_period_credit += period.credit
            total_closing_debit += closing_debit
            total_closing_credit += closing_credit
        
        return {
            "date_from": date_from,
            "date_to": date_to,
            "generated_at": datetime.utcnow(),
            "total_opening_debit": total_opening_debit,
            "total_opening_credit": total_opening_credit,
            "total_period_debit": total_period_debit,
            "total_period_credit": total_period_credit,
            "total_closing_debit": total_closing_debit,
            "total_closing_credit": total_closing_credit,
            "is_balanced": abs(total_closing_debit - total_closing_credit) < Decimal("0.01"),
            "lines": lines
        }
    
    async def get_general_ledger(
        self,
        account_id: Optional[UUID] = None,
        account_codes: Optional[List[str]] = None,
        date_from: date = None,
        date_to: date = None,
        partner_id: Optional[UUID] = None,
        tenant_id: UUID = None
    ) -> Dict[str, Any]:
        """
        Generate general ledger report for an account.
        
        Args:
            account_id: Account ID
            account_codes: List of account codes
            date_from: Start date
            date_to: End date
            partner_id: Filter by partner
            tenant_id: Tenant ID
            
        Returns:
            General ledger report data
        """
        # Build query for journal items
        query = select(JournalItem).options(
            selectinload(JournalItem.account),
            selectinload(JournalItem.entry)
        ).join(JournalEntry).where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.state == EntryState.POSTED,
            JournalEntry.date >= date_from,
            JournalEntry.date <= date_to
        )
        
        if account_id:
            query = query.where(JournalItem.account_id == account_id)
        
        if account_codes:
            query = query.join(Account).where(Account.code.in_(account_codes))
        
        if partner_id:
            query = query.where(JournalItem.partner_id == partner_id)
        
        query = query.order_by(JournalEntry.date, JournalItem.sequence)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        # Build report
        lines = []
        running_balance = Decimal("0")
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        
        for item in items:
            running_balance += item.debit - item.credit
            total_debit += item.debit
            total_credit += item.credit
            
            lines.append({
                "date": item.date,
                "entry_number": item.entry.number,
                "entry_id": item.entry_id,
                "account_code": item.account.code if item.account else None,
                "account_name": item.account.name if item.account else None,
                "description": item.name,
                "debit": item.debit,
                "credit": item.credit,
                "balance": item.debit - item.credit,
                "running_balance": running_balance,
                "ref": item.entry.ref
            })
        
        return {
            "account_id": account_id,
            "date_from": date_from,
            "date_to": date_to,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "lines": lines
        }
    
    async def get_income_statement(
        self,
        date_from: date,
        date_to: date,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """
        Generate income statement (profit and loss).
        
        Args:
            date_from: Start date
            date_to: End date
            tenant_id: Tenant ID
            
        Returns:
            Income statement data
        """
        # Revenue accounts
        revenue_result = await self.db.execute(
            select(Account).where(
                Account.tenant_id == tenant_id,
                Account.account_type == AccountType.REVENUE,
                Account.is_deleted == False,
                Account.is_header == False
            )
        )
        revenue_accounts = revenue_result.scalars().all()
        
        # Expense accounts
        expense_result = await self.db.execute(
            select(Account).where(
                Account.tenant_id == tenant_id,
                Account.account_type == AccountType.EXPENSE,
                Account.is_deleted == False,
                Account.is_header == False
            )
        )
        expense_accounts = expense_result.scalars().all()
        
        # Calculate revenue
        revenue_lines = []
        total_revenue = Decimal("0")
        
        for account in revenue_accounts:
            result = await self.db.execute(
                select(
                    func.coalesce(func.sum(JournalItem.credit) - func.sum(JournalItem.debit), Decimal("0"))
                ).join(JournalEntry).where(
                    JournalItem.account_id == account.id,
                    JournalEntry.date >= date_from,
                    JournalEntry.date <= date_to,
                    JournalEntry.state == EntryState.POSTED
                )
            )
            amount = result.scalar() or Decimal("0")
            
            revenue_lines.append({
                "account_id": account.id,
                "account_code": account.code,
                "account_name": account.name,
                "amount": amount
            })
            total_revenue += amount
        
        # Calculate expenses
        expense_lines = []
        total_expenses = Decimal("0")
        
        for account in expense_accounts:
            result = await self.db.execute(
                select(
                    func.coalesce(func.sum(JournalItem.debit) - func.sum(JournalItem.credit), Decimal("0"))
                ).join(JournalEntry).where(
                    JournalItem.account_id == account.id,
                    JournalEntry.date >= date_from,
                    JournalEntry.date <= date_to,
                    JournalEntry.state == EntryState.POSTED
                )
            )
            amount = result.scalar() or Decimal("0")
            
            expense_lines.append({
                "account_id": account.id,
                "account_code": account.code,
                "account_name": account.name,
                "amount": amount
            })
            total_expenses += amount
        
        net_income = total_revenue - total_expenses
        
        return {
            "date_from": date_from,
            "date_to": date_to,
            "generated_at": datetime.utcnow(),
            "revenue": {
                "title": "Revenue",
                "total": total_revenue,
                "lines": revenue_lines
            },
            "expenses": {
                "title": "Expenses",
                "total": total_expenses,
                "lines": expense_lines
            },
            "gross_profit": total_revenue,
            "total_expenses": total_expenses,
            "net_income": net_income
        }
    
    async def get_balance_sheet(
        self,
        as_of_date: date,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """
        Generate balance sheet.
        
        Args:
            as_of_date: As of date
            tenant_id: Tenant ID
            
        Returns:
            Balance sheet data
        """
        # Asset accounts
        assets_result = await self.db.execute(
            select(Account).where(
                Account.tenant_id == tenant_id,
                Account.account_type == AccountType.ASSET,
                Account.is_deleted == False,
                Account.is_header == False
            )
        )
        asset_accounts = assets_result.scalars().all()
        
        # Liability accounts
        liabilities_result = await self.db.execute(
            select(Account).where(
                Account.tenant_id == tenant_id,
                Account.account_type == AccountType.LIABILITY,
                Account.is_deleted == False,
                Account.is_header == False
            )
        )
        liability_accounts = liabilities_result.scalars().all()
        
        # Equity accounts
        equity_result = await self.db.execute(
            select(Account).where(
                Account.tenant_id == tenant_id,
                Account.account_type == AccountType.EQUITY,
                Account.is_deleted == False,
                Account.is_header == False
            )
        )
        equity_accounts = equity_result.scalars().all()
        
        # Calculate assets
        asset_lines = []
        total_assets = Decimal("0")
        
        for account in asset_accounts:
            result = await self.db.execute(
                select(
                    func.coalesce(func.sum(JournalItem.debit) - func.sum(JournalItem.credit), Decimal("0"))
                ).join(JournalEntry).where(
                    JournalItem.account_id == account.id,
                    JournalEntry.date <= as_of_date,
                    JournalEntry.state == EntryState.POSTED
                )
            )
            amount = result.scalar() or Decimal("0")
            
            asset_lines.append({
                "account_id": account.id,
                "account_code": account.code,
                "account_name": account.name,
                "amount": amount
            })
            total_assets += amount
        
        # Calculate liabilities
        liability_lines = []
        total_liabilities = Decimal("0")
        
        for account in liability_accounts:
            result = await self.db.execute(
                select(
                    func.coalesce(func.sum(JournalItem.credit) - func.sum(JournalItem.debit), Decimal("0"))
                ).join(JournalEntry).where(
                    JournalItem.account_id == account.id,
                    JournalEntry.date <= as_of_date,
                    JournalEntry.state == EntryState.POSTED
                )
            )
            amount = result.scalar() or Decimal("0")
            
            liability_lines.append({
                "account_id": account.id,
                "account_code": account.code,
                "account_name": account.name,
                "amount": amount
            })
            total_liabilities += amount
        
        # Calculate equity
        equity_lines = []
        total_equity = Decimal("0")
        
        for account in equity_accounts:
            result = await self.db.execute(
                select(
                    func.coalesce(func.sum(JournalItem.credit) - func.sum(JournalItem.debit), Decimal("0"))
                ).join(JournalEntry).where(
                    JournalItem.account_id == account.id,
                    JournalEntry.date <= as_of_date,
                    JournalEntry.state == EntryState.POSTED
                )
            )
            amount = result.scalar() or Decimal("0")
            
            equity_lines.append({
                "account_id": account.id,
                "account_code": account.code,
                "account_name": account.name,
                "amount": amount
            })
            total_equity += amount
        
        return {
            "date": as_of_date,
            "generated_at": datetime.utcnow(),
            "assets": {
                "title": "Assets",
                "total": total_assets,
                "lines": asset_lines
            },
            "liabilities": {
                "title": "Liabilities",
                "total": total_liabilities,
                "lines": liability_lines
            },
            "equity": {
                "title": "Equity",
                "total": total_equity,
                "lines": equity_lines
            },
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "total_liabilities_and_equity": total_liabilities + total_equity,
            "is_balanced": abs(total_assets - (total_liabilities + total_equity)) < Decimal("0.01")
        }
    
    # ========================================
    # Helper Methods
    # ========================================
    
    async def _generate_entry_number(self, move_type: MoveType, tenant_id: UUID) -> str:
        """Generate a unique journal entry number."""
        prefix_map = {
            MoveType.MANUAL: "JE",
            MoveType.SALES: "SI",
            MoveType.PURCHASE: "PI",
            MoveType.PAYMENT: "PAY",
            MoveType.RECEIPT: "REC",
            MoveType.TRANSFER: "TRF",
            MoveType.ADJUSTMENT: "ADJ",
            MoveType.CLOSING: "CLO",
            MoveType.OPENING: "OPN"
        }
        
        prefix = prefix_map.get(move_type, "JE")
        
        result = await self.db.execute(
            select(func.count()).select_from(JournalEntry).where(
                JournalEntry.tenant_id == tenant_id
            )
        )
        count = result.scalar() or 0
        
        return f"{prefix}-{date.today().year}-{count + 1:06d}"
    
    async def _get_fiscal_period(
        self,
        entry_date: date,
        tenant_id: UUID
    ) -> Optional[FiscalPeriod]:
        """Get the fiscal period for a given date."""
        result = await self.db.execute(
            select(FiscalPeriod).join(FiscalYear).where(
                FiscalYear.tenant_id == tenant_id,
                FiscalPeriod.start_date <= entry_date,
                FiscalPeriod.end_date >= entry_date,
                FiscalPeriod.is_closed == False
            )
        )
        return result.scalar_one_or_none()
    
    async def get_account_by_code(
        self,
        code: str,
        tenant_id: UUID
    ) -> Optional[Account]:
        """Get account by code."""
        result = await self.db.execute(
            select(Account).where(
                Account.code == code,
                Account.tenant_id == tenant_id,
                Account.is_deleted == False
            )
        )
        return result.scalar_one_or_none()
    
    async def get_or_create_default_accounts(
        self,
        tenant_id: UUID
    ) -> Dict[str, Account]:
        """
        Get or create default chart of accounts for a new tenant.
        
        Returns:
            Dictionary with default account codes and accounts
        """
        defaults = {}
        
        # Define default accounts
        default_accounts = [
            ("1000", "Cash", AccountType.ASSET, AccountCategory.CASH),
            ("1100", "Accounts Receivable", AccountType.ASSET, AccountCategory.RECEIVABLE),
            ("1200", "Inventory", AccountType.ASSET, AccountCategory.INVENTORY),
            ("1500", "Fixed Assets", AccountType.ASSET, AccountCategory.FIXED_ASSET),
            ("2000", "Accounts Payable", AccountType.LIABILITY, AccountCategory.PAYABLE),
            ("2100", "Tax Payable", AccountType.LIABILITY, AccountCategory.TAX),
            ("3000", "Capital", AccountType.EQUITY, AccountCategory.CAPITAL),
            ("3100", "Retained Earnings", AccountType.EQUITY, AccountCategory.CAPITAL),
            ("4000", "Sales Revenue", AccountType.REVENUE, AccountCategory.SALES),
            ("5000", "Cost of Goods Sold", AccountType.EXPENSE, AccountCategory.COST_OF_SALES),
            ("6000", "Operating Expenses", AccountType.EXPENSE, AccountCategory.OPERATING_EXPENSE),
        ]
        
        for code, name, acc_type, category in default_accounts:
            account = await self.get_account_by_code(code, tenant_id)
            if not account:
                account = await self.create_account(
                    code=code,
                    name=name,
                    account_type=acc_type,
                    category=category,
                    tenant_id=tenant_id
                )
            defaults[code] = account
        
        return defaults
