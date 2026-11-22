# Commercial, Inventory & Accounting Schema Reconciliation — 2026-11-21

## Scope

Source-level comparison of the current ORM models with the original committed migration. Reviewed:
- `app/models/crm.py` (Customer, Lead, Opportunity)
- `app/models/inventory.py` (Product, ProductCategory, Warehouse, StockMove)
- `app/models/accounting.py` (Account, JournalEntry, JournalItem, Partner)
- `alembic/versions/001_initial_schema.py`
- `alembic/versions/add_missing_orm_tables_68.py`

This review does not query or alter production data. It is not a production migration.

## Executive conclusion

The original schema is a broad legacy ERP schema. The current ORM has evolved into a more normalized, tenant-aware model. Several table pairs are semantic successors, not simple column additions. Data migration therefore requires explicit mapping and reconciliation, not blind renames or Alembic autogenerate.

## A. CRM and commercial parties

### Legacy `partners` versus current `customers` and `partners`

The initial migration creates one `partners` table containing customer/supplier identity, contact details, address, credit limit, payment terms, and an unconstrained `partner_type`.

The current ORM separates responsibilities:
- `Customer` in `crm.py`: customer lifecycle, type/status, sales profile, contacts, addresses, territory, customer group, payment term, price list and customer-specific credit controls.
- `Partner` in `accounting.py`: accounting-facing commercial party reference used by journal items and other financial flows.

Do not rename the legacy `partners` table to `customers` or drop it. A safe migration must decide whether each legacy partner becomes a Customer, a financial Partner, both, or neither based on `partner_type` and actual references. Preserve the original UUID where possible and create a traceable crosswalk if one legacy record fans out to multiple canonical records.

Candidate mappings that need data validation:
- `partners.name` → `customers.name` and/or financial partner display name.
- `partners.code` → tenant-scoped customer code, after duplicate checks.
- email, phone, website and address fields → customer/contact/address structures.
- credit limit and payment terms → customer financial profile/payment-term records.
- `partner_type` → classification, not a direct enum mapping until all distinct values are inventoried.
- `metadata` and notes must be retained or explicitly mapped; do not discard.

Current Customer requires `tenant_id` through TenantMixin; the original partners tenant is nullable. Tenant attribution is a blocking precondition.

### Legacy `partner_contacts` versus current `contacts`

The old table uses `partner_id` and required first/last names. Current `contacts` references `customers.id` and includes richer contact identity. Migration must resolve the parent customer via the partner crosswalk and retain contact IDs where safe. Do not assume every legacy partner is a customer.

### Leads and opportunities

Legacy leads/opportunities reference `partners` through `partner_id`, and use free-form string statuses/stages. Current models reference `customers`, `teams`, `users`, and use enum-backed status/stage fields. Required work:
- map partner references through the approved customer crosswalk;
- inventory every distinct status/stage value before enum conversion;
- preserve unrecognized values in a staging/exception table and stop enum enforcement until mapped;
- reconcile old assignment fields with current owner/team relationships;
- retain converted-lead links and historical timestamps.

## B. Products and inventory

### `categories` versus `product_categories`

Legacy products reference `categories`; current Product references `product_categories`. This is a parent-table replacement, not a safe column rename. Build a category crosswalk preserving IDs and parent hierarchy, validate tenant assignment and duplicate tenant/code values, then map each product category reference.

### `products`

Legacy columns include:
- globally unique `sku`, barcode, description, category_id;
- `is_saleable`, `is_purchasable`, `is_storable`, `is_active`;
- list/cost/average cost, on-hand/available/reserved quantities;
- nullable `uom_id`, legacy `uom_name`;
- legacy `attributes` JSONB, image_url and tenant_id.

Current Product includes:
- tenant-scoped unique SKU;
- name/name_ar and separate sales/purchase descriptions;
- enum product_type/status;
- product_categories FK, variants, tags, barcode metadata;
- mandatory `uom_id`, purchase/sales UOMs;
- cost/sale/list/minimum prices, currency;
- inventory/valuation/reorder/lot/serial/expiration settings;
- dimensions, weight and commercial availability flags.

Critical conversion issues:
1. `is_saleable` / `is_purchasable` / `is_storable` are not identical to current `saleable` / `purchasable` / `is_stockable` until application semantics are confirmed.
2. Legacy `is_active` must map to current ProductStatus using a reviewed mapping.
3. Legacy stock quantity columns should not be copied into a single current Product field without reconciling stock ledger and stock_quantities; current inventory uses locations and quantity records.
4. Existing products with null UOM cannot satisfy the current non-null `uom_id`. Create/map valid UOM rows first; do not silently assign an arbitrary unit.
5. Numeric precision changes from legacy 12,2 to current generally 18,4; check rounding and overflow before conversion.
6. Legacy attributes JSON and image_url need explicit destinations; retain unmapped JSON in a legacy payload field/table until verified.
7. SKU global uniqueness must be checked before tenant-scoped uniqueness is introduced.

### Warehouses and stock movements

Legacy `stock_moves` stores one `warehouse_id`, optional `location_id`, string `uom`, `quantity`, cost_price/total_value, origin/origin_id and a unique required `reference`.

Current `StockMove` stores:
- `number` as required identifier and optional `reference`;
- `product_id`, `quantity`, `quantity_done`, mandatory UOM FK;
- `location_from_id`, `location_to_id`, optional warehouse_from/to IDs;
- enum move_type/state, expected/date/done dates;
- unit_cost/total_cost, partner and lot/serial/expiration metadata.

A single legacy warehouse cannot always be mapped to both from/to warehouses. Movement direction and origin must be interpreted; inbound/outbound/internal records need explicit transformation rules. Preserve legacy reference values, but do not assume they uniquely represent current move numbers. The current ORM's reference index is not unique, unlike the legacy unique constraint. Do not remove uniqueness until duplicate semantics and application references are understood.

Warehouse codes are tenant-scoped in the current model, while legacy codes were globally unique. Confirm duplicate and tenant distribution first.

## C. Accounting

### `chart_of_accounts` versus `accounts`

The initial migration creates `chart_of_accounts` with code, name, string account_type, parent, balance, currency, active/reconcilable flags and description.

Current ORM uses `accounts` with tenant-scoped code, name/name_ar, enum account_type/category, hierarchy level/is_parent, active/header/reconcilable/contra flags, separate debit and credit balances, and optional currency relation.

Do not drop or rename `chart_of_accounts`. Required mapping:
- create canonical Account records and preserve UUIDs where feasible;
- map account_type strings only after inventorying all values;
- map balance to debit/credit opening balances only after determining sign convention and historical cutoff;
- preserve currency string by resolving it to a Currency row;
- preserve hierarchy and validate no cycles;
- check duplicate codes per tenant before adding unique constraints.

### `journal_entry_lines` versus `journal_items`

Legacy lines reference `chart_of_accounts`, use amount precision 15,2, and include description, currency and reconciled flag. Current JournalItem references `accounts`, carries sequence, debit/credit, balance_after, date, optional Partner, analytic account and reconciliation relations, and inherits tenant/audit/soft-delete fields.

A line migration requires both account and partner crosswalks. Do not discard legacy description/currency/reconciled values; map them to current supported fields or retain them in a legacy extension. Validate debit/credit non-negativity, one-sided posting, and totals per journal entry before enforcing constraints.

### `journal_entries`

Legacy uses `reference`, `journal_type`, `narration`, `is_posted`, posted_at and globally unique number. Current uses `ref`, `move_type`, `state`, totals, fiscal period/journal links, reversal relationships, source idempotency fields, posting actor/time, and tenant-aware indexes.

The legacy `reference` → current `ref` mapping is a candidate rename/copy, but journal_type → move_type and is_posted → state require explicit enum/state mapping. Current model also has a balanced-total check and source idempotency partial unique index; validate historical entries before creating these constraints. Do not set totals from incomplete data; derive from verified journal lines and report imbalances.

### Accounting currency and precision

Legacy accounting uses string currency codes and generally 15,2 precision; current models use Currency FKs and Numeric(18,4) for core amounts. Currency resolution and rounding policy must be explicit. Historical amounts must not be silently rounded or assigned a default currency.

## Required data preflight

Before a migration can be authored:
- row counts and FK references for partners, contacts, leads, opportunities;
- partner_type values and downstream references by table;
- tenant_id null counts and per-tenant duplicate code/SKU checks;
- category hierarchy and product category reference counts;
- products with null/invalid UOM, quantity snapshots versus stock ledger;
- movement types, states, direction and duplicate references;
- account type values, account hierarchy, balances and currencies;
- journal entry states/types, line counts, unbalanced entries and currency distribution;
- orphan references and UUID preservation/crosswalk strategy.

## Safe implementation plan

1. Freeze canonical mappings and enum value maps from actual data.
2. Add compatibility/crosswalk tables and additive nullable canonical structures on a disposable copy.
3. Migrate parent/master data first: tenants, currencies, UOM, categories, customers/partners, warehouses and accounts.
4. Migrate dependent rows: contacts, leads/opportunities, products, stock locations/quantities/moves, journals and journal items.
5. Run referential-integrity, balance, quantity-ledger and tenant-isolation assertions.
6. Compare source/destination counts and financial/inventory control totals.
7. Test application reads/writes against migrated disposable data.
8. Only after backup/restore rehearsal and formal review consider production rollout.
9. Remove legacy structures only in a separate later release after proven cutover.

## Decision

No production migration is safe to apply yet. The legacy partner/customer model, product/UOM/category model, stock movement semantics, and accounting chart/journal models require explicit data crosswalks and control-total validation. No live Supabase data was changed in this review.
