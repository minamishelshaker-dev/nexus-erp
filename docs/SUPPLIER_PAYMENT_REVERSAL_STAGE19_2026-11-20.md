# Stage 19 — Supplier Payment Cancellation and Reversal

## Delivered

- Added a cancellation request schema with mandatory reason and optional reversal date.
- Added `PurchaseService.cancel_supplier_payment`, scoped to tenant and protected by row locks on the payment and all affected vendor bills.
- Validates that the payment is posted, has a linked journal entry, and that active allocations reconcile exactly to the payment amount.
- Creates and posts an accounting reversal through `AccountingService.reverse_journal_entry`; duplicate reversal protection remains enforced by the accounting service.
- Restores vendor-bill paid/residual balances and returns bills to `posted` or `partial` as appropriate. Cancelled bills remain cancelled.
- Soft-deletes allocation rows with deletion metadata rather than physically deleting the audit trail.
- Stores the reversal journal ID in a dedicated `reversal_journal_entry_id` foreign-key column for traceability.
- Marks the payment cancelled only after the reversal and bill balance restoration have succeeded in the same transaction.
- Added an Alembic migration to add the reversal journal link; it has not been executed against production or a live PostgreSQL database.
- Added `POST /purchase/supplier-payments/{payment_id}/cancel`, requiring both purchase invoice update and accounting journal reverse permissions.
- Added the previously missing purchase-invoice permission codes and journal-reversal permission to the code-level RBAC registry and role templates, without broad wildcard access. **This does not by itself provision permission rows or role assignments in an existing database.** The current schema/migration set does not yet provide a verified end-to-end permission seeding path, so effective runtime authorization for these new codes remains a deployment prerequisite.

## Important behavior

- Cancellation is not deletion: the original payment and original journal remain in history; a separate posted reversal journal is created.
- The service rejects payments without a journal entry or with non-reconciling allocations.
- No supplier advances, bank matching, cheque lifecycle, or FX differences are introduced in this stage.

## Verification

- Static source assertions cover tenant scoping, row locking, reversal-before-cancel sequencing, invoice balance restoration, allocation history retention, and dual permission checks.
- Python AST/compile checks and archive integrity are run for this stage.
- PostgreSQL transaction, concurrent cancellation, and end-to-end accounting tests are not run in this environment; do not treat static checks as runtime certification.
- Permission code and role-template definitions are updated, but database permission seeding and persisted role grants remain unverified and must be completed before enabling this endpoint for non-superuser accounts.

## Safety

No production database or deployment was changed.
