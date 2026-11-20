# Stage 20 — Bank reconciliation foundation

## Delivered

- Added tenant-scoped `BankStatement` and `BankStatementLine` models.
- Added a migration after `add_supplier_payment_reversal_stage19`.
- Added APIs to create a statement, add statement lines, match a line to a posted bank-account journal item, and finalize a statement.
- Enforced bank-account category and `is_reconcilable` checks.
- Added database uniqueness for statement numbers, line numbers, matched journal items, and non-empty external references within a statement.
- Matching validates tenant, posted state, bank account, amount, direction, and exact transaction date. Bank-statement credits (cash inflows) map to debit journal lines on the company's bank asset account; statement debits map to journal credits.
- Finalization recalculates line totals and requires the opening balance plus credits minus debits to equal the closing balance. All lines must be matched before finalization.
- Statement/line writes are tenant-scoped and statement locks serialize modifications to the same statement.

## Explicit limitations

- This stage provides statement-entry primitives and matching APIs; it does not yet parse CSV, XLSX, OFX, or CAMT files.
- It does not create accounting entries automatically for bank fees, interest, or unidentified movements. Such entries must be posted through the normal journal workflow before matching.
- Matching is deliberately exact on date, amount, and direction. Tolerant matching, split/combined matches, and approval of date/value differences are deferred.
- It does not connect to bank APIs or store uploaded source files.
- No PostgreSQL migration or concurrent integration test was run.

## Validation

- Python `compileall` completed successfully.
- SQLAlchemy model imports and `configure_mappers()` completed successfully; metadata contains 102 tables including both bank tables.
- Alembic history reports a single head: `add_bank_reconciliation_stage20`.
- API module import could not be completed because required runtime settings `DATABASE_URL` and `SECRET_KEY` are absent in this environment.
- Offline SQL generation is blocked by a pre-existing earlier migration (`add_journal_source_idempotency`) which calls `.fetchall()` on an offline operation result. This is not caused by the Stage 20 migration, but it prevents validating the entire chain in offline mode.
- No live database, real bank statement, API request, or concurrency behavior has been verified.
