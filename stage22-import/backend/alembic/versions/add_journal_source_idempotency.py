"""Enforce one active journal entry per source document and tenant.

Revision ID: add_journal_source_idempotency
Revises: add_tenant_billing
Create Date: 2026-11-20
"""
from alembic import op, context
import sqlalchemy as sa

revision = "add_journal_source_idempotency"
down_revision = "add_tenant_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The legacy initial migration predates source-document references. Add the
    # nullable columns before validating and indexing them; existing journal
    # entries remain intact and simply have no source association.
    op.add_column(
        "journal_entries",
        sa.Column("source_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "journal_entries",
        sa.Column("source_id", sa.UUID(as_uuid=True), nullable=True),
    )

    # Fail loudly rather than silently deleting or merging historical accounting data.
    # Offline SQL generation has no live result set to inspect. The unique index is
    # still emitted there; the duplicate preflight is performed during online upgrade.
    if not context.is_offline_mode():
        duplicates = op.get_bind().execute(sa.text("""
            SELECT tenant_id, source_model, source_id, COUNT(*) AS row_count
            FROM journal_entries
            WHERE source_model IS NOT NULL
              AND source_id IS NOT NULL
              AND is_deleted = false
            GROUP BY tenant_id, source_model, source_id
            HAVING COUNT(*) > 1
            LIMIT 10
        """)).fetchall()
        if duplicates:
            raise RuntimeError(
                "Cannot add journal source idempotency constraint: duplicate active "
                f"source entries exist. Review and reconcile these rows first: {duplicates}"
            )

    op.create_index(
        "uq_journal_entry_tenant_source",
        "journal_entries",
        ["tenant_id", "source_model", "source_id"],
        unique=True,
        postgresql_where=sa.text(
            "source_model IS NOT NULL AND source_id IS NOT NULL AND is_deleted = false"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_journal_entry_tenant_source", table_name="journal_entries")
    op.drop_column("journal_entries", "source_id")
    op.drop_column("journal_entries", "source_model")
