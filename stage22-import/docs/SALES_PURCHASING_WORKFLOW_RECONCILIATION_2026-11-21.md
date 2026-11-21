# Sales & Purchasing Workflow Schema Reconciliation — 2026-11-21

## Scope

Compared current ORM models in `app/models/sales.py` and `app/models/purchase.py` with the legacy initial migration and later ORM inventory migration. No production data was queried or changed.

## Executive finding

The current sales/purchasing workflow is more normalized than the initial schema. Some legacy table names were replaced by canonical ORM table names, while some tables remain and are shared. The most dangerous risks are broken document relationships, losing historical line-level pricing/tax values, and mismatched document state enums.

## Sales workflow

### Quotations

- Legacy table: `sales_quotations` (initial migration).
- Current table: `quotations` with `quotation_lines`.
- The later migration creates current `quotations` and `quotation_lines`; the old `sales_quotations` remains a DB-only table in the parity inventory.
- Do not assume the two tables are duplicates. Compare columns, row counts, line relationships, numbering, status values, and references from sale orders before any merge.
- Current quotation partner/customer relationship points to `partners`; product lines point to current `products`. Confirm the legacy party references and product IDs remain valid.
- Preserve quotation number, dates, expiry, currency, discounts, tax breakdown, notes, and status history. Map unknown statuses to a controlled exception path, not a guessed enum.

### Sales orders

- Legacy tables: `sales_orders`, `sales_order_lines`.
- Current tables: `sale_orders`, `sale_order_lines`.
- Current ORM uses `quotation_id → quotations.id`, `partner_id → partners.id`, and line-level references to products.
- The old and new order header names differ, but line table name is the same. This makes an in-place header rename especially risky: line FK constraints may still reference the old header table.
- Build an explicit order-header crosswalk and re-point line references only after validating all rows and downstream invoice, shipment, and stock-move references.
- Legacy `sales_order_lines` and current ORM `sale_order_lines` must be compared column-by-column; same table name does not imply same contract.

### Invoices and payments

- Current ORM tables: `invoices`, `invoice_lines`, `payments`, `payment_invoices`, `payment_reconciliations`.
- The later migration creates invoices, invoice lines, payments and payment-invoice links. The legacy initial migration excerpt does not establish a complete corresponding invoice/payment schema.
- Current invoices link to sale orders, partners, journals, journal entries and account records. The accounting migration must therefore precede or be coordinated with invoice cutover.
- Current invoices have a tenant-scoped number uniqueness rule and a nonnegative total check. Validate historical credit notes/negative documents and duplicate numbers before adding constraints.
- Payment-to-invoice allocation must preserve partial payments, overpayments, refunds, reconciliation state, payment methods, and source journal entries. Do not collapse many-to-many allocation data into a single invoice_id.
- Compare all tax, discount, currency, exchange-rate, due-date, payment-term, and posted-state fields before data transformation.

## Purchasing workflow

### Purchase orders and lines

- Legacy initial migration creates `purchase_orders` and `purchase_order_lines`; current ORM retains those names.
- Same names do not establish parity. Compare header/line columns, nullability, numeric precision, status values, foreign keys, and tenant uniqueness.
- Current PurchaseOrder references `partners`; current lines reference products. Preserve supplier identity, supplier SKU, unit cost, received/billed quantities, discounts, taxes, currency and delivery dates.
- Current order number uniqueness is tenant-scoped. Legacy numbering/index rules may be global. Preflight duplicate numbers and tenant ownership before constraint changes.

### Receipts

- Current ORM tables: `receipts` and `receipt_lines`; later migration creates both.
- Receipt lines link to purchase order lines, products and stock moves. A receipt migration must preserve the chain from PO line → receipt line → stock movement and received quantity.
- Do not migrate receipt quantities without reconciling stock movement ledger and stock quantities; otherwise inventory can be double-counted.
- Preserve partial receipts, returns, rejected quantities, lot/serial information, warehouse/location destinations, and receipt status transitions.

### Purchase invoices and supplier payments

- Current ORM tables: `purchase_invoices`, `purchase_invoice_lines`, `supplier_payments`, `supplier_payment_allocations`, and `supplier_infos`.
- The purchase invoice and supplier payment structures were introduced in later migrations. Validate that every PO/receipt/supplier link is preserved.
- Supplier payment allocations are many-to-many and have positive-amount and uniqueness constraints. Do not infer one payment equals one invoice.
- Reversal journal links and payment allocations must be retained for auditability.
- Current supplier payment requires valid partner, journal and bank account references. Ensure master data and accounting cutover is complete first.

## Cross-domain dependencies

1. Customer/supplier/Partner reconciliation is a prerequisite for sales and purchasing because document headers and financial records point to `partners`.
2. Product and UOM/category reconciliation is a prerequisite for all document lines.
3. Accounting accounts, journals, currencies and journal entries are prerequisites for invoice/payment posting links.
4. Stock locations and stock moves are prerequisites for receipts and fulfillment.
5. Tenant assignment is required consistently across headers, lines, payments, and linked master data.

## Mandatory preflight and validation

- Header and line row counts per document type, grouped by tenant and state.
- Orphan line/header, product, partner, currency, journal, account and stock-move references.
- Duplicate document numbers within tenant and across tenants.
- All distinct legacy status/type values and explicit mapping tables.
- Line-level totals recomputed from quantity × price, discounts and tax; compare against header totals.
- Partial receipt and billed/received quantity consistency against PO lines.
- Payment allocations compared to payment totals and invoice balances.
- Inventory ledger quantities compared to stock quantity snapshots.
- Posted invoice/payment journal references and debit/credit control totals.
- Preservation of document IDs and all cross-domain UUID references.

## Safe migration approach

1. Work on a restorable disposable copy of the source schema and representative production-shaped data.
2. Produce per-table source/target column maps and enum mapping tables.
3. Create additive target structures and explicit crosswalks for `sales_quotations → quotations` and `sales_orders → sale_orders`.
4. Migrate master data and references before headers, then headers before lines and allocations.
5. Preserve original IDs where possible; where one-to-many transformations are required, store old-to-new ID mappings.
6. Run document-total, payment, stock, and journal control checks; stop on any unexplained discrepancy.
7. Test create/update/post/cancel/return/partial-receipt/partial-payment workflows on the migrated disposable database.
8. Only after successful backup/restore rehearsal and cutover review consider production migration.
9. Retire legacy tables in a later release, never in the same migration that first moves their data.

## Decision

The sales and purchasing schemas are not ready for an automatic destructive reconciliation. The two renamed sales document families and their line references require explicit crosswalks. Purchasing and payment flows require financial and inventory control-total verification. No production migration was applied.
