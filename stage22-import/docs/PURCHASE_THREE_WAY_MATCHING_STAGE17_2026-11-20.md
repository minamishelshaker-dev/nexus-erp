# Stage 17 — Purchase receipt-to-bill quantity controls

Date: 2026-11-20

## Scope

This stage addresses the purchase-order / goods-receipt / vendor-bill quantity path. It does not claim full price, tax, or GR/IR valuation matching.

## Changes

- Vendor bills linked to a goods receipt now load active receipt lines explicitly inside the current tenant boundary.
- A linked receipt must be completed and contain active lines; supplier and purchase-order relationships are revalidated.
- Receipt-backed bill lines must identify products and have positive quantities.
- The service aggregates completed received quantities by product and subtracts quantities from previously posted/paid bills against the same receipt. Draft bills do not consume received quantities.
- Posting is rejected when the bill exceeds the unbilled quantity received for any product.
- Purchase-order `quantity_billed`, invoice status, and billed amount are updated only after the accounting journal is successfully created and posted. Draft creation no longer mutates billed quantities or invoice status.
- Purchase-order status calculation now queries active tenant-owned order lines explicitly rather than relying on an implicitly lazy-loaded relationship.
- Purchase-order and receipt rows are locked with `FOR UPDATE` during posting to serialize competing bill posts against the same source documents.

## Important limitation

The current data model does not persist a purchase-order-line reference on each vendor-bill line. This implementation therefore performs quantity matching by product at receipt level and allocates posted quantities to linked purchase-order lines in receipt order. It does not yet implement deterministic line-to-line price matching, configurable tolerances, tax matching, GR/IR price-variance accounting, or a full multi-receipt/multi-bill allocation ledger. Those require a dedicated invoice-line-to-PO-line/receipt-line relationship and migration. The existing GR/IR posting still needs valuation/price-variance reconciliation before production accounting approval.

## Verification

Static checks performed for this stage:

- Python AST parsing across backend source files.
- `compileall` across backend application code.
- Targeted source assertions for receipt tenant filters, posted-bill aggregation, row locks, and the absence of draft-time billed-quantity mutation.
- ZIP integrity check.

Not performed: live PostgreSQL migration, database transaction tests, concurrency tests, API tests, or full purchasing/accounting end-to-end tests.
- Receipt accounting now fails the receipt transaction when a stockable line lacks a tenant-owned inventory or GR/IR account, has no positive valuation, or journal creation/posting fails. Service-only receipts with no stockable lines may still have no receipt accrual entry.
- Vendor bill line objects are attached to the invoice relationship before totals are calculated, avoiding stale/empty in-memory totals after creating lines.
- Generated receipt bills now resolve a real tenant default debit account (inventory for stockable products, operating expense for non-stockable products) instead of the former all-zero UUID placeholder; configured product/supplier account references are tenant-validated.
