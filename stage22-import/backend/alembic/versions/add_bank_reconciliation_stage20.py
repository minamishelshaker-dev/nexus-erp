"""Add tenant-scoped bank statements and statement lines.

Revision ID: add_bank_reconciliation_stage20
Revises: add_supplier_payment_reversal_stage19
Create Date: 2026-11-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "add_bank_reconciliation_stage20"
down_revision = "create_journal_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bank_statements",
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("statement_number", sa.String(length=100), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("opening_balance", sa.Numeric(18, 4), nullable=False),
        sa.Column("closing_balance", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_debits", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_credits", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("currency_code", sa.String(length=3), nullable=True),
        sa.Column("state", sa.Enum("draft", "in_progress", "reconciled", "cancelled", name="bankstatementstate"), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "account_id", "statement_number", name="uq_bank_statement_tenant_account_number"),
        sa.CheckConstraint("end_date >= start_date", name="ck_bank_statement_date_range"),
    )
    op.create_index("ix_bank_statements_tenant_account_period", "bank_statements", ["tenant_id", "account_id", "start_date", "end_date"])
    op.create_table(
        "bank_statement_lines",
        sa.Column("statement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("external_reference", sa.String(length=150), nullable=True),
        sa.Column("debit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("matched_journal_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("matched_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["statement_id"], ["bank_statements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matched_journal_item_id"], ["journal_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["matched_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "statement_id", "line_number", name="uq_bank_statement_line_number"),
        sa.UniqueConstraint("tenant_id", "matched_journal_item_id", name="uq_bank_statement_matched_journal_item"),
        sa.CheckConstraint("debit >= 0 AND credit >= 0", name="ck_bank_statement_line_nonnegative"),
        sa.CheckConstraint("NOT (debit > 0 AND credit > 0)", name="ck_bank_statement_line_one_side"),
        sa.CheckConstraint("debit > 0 OR credit > 0", name="ck_bank_statement_line_positive"),
    )
    op.create_index("ix_bank_statement_lines_tenant_statement", "bank_statement_lines", ["tenant_id", "statement_id"])
    op.create_index(
        "uq_bank_statement_external_reference", "bank_statement_lines",
        ["tenant_id", "statement_id", "external_reference"], unique=True,
        postgresql_where=sa.text("external_reference IS NOT NULL AND is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("uq_bank_statement_external_reference", table_name="bank_statement_lines")
    op.drop_index("ix_bank_statement_lines_tenant_statement", table_name="bank_statement_lines")
    op.drop_table("bank_statement_lines")
    op.drop_index("ix_bank_statements_tenant_account_period", table_name="bank_statements")
    op.drop_table("bank_statements")
    op.execute("DROP TYPE IF EXISTS bankstatementstate")
