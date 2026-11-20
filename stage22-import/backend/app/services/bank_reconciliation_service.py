"""Tenant-scoped bank statement import and matching primitives."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import (
    Account, AccountCategory, BankStatement, BankStatementLine,
    BankStatementState, JournalEntry, JournalItem, EntryState,
)


class BankReconciliationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _statement(self, statement_id: UUID, tenant_id: UUID, lock: bool = False):
        q = select(BankStatement).where(
            BankStatement.id == statement_id,
            BankStatement.tenant_id == tenant_id,
            BankStatement.is_deleted.is_(False),
        )
        if lock:
            q = q.with_for_update()
        statement = await self.db.scalar(q)
        if statement is None:
            raise ValueError("Bank statement not found")
        return statement

    async def create_statement(self, *, account_id: UUID, statement_number: str,
                               start_date, end_date, opening_balance: Decimal,
                               closing_balance: Decimal, tenant_id: UUID,
                               created_by_id: UUID, currency_code=None, notes=None):
        if not tenant_id:
            raise ValueError("tenant_id is required")
        if end_date < start_date:
            raise ValueError("Statement end date must not precede start date")
        account = await self.db.scalar(select(Account).where(
            Account.id == account_id, Account.tenant_id == tenant_id,
            Account.is_deleted.is_(False), Account.is_active.is_(True),
        ).with_for_update())
        if account is None:
            raise ValueError("Bank account not found")
        if account.category != AccountCategory.BANK or not account.is_reconcilable:
            raise ValueError("Selected account must be an active, reconcilable bank account")
        if not statement_number.strip():
            raise ValueError("Statement number is required")
        statement = BankStatement(
            account_id=account_id, statement_number=statement_number.strip(),
            start_date=start_date, end_date=end_date,
            opening_balance=Decimal(str(opening_balance)),
            closing_balance=Decimal(str(closing_balance)),
            currency_code=currency_code.upper() if currency_code else None,
            notes=notes, tenant_id=tenant_id, created_by_id=created_by_id,
        )
        self.db.add(statement)
        await self.db.flush()
        return statement

    async def add_line(self, *, statement_id: UUID, tenant_id: UUID, line_number: int,
                       transaction_date, description: str, debit=Decimal("0"),
                       credit=Decimal("0"), value_date=None, external_reference=None,
                       created_by_id=None):
        statement = await self._statement(statement_id, tenant_id, lock=True)
        if statement.state != BankStatementState.DRAFT:
            raise ValueError("Lines can only be added to a draft statement")
        if transaction_date < statement.start_date or transaction_date > statement.end_date:
            raise ValueError("Transaction date is outside the statement period")
        debit, credit = Decimal(str(debit)), Decimal(str(credit))
        if not debit.is_finite() or not credit.is_finite() or debit < 0 or credit < 0:
            raise ValueError("Statement amounts must be finite and non-negative")
        if (debit > 0) == (credit > 0):
            raise ValueError("Exactly one of debit or credit must be greater than zero")
        if not description.strip() or line_number < 1:
            raise ValueError("A description and positive line number are required")
        line = BankStatementLine(
            statement_id=statement.id, line_number=line_number,
            transaction_date=transaction_date, value_date=value_date,
            description=description.strip(), external_reference=external_reference,
            debit=debit, credit=credit, tenant_id=tenant_id,
            created_by_id=created_by_id,
        )
        self.db.add(line)
        await self.db.flush()
        return line

    async def match_line(self, *, statement_id: UUID, line_id: UUID,
                         journal_item_id: UUID, tenant_id: UUID, user_id: UUID):
        statement = await self._statement(statement_id, tenant_id, lock=True)
        if statement.state not in (BankStatementState.DRAFT, BankStatementState.IN_PROGRESS):
            raise ValueError("Statement is not open for matching")
        line = await self.db.scalar(select(BankStatementLine).where(
            BankStatementLine.id == line_id,
            BankStatementLine.statement_id == statement.id,
            BankStatementLine.tenant_id == tenant_id,
            BankStatementLine.is_deleted.is_(False),
        ).with_for_update())
        if line is None:
            raise ValueError("Statement line not found")
        if line.matched_journal_item_id:
            raise ValueError("Statement line is already matched")
        journal_line = await self.db.scalar(select(JournalItem).join(
            JournalEntry, JournalEntry.id == JournalItem.entry_id
        ).where(
            JournalItem.id == journal_item_id,
            JournalItem.tenant_id == tenant_id,
            JournalItem.is_deleted.is_(False),
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.is_deleted.is_(False),
            JournalEntry.state == EntryState.POSTED,
            JournalItem.account_id == statement.account_id,
        ).with_for_update())
        if journal_line is None:
            raise ValueError("Posted journal line for this bank account was not found")
        # Bank statements are from the bank's perspective: a bank credit is an
        # inflow and corresponds to a debit on the company's bank asset account.
        if line.credit > 0:
            amount_matches = journal_line.debit == line.credit and journal_line.credit == 0
        else:
            amount_matches = journal_line.credit == line.debit and journal_line.debit == 0
        if not amount_matches:
            raise ValueError("Statement movement does not match journal amount and direction")
        if journal_line.date != line.transaction_date:
            raise ValueError("Transaction dates do not match; use a separately approved adjustment workflow")
        line.matched_journal_item_id = journal_line.id
        line.matched_at = datetime.utcnow()
        line.matched_by_id = user_id
        statement.state = BankStatementState.IN_PROGRESS
        await self.db.flush()
        return line

    async def finalize_statement(self, *, statement_id: UUID, tenant_id: UUID):
        statement = await self._statement(statement_id, tenant_id, lock=True)
        if statement.state not in (BankStatementState.DRAFT, BankStatementState.IN_PROGRESS):
            raise ValueError("Statement cannot be finalized in its current state")
        totals = await self.db.execute(select(
            func.coalesce(func.sum(BankStatementLine.debit), 0),
            func.coalesce(func.sum(BankStatementLine.credit), 0),
        ).where(
            BankStatementLine.statement_id == statement.id,
            BankStatementLine.tenant_id == tenant_id,
            BankStatementLine.is_deleted.is_(False),
        ))
        total_debits, total_credits = totals.one()
        total_debits, total_credits = Decimal(str(total_debits)), Decimal(str(total_credits))
        calculated_closing = statement.opening_balance + total_credits - total_debits
        if calculated_closing != statement.closing_balance:
            raise ValueError(
                f"Statement does not balance: expected closing {statement.closing_balance}, "
                f"calculated {calculated_closing}"
            )
        unmatched = await self.db.scalar(select(func.count()).select_from(BankStatementLine).where(
            BankStatementLine.statement_id == statement.id,
            BankStatementLine.tenant_id == tenant_id,
            BankStatementLine.is_deleted.is_(False),
            BankStatementLine.matched_journal_item_id.is_(None),
        ))
        if unmatched:
            raise ValueError(f"Cannot finalize: {unmatched} statement line(s) remain unmatched")
        statement.total_debits = total_debits
        statement.total_credits = total_credits
        statement.state = BankStatementState.RECONCILED
        await self.db.flush()
        return statement
