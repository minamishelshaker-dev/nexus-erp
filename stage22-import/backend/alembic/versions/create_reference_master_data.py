"""Create CRM and organization reference/master-data tables.

Revision ID: create_reference_master_data
Revises: fix_bank_deleted_at_timezone
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "create_reference_master_data"
down_revision = "fix_bank_deleted_at_timezone"
branch_labels = None
depends_on = None


def _common_columns():
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
    ]


def _create_simple(table, extra, constraints=(), indexes=()):
    op.create_table(table, *_common_columns(), *extra, *constraints)
    for name, columns in indexes:
        op.create_index(name, table, columns)


def upgrade():
    _create_simple(
        "industries",
        [sa.Column("code", sa.String(40), nullable=False), sa.Column("name", sa.String(160), nullable=False),
         sa.Column("description", sa.Text(), nullable=True), sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False)],
        [sa.UniqueConstraint("tenant_id", "code", name="uq_industries_tenant_code")],
        [("ix_industries_tenant_name", ["tenant_id", "name"])],
    )
    _create_simple(
        "payment_terms",
        [sa.Column("code", sa.String(40), nullable=False), sa.Column("name", sa.String(160), nullable=False),
         sa.Column("description", sa.Text(), nullable=True), sa.Column("due_days", sa.Integer(), server_default="0", nullable=False),
         sa.Column("discount_days", sa.Integer(), server_default="0", nullable=False),
         sa.Column("discount_percent", sa.Numeric(5, 2), server_default="0", nullable=False),
         sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False)],
        [sa.UniqueConstraint("tenant_id", "code", name="uq_payment_terms_tenant_code"),
         sa.CheckConstraint("due_days >= 0", name="ck_payment_terms_due_days_nonnegative"),
         sa.CheckConstraint("discount_days >= 0", name="ck_payment_terms_discount_days_nonnegative"),
         sa.CheckConstraint("discount_percent >= 0 AND discount_percent <= 100", name="ck_payment_terms_discount_percent_range")],
        [("ix_payment_terms_tenant_name", ["tenant_id", "name"])],
    )
    _create_simple(
        "price_lists",
        [sa.Column("code", sa.String(40), nullable=False), sa.Column("name", sa.String(160), nullable=False),
         sa.Column("description", sa.Text(), nullable=True),
         sa.Column("currency_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("currencies.id", ondelete="RESTRICT"), nullable=True),
         sa.Column("price_list_type", sa.String(30), server_default="sales", nullable=False),
         sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
         sa.Column("settings", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False)],
        [sa.UniqueConstraint("tenant_id", "code", name="uq_price_lists_tenant_code")],
        [("ix_price_lists_tenant_name", ["tenant_id", "name"]), ("ix_price_lists_currency", ["currency_id"])],
    )
    _create_simple(
        "territories",
        [sa.Column("code", sa.String(40), nullable=False), sa.Column("name", sa.String(160), nullable=False),
         sa.Column("description", sa.Text(), nullable=True),
         sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("territories.id", ondelete="SET NULL"), nullable=True),
         sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False)],
        [sa.UniqueConstraint("tenant_id", "code", name="uq_territories_tenant_code")],
        [("ix_territories_parent", ["parent_id"]), ("ix_territories_tenant_name", ["tenant_id", "name"])],
    )
    _create_simple(
        "customer_groups",
        [sa.Column("code", sa.String(40), nullable=False), sa.Column("name", sa.String(160), nullable=False),
         sa.Column("description", sa.Text(), nullable=True), sa.Column("credit_limit", sa.Numeric(18, 2), server_default="0", nullable=False),
         sa.Column("payment_terms_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payment_terms.id", ondelete="SET NULL"), nullable=True),
         sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False)],
        [sa.UniqueConstraint("tenant_id", "code", name="uq_customer_groups_tenant_code"),
         sa.CheckConstraint("credit_limit >= 0", name="ck_customer_groups_credit_limit_nonnegative")],
        [("ix_customer_groups_tenant_name", ["tenant_id", "name"])],
    )
    _create_simple(
        "teams",
        [sa.Column("code", sa.String(40), nullable=False), sa.Column("name", sa.String(160), nullable=False),
         sa.Column("description", sa.Text(), nullable=True), sa.Column("team_type", sa.String(40), server_default="sales", nullable=False),
         sa.Column("leader_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
         sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False)],
        [sa.UniqueConstraint("tenant_id", "code", name="uq_teams_tenant_code")],
        [("ix_teams_leader", ["leader_id"]), ("ix_teams_tenant_name", ["tenant_id", "name"])],
    )
    _create_simple(
        "departments",
        [sa.Column("code", sa.String(40), nullable=False), sa.Column("name", sa.String(160), nullable=False),
         sa.Column("description", sa.Text(), nullable=True),
         sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
         sa.Column("manager_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
         sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False)],
        [sa.UniqueConstraint("tenant_id", "code", name="uq_departments_tenant_code")],
        [("ix_departments_parent", ["parent_id"]), ("ix_departments_tenant_name", ["tenant_id", "name"])],
    )


def downgrade():
    op.drop_table("departments")
    op.drop_table("teams")
    op.drop_table("customer_groups")
    op.drop_table("territories")
    op.drop_table("price_lists")
    op.drop_table("payment_terms")
    op.drop_table("industries")
