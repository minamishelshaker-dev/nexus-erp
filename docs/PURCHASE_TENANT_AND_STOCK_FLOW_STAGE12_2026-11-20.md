# Stage 12 — Purchase tenant isolation and receipt stock flow

Date: 2026-11-20

## Scope

This stage targets the purchase service and a pre-existing syntax defect in the inventory service. It does not claim complete ERP tenant isolation or production readiness.

## Changes

- Added a reusable tenant-scoped lookup helper in `PurchaseService`.
- Replaced direct `db.get()` lookups in purchase workflows with tenant-scoped queries; the service now has no direct `db.get()` calls.
- Validated supplier, warehouse, receiving location, purchase order, product, purchase-order line, stock lot, journal, and account references against the active tenant where those references are supplied.
- Scoped the default input-location lookup by tenant and soft-delete status.
- Added soft-delete filtering to private purchase order, receipt, and purchase invoice getters.
- Updated purchase-order receipt/invoice status helpers to carry the tenant ID.
- Replaced a call to a non-existent `InventoryService.update_stock_quantity()` with the actual inventory lifecycle: create draft stock move, confirm it, then process it. This ensures stock quantity and valuation updates use the central inventory service path.
- Rejects stockable receipt lines when warehouse or receiving location is missing.
- Validates that a receipt's linked purchase-order line belongs to the selected purchase order.
- Fixed a duplicate `tenant_id` parameter in `InventoryService.cancel_stock_move`, which made the Stage 11 source fail Python parsing.

## Verification

- Python AST parse: all 85 Python files under backend/app and backend/tests parsed successfully.
- Static review: `purchase_service.py` contains no direct `db.get()` calls.
- Import smoke test could not complete because the local environment lacks the declared `stripe` dependency, imported by `app.services.__init__` through billing service.
- No pytest run, PostgreSQL integration test, concurrency test, or end-to-end purchase cycle was executed.

## Remaining risks

- Verify model constraints and accounting integration on PostgreSQL.
- Validate UOM, taxes, analytic accounts, payment terms, currencies, and all optional purchase invoice references against tenant/global ownership rules.
- Add transactional rollback tests for receipt processing and integration failures.
- Add idempotency protection for repeated receipt confirmation and stock-move processing.
- Validate inventory valuation and accounting journal creation end-to-end.
