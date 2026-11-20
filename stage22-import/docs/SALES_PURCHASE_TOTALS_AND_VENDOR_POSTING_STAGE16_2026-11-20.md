# Stage 16 — Sales/Purchase totals and vendor-bill posting

## Scope
This stage addresses a financial correctness defect in document totals and completes the vendor-bill posting path. It is a local working-copy change only; no production database or deployment was modified.

## Changes

1. Corrected `calculate_totals()` on quotations, sales orders, sales invoices, purchase orders, and purchase invoices. Their line `subtotal` is already calculated net of line discount, so subtracting `amount_discount` again double-counted the discount. `amount_discount` remains available as a reporting field; document total is now net line subtotal plus tax.
2. `PurchaseService.post_purchase_invoice()` now validates supplier/source-document consistency, requires a completed linked receipt where applicable, recalculates totals from loaded lines, and calls the accounting integration before committing the posted state.
3. Vendor-bill accounting now loads active invoice lines with tenant scope, validates supplier and accounts within the tenant, requires payable and tax accounts when needed, distinguishes receipt-linked GR/IR debits from standalone line-account debits, checks exact balance, creates and posts the journal entry, and links it to the bill.
4. Accounting integration errors are no longer swallowed for vendor bills. The caller transaction cannot commit a posted vendor bill without its accounting entry.

## Important accounting limitation
For receipt-linked vendor bills, this implementation debits GR/IR for the bill's untaxed amount. It does not yet perform line-by-line three-way matching (PO vs receipt vs bill), handle price/quantity variances, or allocate partial invoices across multiple receipts. Those controls are required before production accounting use. Tax treatment also depends on the configured tax amounts and account mapping supplied by the application.

## Validation performed
- Python AST parse and `compileall` across backend source.
- Static assertions for all five corrected total formulas and the vendor-bill accounting call/validation path.
- ZIP integrity test.

No PostgreSQL migration, live transaction, concurrency, or end-to-end financial test was executed in this environment.
