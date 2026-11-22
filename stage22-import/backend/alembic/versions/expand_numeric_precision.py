"""Expand numeric precision and relax optional document references.

Revision ID: expand_numeric_precision
Revises: additive_orm_schema_columns
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "expand_numeric_precision"
down_revision = "additive_orm_schema_columns"
branch_labels = None
depends_on = None


_NUMERIC_COLUMNS = (
    ("bills_of_materials", "product_qty", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("bom_lines", "product_qty", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("leads", "estimated_value", sa.Numeric(12, 2), sa.Numeric(18, 2), True),
    ("manufacturing_orders", "product_qty", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("opportunities", "expected_revenue", sa.Numeric(12, 2), sa.Numeric(18, 2), False),
    ("products", "cost_price", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("products", "list_price", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("products", "reorder_point", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("products", "reorder_quantity", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("products", "weight", sa.Numeric(10, 2), sa.Numeric(12, 4), True),
    ("products", "volume", sa.Numeric(10, 2), sa.Numeric(12, 4), True),
    ("products", "quantity_on_hand", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("products", "quantity_available", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("products", "quantity_reserved", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("products", "average_cost", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("purchase_order_lines", "quantity", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("purchase_order_lines", "quantity_received", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("purchase_order_lines", "price_unit", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("purchase_order_lines", "subtotal", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("purchase_orders", "amount_untaxed", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("purchase_orders", "amount_tax", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("purchase_orders", "amount_total", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
    ("stock_moves", "quantity", sa.Numeric(12, 2), sa.Numeric(18, 4), False),
)


def upgrade():
    for table, column, old_type, new_type, nullable in _NUMERIC_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=old_type,
            type_=new_type,
            existing_nullable=nullable,
            postgresql_using=f"{column}::numeric({new_type.precision},{new_type.scale})",
        )

    # These fields are explicitly optional in the ORM and represent valid
    # business cases (unassigned partner code, service purchase line, or
    # unlinked stock movement reference).
    op.alter_column(
        "partners", "code",
        existing_type=sa.String(length=50),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        "purchase_order_lines", "product_id",
        existing_type=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        "stock_moves", "reference",
        existing_type=sa.String(length=100),
        existing_nullable=False,
        nullable=True,
    )


def downgrade():
    op.alter_column(
        "stock_moves", "reference",
        existing_type=sa.String(length=100),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "purchase_order_lines", "product_id",
        existing_type=postgresql.UUID(as_uuid=True),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "partners", "code",
        existing_type=sa.String(length=50),
        existing_nullable=True,
        nullable=False,
    )

    for table, column, old_type, new_type, nullable in reversed(_NUMERIC_COLUMNS):
        op.alter_column(
            table,
            column,
            existing_type=new_type,
            type_=old_type,
            existing_nullable=nullable,
            postgresql_using=f"{column}::numeric({old_type.precision},{old_type.scale})",
        )
