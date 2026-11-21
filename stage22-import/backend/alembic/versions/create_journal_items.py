"""Create analytic accounting and journal item tables required by bank reconciliation.

Revision ID: create_journal_items
Revises: supp_payment_reverse_19
Create Date: 2026-11-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "create_journal_items"
down_revision = "supp_payment_reverse_19"
branch_labels = None
depends_on = None


def _base_columns():
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
    ]


def _tenant_constraints():
    return [
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    ]


def _base_indexes(table_name):
    op.create_index(f"ix_{table_name}_tenant_id", table_name, ["tenant_id"])
    op.create_index(f"ix_{table_name}_is_deleted", table_name, ["is_deleted"])


def upgrade() -> None:
    # JournalItem references these two accounting dimensions, so they must exist
    # before journal_items is created. Their shape follows app/models/accounting.py.
    op.create_table(
        "analytic_accounts",
        *_base_columns(),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("debit_balance", sa.Numeric(18, 4), nullable=True),
        sa.Column("credit_balance", sa.Numeric(18, 4), nullable=True),
        sa.Column("balance", sa.Numeric(18, 4), nullable=True),
        *_tenant_constraints(),
        sa.ForeignKeyConstraint(["parent_id"], ["analytic_accounts.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_analytic_accounts_code", "analytic_accounts", ["code"])
    _base_indexes("analytic_accounts")

    op.create_table(
        "reconciliations",
        *_base_columns(),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("total_debit", sa.Numeric(18, 4), nullable=True),
        sa.Column("total_credit", sa.Numeric(18, 4), nullable=True),
        sa.Column("is_full", sa.Boolean(), nullable=True),
        sa.Column("is_partial", sa.Boolean(), nullable=True),
        *_tenant_constraints(),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
    )
    _base_indexes("reconciliations")

    op.create_table(
        "journal_items",
        *_base_columns(),
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("debit", sa.Numeric(18, 4), nullable=False),
        sa.Column("credit", sa.Numeric(18, 4), nullable=False),
        sa.Column("balance_after", sa.Numeric(18, 4), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("partner_type", sa.String(length=20), nullable=True),
        sa.Column("analytic_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reconciliation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("source_model", sa.String(length=100), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount_currency", sa.Numeric(18, 4), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_tenant_constraints(),
        sa.ForeignKeyConstraint(["entry_id"], ["journal_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["analytic_account_id"], ["analytic_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reconciliation_id"], ["reconciliations.id"], ondelete="SET NULL"),
        sa.CheckConstraint("debit >= 0 AND credit >= 0", name="ck_journal_item_amounts_positive"),
        sa.CheckConstraint("NOT (debit > 0 AND credit > 0)", name="ck_journal_item_not_both"),
    )
    op.create_index("ix_journal_items_entry", "journal_items", ["entry_id"])
    op.create_index("ix_journal_items_account", "journal_items", ["account_id"])
    op.create_index("ix_journal_items_partner", "journal_items", ["partner_id"])
    op.create_index("ix_journal_items_date", "journal_items", ["date"])
    _base_indexes("journal_items")

    op.create_table(
        "analytic_lines",
        *_base_columns(),
        sa.Column("journal_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analytic_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("percentage", sa.Numeric(5, 2), nullable=True),
        *_tenant_constraints(),
        sa.ForeignKeyConstraint(["journal_item_id"], ["journal_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analytic_account_id"], ["analytic_accounts.id"]),
    )
    _base_indexes("analytic_lines")


def downgrade() -> None:
    op.drop_table("analytic_lines")
    op.drop_table("journal_items")
    op.drop_table("reconciliations")
    op.drop_table("analytic_accounts")
