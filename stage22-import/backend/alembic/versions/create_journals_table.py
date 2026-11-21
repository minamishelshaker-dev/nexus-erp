"""Create the journals table required by supplier payment posting.

Revision ID: create_journals_table
Revises: add_journal_source_idempotency
Create Date: 2026-11-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "create_journals_table"
down_revision = "create_accounts_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "journals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("journal_type", sa.String(length=20), nullable=False),
        sa.Column("default_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sequence_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["default_account_id"], ["accounts.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_journals_code_tenant", "journals", ["code", "tenant_id"], unique=True)
    op.create_index("ix_journals_tenant_id", "journals", ["tenant_id"])
    op.create_index("ix_journals_is_deleted", "journals", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_journals_is_deleted", table_name="journals")
    op.drop_index("ix_journals_tenant_id", table_name="journals")
    op.drop_index("ix_journals_code_tenant", table_name="journals")
    op.drop_table("journals")
