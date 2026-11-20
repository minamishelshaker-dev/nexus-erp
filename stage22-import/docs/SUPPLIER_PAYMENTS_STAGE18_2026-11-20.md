# Stage 18 — Supplier Payments

## Delivered

- Added tenant-scoped `SupplierPayment` and `SupplierPaymentAllocation` models.
- Added an Alembic migration creating both tables, foreign keys, positive-amount checks, tenant indexes, and uniqueness constraints.
- Added `PurchaseService.register_supplier_payment` to post a supplier disbursement and allocate it across one or more posted/partially-paid vendor bills in one database transaction.
- Locks allocated vendor bills in stable ID order (`FOR UPDATE`) before checking residual balances, reducing over-allocation races.
- Validates supplier, payable account, bank/cash account, journal, invoice ownership, invoice state, currency consistency, and allocation totals.
- Creates and posts the accounting entry in the same transaction: debit supplier payables, credit bank/cash; links the entry to the payment using the idempotent journal source (`supplier_payment`, payment ID).
- Updates vendor-bill `amount_paid`, `amount_residual`, and `state` only in the same transaction as the payment and journal entry.
- Added request/response schemas and `POST /purchase/supplier-payments` endpoint, protected by the existing purchase-invoice update permission.

## Deliberate scope limits

This release only supports payments fully allocated to existing posted vendor bills. It rejects unallocated balances, supplier advances, overpayments, and mixed-currency allocation. It does not yet implement bank-statement import/matching, cheque lifecycle, payment cancellation/reversal, payment listing/reporting, or FX gain/loss. These must not be represented as supported UI capabilities until implemented and tested.

## Verification

- Python AST parsing: 90/90 files passed.
- `compileall`: passed.
- SQLAlchemy model import and `configure_mappers()`: passed.
- Alembic graph: `add_supplier_payments_stage18` is the sole reported head.
- Static assertions for tenant scoping, invoice locks, allocation bounds, journal source idempotency, and atomic posting: passed.
- PostgreSQL migration execution, database integration tests, and concurrent transaction tests: not run; no configured PostgreSQL test database is available in this environment.
- Service import smoke test is blocked by the environment's missing `stripe` package, imported by the existing `app.services` package initializer. Schema-package import smoke test is blocked by an existing Pydantic model-construction error in `app.schemas.accounting.JournalEntryCreate`. These prevent a full API/service import test; they are not evidence that the new endpoint runtime path passed.

## Safety

No production database or deployment was changed. Migration has been added but not executed.
