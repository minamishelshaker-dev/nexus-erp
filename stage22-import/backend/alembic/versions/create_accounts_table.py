"""Create accounting currencies and tenant-scoped chart accounts.

Revision ID: create_accounts_table
Revises: add_journal_source_idempotency
Create Date: 2026-11-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "create_accounts_table"
down_revision = "add_journal_source_idempotency"
branch_labels = None
depends_on = None

account_type = postgresql.ENUM(
    "asset", "liability", "equity", "revenue", "expense",
    "contra_asset", "contra_liability", "contra_equity",
    "contra_revenue", "contra_expense",
    name="accounttype",
)
account_category = postgresql.ENUM(
    "cash", "bank", "receivable", "inventory", "fixed_asset",
    "payable", "tax", "capital", "sales", "cost_of_sales",
    "operating_expense", "other_income", "other_expense",
    name="accountcategory",
)


def upgrade() -> None:
    bind = op.get_bind()
    account_type.create(bind, checkfirst=True)
    account_category.create(bind, checkfirst=True)

    op.create_table(
        "currencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(3), nullable=False, unique=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(10), nullable=False),
        sa.Column("decimal_places", sa.Integer(), nullable=True, server_default="2"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_ar", sa.String(255), nullable=True),
        sa.Column("account_type", account_type, nullable=False),
        sa.Column("category", account_category, nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_parent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_header", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_reconcilable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_contra", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("debit_balance", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("credit_balance", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("balance", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("opening_debit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("opening_credit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("partner_type", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'::varchar[]")),
        sa.Column("custom_fields", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["currency_id"], ["currencies.id"], ondelete="SET NULL"),
        sa.CheckConstraint("debit_balance >= 0", name="ck_account_debit_balance"),
        sa.CheckConstraint("credit_balance >= 0", name="ck_account_credit_balance"),
    )
    op.create_index("ix_accounts_code_tenant", "accounts", ["code", "tenant_id"], unique=True)
    op.create_index("ix_accounts_parent", "accounts", ["parent_id"])
    op.create_index("ix_accounts_type", "accounts", ["account_type"])
    op.create_index("ix_accounts_tenant", "accounts", ["tenant_id"])
    op.create_index("ix_accounts_tenant_id", "accounts", ["tenant_id"])
    op.create_index("ix_accounts_is_deleted", "accounts", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_accounts_is_deleted", table_name="accounts")
    op.drop_index("ix_accounts_tenant_id", table_name="accounts")
    op.drop_index("ix_accounts_tenant", table_name="accounts")
    op.drop_index("ix_accounts_type", table_name="accounts")
    op.drop_index("ix_accounts_parent", table_name="accounts")
    op.drop_index("ix_accounts_code_tenant", table_name="accounts")
    op.drop_table("accounts")
    op.drop_table("currencies")
    account_category.drop(op.get_bind(), checkfirst=True)
    account_type.drop(op.get_bind(), checkfirst=True)
