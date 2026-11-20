"""Regression checks for the shared SQLAlchemy model registry."""

import warnings

from sqlalchemy.orm import configure_mappers

import app.models  # noqa: F401 - import every model module
from app.models.base import Base


def test_all_orm_models_share_one_registry():
    assert len(Base.metadata.tables) == 98
    assert len(Base.registry.mappers) == 98
    assert "users" in Base.metadata.tables
    assert "billing_invoices" in Base.metadata.tables
    assert "invoices" in Base.metadata.tables


def test_all_relationship_mappers_configure_without_warnings():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        configure_mappers()
    assert not caught


def test_tenant_scoped_tables_reference_tenants():
    for table_name in ("users", "products", "accounts", "stock_moves", "sale_orders"):
        table = Base.metadata.tables[table_name]
        assert any(
            foreign_key.target_fullname == "tenants.id"
            for column in table.columns
            for foreign_key in column.foreign_keys
        ), table_name
