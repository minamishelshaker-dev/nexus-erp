# Database Migrations Guide

Nexus ERP uses Alembic for database migrations. This guide explains how to manage database schema changes.

## Overview

Alembic tracks database changes in the `alembic/versions/` directory. Each migration file represents a schema change that can be applied (upgrade) or reverted (downgrade).

## Migration Files

### Current Migrations

1. **001_initial_schema.py** - Creates all core tables:
   - Users, Roles, Permissions
   - Products, Categories, Warehouses, Stock Moves
   - Partners, Leads, Opportunities
   - Sales Orders, Quotations, Invoices
   - Purchase Orders, Requisitions
   - Chart of Accounts, Journal Entries
   - Manufacturing Orders, BOMs
   - Employees, Attendance
   - Projects, Tasks, Timesheets

2. **add_tenant_billing.py** - Adds multi-tenancy:
   - Tenants, Subscriptions, Plans
   - Invoices, Audit Logs
   - Adds `tenant_id` to existing tables

## Running Migrations

### Apply All Migrations

```bash
# Using Docker
docker compose exec backend alembic upgrade head

# Local development
cd backend
alembic upgrade head
```

### Check Current Migration

```bash
docker compose exec backend alembic current
```

### View Migration History

```bash
docker compose exec backend alembic history
```

### Rollback Last Migration

```bash
docker compose exec backend alembic downgrade -1
```

### Rollback All Migrations

```bash
docker compose exec backend alembic downgrade base
```

## Creating New Migrations

### Automatic Migration (Recommended)

After modifying models, generate a migration automatically:

```bash
docker compose exec backend alembic revision --autogenerate -m "Add new field to products"
```

This compares your models with the current database schema and generates the migration.

### Manual Migration

For complex changes, create a blank migration:

```bash
docker compose exec backend alembic revision -m "Custom data migration"
```

Then edit the generated file in `alembic/versions/`.

## Migration Best Practices

### 1. Always Test Migrations

```bash
# Apply migration
alembic upgrade head

# Verify data integrity
# Run tests

# Test rollback
alembic downgrade -1
alembic upgrade head
```

### 2. Include Both Upgrade and Downgrade

Every migration should have a reversible `downgrade()`:

```python
def upgrade():
    op.add_column('products', sa.Column('new_field', sa.String(100)))

def downgrade():
    op.drop_column('products', 'new_field')
```

### 3. Use Batch Operations for SQLite

For databases that don't support all ALTER operations:

```python
with op.batch_alter_table('products') as batch_op:
    batch_op.add_column(sa.Column('new_field', sa.String(100)))
```

### 4. Handle Data Migrations Separately

For large data changes, use a separate migration:

```python
def upgrade():
    # Schema changes
    op.add_column('orders', sa.Column('status', sa.String(50)))
    
    # Data migration
    op.execute("""
        UPDATE orders SET status = 'completed' 
        WHERE state = 'done'
    """)
```

### 5. Never Modify Applied Migrations

Once a migration is applied to production:
- Create a new migration for additional changes
- Don't modify the existing migration file

## Common Migration Patterns

### Add Column

```python
def upgrade():
    op.add_column(
        'products',
        sa.Column('weight', sa.Numeric(10, 2), nullable=True)
    )

def downgrade():
    op.drop_column('products', 'weight')
```

### Add Index

```python
def upgrade():
    op.create_index('ix_products_sku', 'products', ['sku'])

def downgrade():
    op.drop_index('ix_products_sku')
```

### Add Foreign Key

```python
def upgrade():
    op.add_column(
        'orders',
        sa.Column('customer_id', UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_orders_customer',
        'orders', 'partners',
        ['customer_id'], ['id'],
        ondelete='SET NULL'
    )

def downgrade():
    op.drop_constraint('fk_orders_customer', 'orders', type_='foreignkey')
    op.drop_column('orders', 'customer_id')
```

### Rename Column

```python
def upgrade():
    op.alter_column('products', 'old_name', new_column_name='new_name')

def downgrade():
    op.alter_column('products', 'new_name', new_column_name='old_name')
```

### Create New Table

```python
def upgrade():
    op.create_table(
        'new_table',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'))
    )

def downgrade():
    op.drop_table('new_table')
```

## Troubleshooting

### Migration Conflict

```bash
# Merge heads if multiple branches
alembic merge heads -m "Merge migrations"
```

### Out of Sync

```bash
# Mark migration as applied without running
alembic stamp head

# Mark specific version
alembic stamp <revision_id>
```

### View SQL Without Executing

```bash
alembic upgrade head --sql
```

## Database Backup

Always backup before migrations:

```bash
# PostgreSQL backup
docker compose exec postgres pg_dump -U nexus nexus_erp > backup.sql

# Restore
cat backup.sql | docker compose exec -T postgres psql -U nexus nexus_erp
```

## Environment Variables

Configure database connection in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
```

Or in `alembic.ini`:

```ini
sqlalchemy.url = postgresql://user:password@host:port/database
```
