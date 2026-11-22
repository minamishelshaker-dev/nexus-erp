"""Align bank statement soft-delete timestamps with the shared ORM base model.

Revision ID: fix_bank_deleted_at_timezone
Revises: add_bank_reconciliation_stage20
Create Date: 2026-11-21
"""
from alembic import op
import sqlalchemy as sa

revision = "fix_bank_deleted_at_timezone"
down_revision = "add_bank_reconciliation_stage20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # BaseModel.deleted_at is DateTime(timezone=True). The preceding bank
    # reconciliation revision accidentally created these two columns as
    # timestamp without time zone. Existing naive values are interpreted as
    # UTC explicitly; do not rely on the PostgreSQL session TimeZone setting.
    for table_name in ("bank_statements", "bank_statement_lines"):
        op.alter_column(
            table_name,
            "deleted_at",
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=True,
            postgresql_using='"deleted_at" AT TIME ZONE \'UTC\'',
        )


def downgrade() -> None:
    # Preserve the instant while returning to the old naive-UTC representation.
    for table_name in ("bank_statement_lines", "bank_statements"):
        op.alter_column(
            table_name,
            "deleted_at",
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=True,
            postgresql_using='"deleted_at" AT TIME ZONE \'UTC\'',
        )
