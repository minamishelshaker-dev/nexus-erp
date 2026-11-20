"""
Add tenant billing and audit tables

Revision ID: add_tenant_billing
Revises: 
Create Date: 2024-01-15 10:00:00.000000

This migration adds:
- tenants table for multi-tenant support
- subscriptions table for subscription management
- plans table for plan definitions
- invoices table for billing
- audit_logs table for audit tracking
- tenant_id column to existing tables (if not exists)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_tenant_billing'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration."""
    
    # Create enum types
    tenant_status_enum = ENUM(
        'trial', 'active', 'past_due', 'suspended', 'cancelled', 'churned',
        name='tenant_status',
        create_type=False
    )
    
    plan_type_enum = ENUM(
        'basic', 'pro', 'enterprise',
        name='plan_type',
        create_type=False
    )
    
    audit_action_enum = ENUM(
        'login', 'logout', 'login_failed', 'password_reset', 'password_changed',
        'create', 'read', 'update', 'delete', 'bulk_create', 'bulk_update', 'bulk_delete',
        'export', 'import', 'system_config', 'backup', 'restore',
        'user_invite', 'user_activate', 'user_deactivate', 'user_role_change',
        'subscription_create', 'subscription_update', 'subscription_cancel',
        'payment_success', 'payment_failed',
        'tenant_create', 'tenant_update', 'tenant_suspend', 'tenant_reactivate',
        name='audit_action',
        create_type=False
    )
    
    # Create enum types in PostgreSQL
    op.execute("CREATE TYPE tenant_status AS ENUM ('trial', 'active', 'past_due', 'suspended', 'cancelled', 'churned')")
    op.execute("CREATE TYPE plan_type AS ENUM ('basic', 'pro', 'enterprise')")
    op.execute("""
        CREATE TYPE audit_action AS ENUM (
            'login', 'logout', 'login_failed', 'password_reset', 'password_changed',
            'create', 'read', 'update', 'delete', 'bulk_create', 'bulk_update', 'bulk_delete',
            'export', 'import', 'system_config', 'backup', 'restore',
            'user_invite', 'user_activate', 'user_deactivate', 'user_role_change',
            'subscription_create', 'subscription_update', 'subscription_cancel',
            'payment_success', 'payment_failed',
            'tenant_create', 'tenant_update', 'tenant_suspend', 'tenant_reactivate'
        )
    """)
    
    # ========================================
    # Create plans table
    # ========================================
    op.create_table(
        'plans',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('plan_type', plan_type_enum, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('is_public', sa.Boolean, default=True, nullable=False),
        
        # Pricing
        sa.Column('monthly_price', sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column('yearly_price', sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column('stripe_price_id_monthly', sa.String(100), nullable=True),
        sa.Column('stripe_price_id_yearly', sa.String(100), nullable=True),
        
        # Limits
        sa.Column('max_users', sa.Integer, default=5, nullable=False),
        sa.Column('max_storage_mb', sa.Integer, default=1024, nullable=False),
        sa.Column('max_products', sa.Integer, default=100, nullable=False),
        sa.Column('max_customers', sa.Integer, default=500, nullable=False),
        
        # Trial
        sa.Column('trial_days', sa.Integer, default=14, nullable=False),
        
        # Features
        sa.Column('features', JSONB, default=dict, nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by_id', UUID(as_uuid=True), nullable=True),
    )
    
    op.create_index('ix_plans_code', 'plans', ['code'], unique=True)
    
    # ========================================
    # Create tenants table
    # ========================================
    op.create_table(
        'tenants',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        
        # Basic Information
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subdomain', sa.String(100), unique=True, nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        
        # Contact Information
        sa.Column('contact_email', sa.String(255), nullable=False),
        sa.Column('contact_phone', sa.String(20), nullable=True),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        
        # Subscription & Billing
        sa.Column('status', tenant_status_enum, default='trial', nullable=False),
        sa.Column('plan_type', plan_type_enum, default='basic', nullable=False),
        sa.Column('stripe_customer_id', sa.String(100), unique=True, nullable=True),
        sa.Column('stripe_subscription_id', sa.String(100), nullable=True),
        sa.Column('subscription_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('subscription_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True),
        
        # Usage & Limits
        sa.Column('max_users', sa.Integer, default=5, nullable=False),
        sa.Column('current_users', sa.Integer, default=0, nullable=False),
        sa.Column('max_storage_mb', sa.Integer, default=1024, nullable=False),
        sa.Column('current_storage_mb', sa.Integer, default=0, nullable=False),
        sa.Column('max_products', sa.Integer, default=100, nullable=False),
        sa.Column('current_products', sa.Integer, default=0, nullable=False),
        sa.Column('max_customers', sa.Integer, default=500, nullable=False),
        sa.Column('current_customers', sa.Integer, default=0, nullable=False),
        sa.Column('api_calls_limit', sa.Integer, default=10000, nullable=False),
        sa.Column('api_calls_used', sa.Integer, default=0, nullable=False),
        
        # Features & Settings
        sa.Column('features', JSONB, default=dict, nullable=False),
        sa.Column('settings', JSONB, default=dict, nullable=False),
        sa.Column('schema_name', sa.String(100), unique=True, nullable=True),
        
        # Status Flags
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('is_verified', sa.Boolean, default=False, nullable=False),
        sa.Column('onboarding_completed', sa.Boolean, default=False, nullable=False),
        
        # Timestamps
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('suspended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by_id', UUID(as_uuid=True), nullable=True),
    )
    
    op.create_index('ix_tenants_subdomain', 'tenants', ['subdomain'], unique=True)
    op.create_index('ix_tenants_status', 'tenants', ['status'])
    op.create_index('ix_tenants_plan', 'tenants', ['plan_type'])
    
    # ========================================
    # Create subscriptions table
    # ========================================
    op.create_table(
        'subscriptions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', UUID(as_uuid=True), sa.ForeignKey('plans.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(50), default='active', nullable=False),
        sa.Column('stripe_subscription_id', sa.String(100), unique=True, nullable=True),
        sa.Column('stripe_price_id', sa.String(100), nullable=True),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean, default=False, nullable=False),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('quantity', sa.Integer, default=1, nullable=False),
        sa.Column('unit_price', sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column('trial_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('coupon_id', sa.String(100), nullable=True),
        sa.Column('discount_percent', sa.Integer, nullable=True),
        sa.Column('metadata', JSONB, default=dict, nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by_id', UUID(as_uuid=True), nullable=True),
    )
    
    op.create_index('ix_subscriptions_tenant', 'subscriptions', ['tenant_id'])
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])
    op.create_index('ix_subscriptions_stripe', 'subscriptions', ['stripe_subscription_id'])
    
    # ========================================
    # Create invoices table
    # ========================================
    op.create_table(
        'billing_invoices',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subscription_id', UUID(as_uuid=True), sa.ForeignKey('subscriptions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('stripe_invoice_id', sa.String(100), unique=True, nullable=True),
        sa.Column('invoice_number', sa.String(50), unique=True, nullable=False),
        sa.Column('status', sa.String(50), default='draft', nullable=False),
        
        # Amounts
        sa.Column('subtotal', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('tax', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('discount', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('total', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('amount_paid', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('amount_due', sa.Numeric(12, 2), default=0, nullable=False),
        
        # Currency
        sa.Column('currency', sa.String(3), default='USD', nullable=False),
        
        # Dates
        sa.Column('invoice_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        
        # Payment
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('charge_id', sa.String(100), nullable=True),
        
        # Content
        sa.Column('line_items', JSONB, default=list, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('metadata', JSONB, default=dict, nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by_id', UUID(as_uuid=True), nullable=True),
    )
    
    op.create_index('ix_billing_invoices_tenant', 'billing_invoices', ['tenant_id'])
    op.create_index('ix_billing_invoices_status', 'billing_invoices', ['status'])
    op.create_index('ix_billing_invoices_stripe', 'billing_invoices', ['stripe_invoice_id'])
    
    # ========================================
    # Create audit_logs table
    # ========================================
    op.create_table(
        'audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        
        # Context
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        
        # Action Details
        sa.Column('action', audit_action_enum, nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('resource_name', sa.String(255), nullable=True),
        
        # Change Details
        sa.Column('old_values', JSONB, nullable=True),
        sa.Column('new_values', JSONB, nullable=True),
        sa.Column('changes', JSONB, nullable=True),
        
        # Request Context
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('request_method', sa.String(10), nullable=True),
        sa.Column('request_path', sa.String(500), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        
        # Additional
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('metadata', JSONB, default=dict, nullable=False),
        sa.Column('status', sa.String(20), default='success', nullable=False),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('ix_audit_logs_tenant', 'audit_logs', ['tenant_id'])
    op.create_index('ix_audit_logs_user', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    
    # The predecessor initial_schema migration already defines tenant_id on
    # the root tables that exist in this schema. The former information_schema
    # probing loop was not offline-safe and also referenced several table names
    # that are not created by that predecessor. Keep a connection for seeding.
    conn = op.get_bind()

    # ========================================
    # Insert default plans
    # ========================================
    conn.execute(sa.text("""
        INSERT INTO plans (id, code, name, description, plan_type, is_active, is_public, 
                          monthly_price, yearly_price, max_users, max_storage_mb, max_products, 
                          max_customers, trial_days, features)
        VALUES 
        (gen_random_uuid(), 'basic', 'Basic', 'Perfect for small businesses getting started', 
         'basic', true, true, 29, 290, 5, 1024, 100, 500, 14,
         '{"inventory": true, "sales": true, "purchase": true, "accounting": true, "crm": true}'::jsonb),
        (gen_random_uuid(), 'pro', 'Professional', 'Ideal for growing businesses', 
         'pro', true, true, 79, 790, 25, 10240, 1000, 5000, 14,
         '{"inventory": true, "sales": true, "purchase": true, "accounting": true, "crm": true, 
           "manufacturing": true, "ai_features": true, "api_access": true, "custom_reports": true}'::jsonb),
        (gen_random_uuid(), 'enterprise', 'Enterprise', 'For large organizations with custom needs', 
         'enterprise', true, true, 199, 1990, -1, -1, -1, -1, 30,
         '{"inventory": true, "sales": true, "purchase": true, "accounting": true, "crm": true,
           "manufacturing": true, "ai_features": true, "api_access": true, "custom_reports": true,
           "white_label": true, "dedicated_support": true, "custom_integrations": true, "sla": true}'::jsonb)
    """))


def downgrade() -> None:
    """Revert migration."""
    
    # Drop indexes first
    op.drop_index('ix_audit_logs_created_at', 'audit_logs')
    op.drop_index('ix_audit_logs_resource', 'audit_logs')
    op.drop_index('ix_audit_logs_action', 'audit_logs')
    op.drop_index('ix_audit_logs_user', 'audit_logs')
    op.drop_index('ix_audit_logs_tenant', 'audit_logs')
    
    op.drop_index('ix_billing_invoices_stripe', 'billing_invoices')
    op.drop_index('ix_billing_invoices_status', 'billing_invoices')
    op.drop_index('ix_billing_invoices_tenant', 'billing_invoices')
    
    op.drop_index('ix_subscriptions_stripe', 'subscriptions')
    op.drop_index('ix_subscriptions_status', 'subscriptions')
    op.drop_index('ix_subscriptions_tenant', 'subscriptions')
    
    op.drop_index('ix_tenants_plan', 'tenants')
    op.drop_index('ix_tenants_status', 'tenants')
    op.drop_index('ix_tenants_subdomain', 'tenants')
    
    op.drop_index('ix_plans_code', 'plans')
    
    # Drop tables
    op.drop_table('audit_logs')
    op.drop_table('billing_invoices')
    op.drop_table('subscriptions')
    op.drop_table('tenants')
    op.drop_table('plans')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS audit_action')
    op.execute('DROP TYPE IF EXISTS plan_type')
    op.execute('DROP TYPE IF EXISTS tenant_status')
    
    # Existing tenant_id columns belong to the predecessor schema and are not
    # removed by this billing-only downgrade.
