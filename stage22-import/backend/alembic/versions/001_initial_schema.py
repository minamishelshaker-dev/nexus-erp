"""
Initial Schema Migration
========================

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-01-01 00:00:00.000000

This migration creates all core tables for Nexus ERP:
- users, roles, permissions (Authentication)
- products, categories, warehouses (Inventory)
- customers, leads, opportunities (CRM)
- sales_orders, sales_quotations, invoices (Sales)
- purchase_orders, suppliers (Purchasing)
- chart_of_accounts, journal_entries (Accounting)
- manufacturing_orders, bills_of_materials (Manufacturing)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply initial schema migration."""
    
    # ========================================
    # Users and Authentication
    # ========================================
    
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('username', sa.String(100), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('is_verified', sa.Boolean, default=False, nullable=False),
        sa.Column('is_superuser', sa.Boolean, default=False, nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('preferences', JSONB, default=dict, nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_tenant', 'users', ['tenant_id'])
    
    # Roles
    op.create_table(
        'roles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_system', sa.Boolean, default=False, nullable=False),
        sa.Column('permissions', JSONB, default=list, nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_roles_code', 'roles', ['code'], unique=True)
    
    # User-Role association
    op.create_table(
        'user_roles',
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )
    
    # Refresh Tokens
    op.create_table(
        'refresh_tokens',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_refresh_tokens_hash', 'refresh_tokens', ['token_hash'], unique=True)
    
    # ========================================
    # Products and Inventory
    # ========================================
    
    # Categories
    op.create_table(
        'categories',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('parent_id', UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    op.create_index('ix_categories_code', 'categories', ['code'], unique=True)
    
    # Products
    op.create_table(
        'products',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('sku', sa.String(100), unique=True, nullable=False),
        sa.Column('barcode', sa.String(100), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category_id', UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('product_type', sa.String(50), default='product', nullable=False),
        sa.Column('is_saleable', sa.Boolean, default=True, nullable=False),
        sa.Column('is_purchasable', sa.Boolean, default=True, nullable=False),
        sa.Column('is_storable', sa.Boolean, default=True, nullable=False),
        
        # Pricing
        sa.Column('list_price', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('cost_price', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('average_cost', sa.Numeric(12, 2), default=0, nullable=False),
        
        # Inventory
        sa.Column('quantity_on_hand', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('quantity_available', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('quantity_reserved', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('reorder_point', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('reorder_quantity', sa.Numeric(12, 2), default=0, nullable=False),
        
        # Unit of Measure
        sa.Column('uom_id', UUID(as_uuid=True), nullable=True),
        sa.Column('uom_name', sa.String(50), default='Units', nullable=False),
        
        # Status
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('track_inventory', sa.Boolean, default=True, nullable=False),
        
        # Metadata
        sa.Column('weight', sa.Numeric(10, 2), nullable=True),
        sa.Column('volume', sa.Numeric(10, 2), nullable=True),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('attributes', JSONB, default=dict, nullable=False),
        
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    op.create_index('ix_products_sku', 'products', ['sku'], unique=True)
    op.create_index('ix_products_category', 'products', ['category_id'])
    
    # Warehouses
    op.create_table(
        'warehouses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('is_default', sa.Boolean, default=False, nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    op.create_index('ix_warehouses_code', 'warehouses', ['code'], unique=True)
    
    # Stock Moves
    op.create_table(
        'stock_moves',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('reference', sa.String(100), unique=True, nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('warehouse_id', UUID(as_uuid=True), sa.ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('location_id', UUID(as_uuid=True), nullable=True),
        sa.Column('move_type', sa.String(50), nullable=False),  # in, out, internal
        sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
        sa.Column('uom', sa.String(50), default='Units', nullable=False),
        sa.Column('cost_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('total_value', sa.Numeric(12, 2), nullable=True),
        sa.Column('state', sa.String(50), default='draft', nullable=False),
        sa.Column('origin', sa.String(100), nullable=True),
        sa.Column('origin_id', UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('date_done', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_stock_moves_reference', 'stock_moves', ['reference'], unique=True)
    op.create_index('ix_stock_moves_product', 'stock_moves', ['product_id'])
    op.create_index('ix_stock_moves_warehouse', 'stock_moves', ['warehouse_id'])
    
    # ========================================
    # CRM - Customers, Leads, Opportunities
    # ========================================
    
    # Customers (Partners)
    op.create_table(
        'partners',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('partner_type', sa.String(50), default='customer', nullable=False),
        sa.Column('tax_id', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('address_line1', sa.String(255), nullable=True),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('credit_limit', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('credit_used', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('payment_terms', sa.Integer, default=30, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('metadata', JSONB, default=dict, nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    op.create_index('ix_partners_code', 'partners', ['code'], unique=True)
    op.create_index('ix_partners_type', 'partners', ['partner_type'])
    
    # Customer Contacts
    op.create_table(
        'partner_contacts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('partner_id', UUID(as_uuid=True), sa.ForeignKey('partners.id', ondelete='CASCADE'), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('title', sa.String(100), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('is_primary', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_partner_contacts_partner', 'partner_contacts', ['partner_id'])
    
    # Leads
    op.create_table(
        'leads',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), default='new', nullable=False),
        sa.Column('priority', sa.String(20), default='medium', nullable=False),
        sa.Column('estimated_value', sa.Numeric(12, 2), nullable=True),
        sa.Column('assigned_to_id', UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('converted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('converted_to_id', UUID(as_uuid=True), nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_leads_status', 'leads', ['status'])
    
    # Opportunities
    op.create_table(
        'opportunities',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('partner_id', UUID(as_uuid=True), sa.ForeignKey('partners.id', ondelete='SET NULL'), nullable=True),
        sa.Column('lead_id', UUID(as_uuid=True), sa.ForeignKey('leads.id', ondelete='SET NULL'), nullable=True),
        sa.Column('stage', sa.String(50), default='qualification', nullable=False),
        sa.Column('probability', sa.Integer, default=10, nullable=False),
        sa.Column('expected_revenue', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('expected_close_date', sa.Date, nullable=True),
        sa.Column('assigned_to_id', UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('lost_reason', sa.Text, nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_index('ix_opportunities_stage', 'opportunities', ['stage'])
    op.create_index('ix_opportunities_partner', 'opportunities', ['partner_id'])
    
    # ========================================
    # Sales Module
    # ========================================
    
    # Sales Quotations
    op.create_table(
        'sales_quotations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('number', sa.String(50), unique=True, nullable=False),
        sa.Column('partner_id', UUID(as_uuid=True), sa.ForeignKey('partners.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('date_quotation', sa.Date, nullable=False),
        sa.Column('valid_until', sa.Date, nullable=True),
        sa.Column('state', sa.String(50), default='draft', nullable=False),
        sa.Column('amount_untaxed', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('amount_tax', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('amount_total', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('currency', sa.String(3), default='USD', nullable=False),
        sa.Column('payment_terms', sa.Integer, default=30, nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('terms_conditions', sa.Text, nullable=True),
        sa.Column('salesperson_id', UUID(as_uuid=True), nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_sales_quotations_number', 'sales_quotations', ['number'], unique=True)
    op.create_index('ix_sales_quotations_partner', 'sales_quotations', ['partner_id'])
    
    # Sales Orders
    op.create_table(
        'sales_orders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('number', sa.String(50), unique=True, nullable=False),
        sa.Column('quotation_id', UUID(as_uuid=True), sa.ForeignKey('sales_quotations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('partner_id', UUID(as_uuid=True), sa.ForeignKey('partners.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('date_order', sa.Date, nullable=False),
        sa.Column('date_planned', sa.Date, nullable=True),
        sa.Column('state', sa.String(50), default='draft', nullable=False),
        sa.Column('amount_untaxed', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('amount_tax', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('amount_total', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('currency', sa.String(3), default='USD', nullable=False),
        sa.Column('payment_terms', sa.Integer, default=30, nullable=False),
        sa.Column('shipping_address_id', UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('salesperson_id', UUID(as_uuid=True), nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_sales_orders_number', 'sales_orders', ['number'], unique=True)
    op.create_index('ix_sales_orders_partner', 'sales_orders', ['partner_id'])
    op.create_index('ix_sales_orders_state', 'sales_orders', ['state'])
    
    # Sales Order Lines
    op.create_table(
        'sales_order_lines',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('sales_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
        sa.Column('uom', sa.String(50), default='Units', nullable=False),
        sa.Column('price_unit', sa.Numeric(12, 2), nullable=False),
        sa.Column('discount', sa.Numeric(5, 2), default=0, nullable=False),
        sa.Column('tax_rate', sa.Numeric(5, 2), default=0, nullable=False),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_sales_order_lines_order', 'sales_order_lines', ['order_id'])
    
    # ========================================
    # Purchasing Module
    # ========================================
    
    # Suppliers (partner_type='supplier' in partners table)
    
    # Purchase Requisitions
    op.create_table(
        'purchase_requisitions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('number', sa.String(50), unique=True, nullable=False),
        sa.Column('date_required', sa.Date, nullable=True),
        sa.Column('state', sa.String(50), default='draft', nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('requested_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    # Purchase Orders
    op.create_table(
        'purchase_orders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('number', sa.String(50), unique=True, nullable=False),
        sa.Column('requisition_id', UUID(as_uuid=True), sa.ForeignKey('purchase_requisitions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('partner_id', UUID(as_uuid=True), sa.ForeignKey('partners.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('date_order', sa.Date, nullable=False),
        sa.Column('date_planned', sa.Date, nullable=True),
        sa.Column('state', sa.String(50), default='draft', nullable=False),
        sa.Column('amount_untaxed', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('amount_tax', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('amount_total', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('currency', sa.String(3), default='USD', nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('buyer_id', UUID(as_uuid=True), nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_purchase_orders_number', 'purchase_orders', ['number'], unique=True)
    op.create_index('ix_purchase_orders_partner', 'purchase_orders', ['partner_id'])
    op.create_index('ix_purchase_orders_state', 'purchase_orders', ['state'])
    
    # Purchase Order Lines
    op.create_table(
        'purchase_order_lines',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('purchase_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
        sa.Column('quantity_received', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('uom', sa.String(50), default='Units', nullable=False),
        sa.Column('price_unit', sa.Numeric(12, 2), nullable=False),
        sa.Column('tax_rate', sa.Numeric(5, 2), default=0, nullable=False),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False),
        sa.Column('date_planned', sa.Date, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_purchase_order_lines_order', 'purchase_order_lines', ['order_id'])
    
    # ========================================
    # Accounting Module
    # ========================================
    
    # Chart of Accounts
    op.create_table(
        'chart_of_accounts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('account_type', sa.String(50), nullable=False),  # asset, liability, equity, revenue, expense
        sa.Column('parent_id', UUID(as_uuid=True), sa.ForeignKey('chart_of_accounts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('balance', sa.Numeric(15, 2), default=0, nullable=False),
        sa.Column('currency', sa.String(3), default='USD', nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('is_reconcilable', sa.Boolean, default=False, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    op.create_index('ix_chart_of_accounts_code', 'chart_of_accounts', ['code'], unique=True)
    
    # Journal Entries
    op.create_table(
        'journal_entries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('number', sa.String(50), unique=True, nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('journal_type', sa.String(50), default='general', nullable=False),
        sa.Column('reference', sa.String(100), nullable=True),
        sa.Column('narration', sa.Text, nullable=True),
        sa.Column('state', sa.String(50), default='draft', nullable=False),
        sa.Column('is_posted', sa.Boolean, default=False, nullable=False),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_journal_entries_number', 'journal_entries', ['number'], unique=True)
    op.create_index('ix_journal_entries_date', 'journal_entries', ['date'])
    
    # Journal Entry Lines
    op.create_table(
        'journal_entry_lines',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('entry_id', UUID(as_uuid=True), sa.ForeignKey('journal_entries.id', ondelete='CASCADE'), nullable=False),
        sa.Column('account_id', UUID(as_uuid=True), sa.ForeignKey('chart_of_accounts.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('partner_id', UUID(as_uuid=True), sa.ForeignKey('partners.id', ondelete='SET NULL'), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('debit', sa.Numeric(15, 2), default=0, nullable=False),
        sa.Column('credit', sa.Numeric(15, 2), default=0, nullable=False),
        sa.Column('currency', sa.String(3), default='USD', nullable=False),
        sa.Column('reconciled', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_journal_entry_lines_entry', 'journal_entry_lines', ['entry_id'])
    op.create_index('ix_journal_entry_lines_account', 'journal_entry_lines', ['account_id'])
    
    # ========================================
    # Manufacturing Module
    # ========================================
    
    # Bills of Materials
    op.create_table(
        'bills_of_materials',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('product_qty', sa.Numeric(12, 2), nullable=False),
        sa.Column('product_uom', sa.String(50), default='Units', nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('routing', sa.Text, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_bom_code', 'bills_of_materials', ['code'], unique=True)
    
    # BOM Lines
    op.create_table(
        'bom_lines',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('bom_id', UUID(as_uuid=True), sa.ForeignKey('bills_of_materials.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('product_qty', sa.Numeric(12, 2), nullable=False),
        sa.Column('product_uom', sa.String(50), default='Units', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_bom_lines_bom', 'bom_lines', ['bom_id'])
    
    # Manufacturing Orders
    op.create_table(
        'manufacturing_orders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('number', sa.String(50), unique=True, nullable=False),
        sa.Column('bom_id', UUID(as_uuid=True), sa.ForeignKey('bills_of_materials.id', ondelete='SET NULL'), nullable=True),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('product_qty', sa.Numeric(12, 2), nullable=False),
        sa.Column('product_uom', sa.String(50), default='Units', nullable=False),
        sa.Column('date_planned_start', sa.Date, nullable=True),
        sa.Column('date_planned_finished', sa.Date, nullable=True),
        sa.Column('date_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_finished', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(50), default='draft', nullable=False),
        sa.Column('progress', sa.Numeric(5, 2), default=0, nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_manufacturing_orders_number', 'manufacturing_orders', ['number'], unique=True)
    op.create_index('ix_manufacturing_orders_state', 'manufacturing_orders', ['state'])
    
    # Work Centers
    op.create_table(
        'work_centers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('capacity', sa.Numeric(12, 2), default=1, nullable=False),
        sa.Column('cost_hour', sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_work_centers_code', 'work_centers', ['code'], unique=True)
    
    # ========================================
    # HR Module
    # ========================================
    
    # Employees
    op.create_table(
        'employees',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('employee_number', sa.String(50), unique=True, nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('position', sa.String(100), nullable=True),
        sa.Column('manager_id', UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('hire_date', sa.Date, nullable=True),
        sa.Column('termination_date', sa.Date, nullable=True),
        sa.Column('employment_type', sa.String(50), default='full_time', nullable=False),
        sa.Column('status', sa.String(50), default='active', nullable=False),
        sa.Column('salary', sa.Numeric(12, 2), nullable=True),
        sa.Column('salary_currency', sa.String(3), default='USD', nullable=False),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    op.create_index('ix_employees_number', 'employees', ['employee_number'], unique=True)
    op.create_index('ix_employees_status', 'employees', ['status'])
    
    # Attendance
    op.create_table(
        'attendance_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('employee_id', UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('check_in', sa.DateTime(timezone=True), nullable=True),
        sa.Column('check_out', sa.DateTime(timezone=True), nullable=True),
        sa.Column('hours_worked', sa.Numeric(5, 2), default=0, nullable=False),
        sa.Column('overtime_hours', sa.Numeric(5, 2), default=0, nullable=False),
        sa.Column('status', sa.String(50), default='present', nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_attendance_employee_date', 'attendance_records', ['employee_id', 'date'])
    
    # ========================================
    # Projects Module
    # ========================================
    
    # Projects
    op.create_table(
        'projects',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('customer_id', UUID(as_uuid=True), sa.ForeignKey('partners.id', ondelete='SET NULL'), nullable=True),
        sa.Column('manager_id', UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('start_date', sa.Date, nullable=True),
        sa.Column('end_date', sa.Date, nullable=True),
        sa.Column('budget', sa.Numeric(15, 2), default=0, nullable=False),
        sa.Column('status', sa.String(50), default='planning', nullable=False),
        sa.Column('progress', sa.Numeric(5, 2), default=0, nullable=False),
        sa.Column('color', sa.String(7), default='#3B82F6', nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_projects_code', 'projects', ['code'], unique=True)
    op.create_index('ix_projects_status', 'projects', ['status'])
    
    # Project Tasks
    op.create_table(
        'project_tasks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('assignee_id', UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('parent_id', UUID(as_uuid=True), sa.ForeignKey('project_tasks.id', ondelete='CASCADE'), nullable=True),
        sa.Column('planned_hours', sa.Numeric(6, 2), default=0, nullable=False),
        sa.Column('spent_hours', sa.Numeric(6, 2), default=0, nullable=False),
        sa.Column('progress', sa.Numeric(5, 2), default=0, nullable=False),
        sa.Column('priority', sa.String(20), default='medium', nullable=False),
        sa.Column('status', sa.String(50), default='todo', nullable=False),
        sa.Column('due_date', sa.Date, nullable=True),
        sa.Column('tags', JSONB, default=list, nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_project_tasks_project', 'project_tasks', ['project_id'])
    op.create_index('ix_project_tasks_status', 'project_tasks', ['status'])
    
    # Timesheets
    op.create_table(
        'timesheets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('employee_id', UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('task_id', UUID(as_uuid=True), sa.ForeignKey('project_tasks.id', ondelete='SET NULL'), nullable=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('hours', sa.Numeric(5, 2), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('billable', sa.Boolean, default=True, nullable=False),
        sa.Column('approved', sa.Boolean, default=False, nullable=False),
        sa.Column('approved_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_timesheets_employee', 'timesheets', ['employee_id'])
    op.create_index('ix_timesheets_project', 'timesheets', ['project_id'])
    
    print("Initial schema migration completed successfully!")


def downgrade() -> None:
    """Revert initial schema migration."""
    
    # Drop tables in reverse order
    tables = [
        'timesheets', 'project_tasks', 'projects',
        'attendance_records', 'employees',
        'work_centers', 'manufacturing_orders', 'bom_lines', 'bills_of_materials',
        'journal_entry_lines', 'journal_entries', 'chart_of_accounts',
        'purchase_order_lines', 'purchase_orders', 'purchase_requisitions',
        'sales_order_lines', 'sales_orders', 'sales_quotations',
        'opportunities', 'leads', 'partner_contacts', 'partners',
        'stock_moves', 'warehouses', 'products', 'categories',
        'refresh_tokens', 'user_roles', 'roles', 'users'
    ]
    
    for table in tables:
        op.drop_table(table)
    
    print("Initial schema migration reverted successfully!")
