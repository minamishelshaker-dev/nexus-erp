"""Enforce ORM-required non-null fields after CI null audit.

Revision ID: enforce_required_columns
Revises: expand_numeric_precision
"""
from alembic import op

revision = "enforce_required_columns"
down_revision = "expand_numeric_precision"
branch_labels = None
depends_on = None

_REQUIRED_COLUMNS = (
    ("analytic_accounts", "is_active"),
    ("bills_of_materials", "tenant_id"),
    ("journal_entries", "tenant_id"),
    ("leads", "tenant_id"),
    ("manufacturing_orders", "tenant_id"),
    ("opportunities", "tenant_id"),
    ("partners", "tenant_id"),
    ("products", "uom_id"),
    ("products", "tenant_id"),
    ("purchase_order_lines", "description"),
    ("purchase_orders", "tenant_id"),
    ("roles", "tenant_id"),
    ("stock_moves", "tenant_id"),
    ("users", "first_name"),
    ("users", "last_name"),
    ("users", "tenant_id"),
    ("warehouses", "tenant_id"),
    ("work_centers", "tenant_id"),
)


def upgrade():
    # The disposable PostgreSQL migration test confirmed zero NULL values
    # in every field below before this constraint-tightening migration.
    for table, column in _REQUIRED_COLUMNS:
        op.alter_column(table, column, nullable=False)


def downgrade():
    for table, column in reversed(_REQUIRED_COLUMNS):
        op.alter_column(table, column, nullable=True)
