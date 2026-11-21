"""Create vendor bills and bill lines before supplier-payment allocations.

Revision ID: create_purchase_invoices
Revises: create_journals_table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "create_purchase_invoices"
down_revision = "create_journals_table"
branch_labels = None
depends_on = None

purchase_invoice_state = postgresql.ENUM(
    "DRAFT", "POSTED", "PAID", "PARTIAL", "CANCELLED",
    name="purchaseinvoicestate",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    purchase_invoice_state.create(bind, checkfirst=True)

    op.create_table(
        "purchase_invoices",
        sa.Column("number", sa.String(50), nullable=False),
        sa.Column("supplier_invoice_number", sa.String(100), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("origin", sa.String(100), nullable=True),
        sa.Column("date_invoice", sa.Date(), nullable=False),
        sa.Column("date_due", sa.Date(), nullable=True),
        sa.Column("date_posted", sa.Date(), nullable=True),
        sa.Column("state", purchase_invoice_state, nullable=False),
        sa.Column("amount_untaxed", sa.Numeric(18, 4), nullable=False),
        sa.Column("amount_tax", sa.Numeric(18, 4), nullable=False),
        sa.Column("amount_discount", sa.Numeric(18, 4), nullable=False),
        sa.Column("amount_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("amount_residual", sa.Numeric(18, 4), nullable=False),
        sa.Column("amount_paid", sa.Numeric(18, 4), nullable=False),
        sa.Column("payment_term_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("currency_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("exchange_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("custom_fields", postgresql.JSONB(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["journal_id"], ["journals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("number", "tenant_id", name="uq_purchase_invoice_number"),
    )
    op.create_index("ix_purchase_invoices_number", "purchase_invoices", ["number"])
    op.create_index("ix_purchase_invoices_partner", "purchase_invoices", ["partner_id"])
    op.create_index("ix_purchase_invoices_date", "purchase_invoices", ["date_invoice"])
    op.create_index("ix_purchase_invoices_state", "purchase_invoices", ["state"])
    op.create_index("ix_purchase_invoices_company", "purchase_invoices", ["tenant_id"])
    op.create_index("ix_purchase_invoices_is_deleted", "purchase_invoices", ["is_deleted"])

    op.create_table(
        "purchase_invoice_lines",
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("price_unit", sa.Numeric(18, 4), nullable=False),
        sa.Column("discount", sa.Numeric(5, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("tax_ids", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("tax_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 4), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analytic_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_id"], ["purchase_invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_purchase_invoice_lines_invoice", "purchase_invoice_lines", ["invoice_id"])
    op.create_index("ix_purchase_invoice_lines_product", "purchase_invoice_lines", ["product_id"])
    op.create_index("ix_purchase_invoice_lines_is_deleted", "purchase_invoice_lines", ["is_deleted"])


def downgrade() -> None:
    op.drop_table("purchase_invoice_lines")
    op.drop_table("purchase_invoices")
    purchase_invoice_state.drop(op.get_bind(), checkfirst=True)
