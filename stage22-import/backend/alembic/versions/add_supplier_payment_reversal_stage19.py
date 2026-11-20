"""Link supplier payment cancellations to their reversal journal entry.

Revision ID: add_supplier_payment_reversal_stage19
Revises: add_supplier_payments_stage18
Create Date: 2026-11-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "add_supplier_payment_reversal_stage19"
down_revision = "add_supplier_payments_stage18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "supplier_payments",
        sa.Column("reversal_journal_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_supplier_payments_reversal_journal_entry",
        "supplier_payments", "journal_entries",
        ["reversal_journal_entry_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index(
        "ix_supplier_payments_reversal_journal_entry_id",
        "supplier_payments", ["reversal_journal_entry_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_supplier_payments_reversal_journal_entry_id", table_name="supplier_payments")
    op.drop_constraint("fk_supplier_payments_reversal_journal_entry", "supplier_payments", type_="foreignkey")
    op.drop_column("supplier_payments", "reversal_journal_entry_id")
