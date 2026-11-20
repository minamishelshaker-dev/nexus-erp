# Manufacturing tenant isolation and stock flow — Stage 13

## Scope
This stage reviews `backend/app/services/manufacturing_service.py` against the existing tenant-aware `InventoryService` APIs. It does not change production resources or database migrations.

## Changes
- Added a tenant-scoped record loader for tenant-owned references, excluding logically deleted rows.
- Validated BOM products, components, routing references, and work centers before creation/update.
- Validated work-center locations, manufacturing products, BOM components, routings, source/destination locations, and optional sales-order references against the current tenant.
- Replaced unscoped `db.get()` calls for work centers/products with tenant-scoped lookups.
- Fixed a duplicate dictionary key in material-availability details that previously overwrote the numeric available quantity with a boolean.
- Scoped material availability to the current tenant and, when selected, the manufacturing source location.
- Removed calls to a nonexistent `InventoryService.update_stock_quantity()` method. Material consumption and finished-goods receipts now use the existing create → confirm → process stock-move API with tenant context and the location's warehouse.
- Added quantity validation to prevent zero/negative production and overproduction beyond the remaining manufacturing quantity.
- Added a guard against starting the same manufacturing order twice.

## Important limitations
- No PostgreSQL-backed manufacturing cycle was executed in this environment.
- No concurrent-worker/idempotency test was executed. The inventory flow still needs database-level locking and idempotency keys before production use.
- The current material availability calculation and stock movement semantics need validation against warehouse policy (negative stock, reservations, scrap, partial consumption, and costing).
- No Alembic migration was created or applied.
- Static syntax validation is not evidence of runtime correctness.
