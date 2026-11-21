-- Nexus ERP legacy-data preflight (READ ONLY)
-- Run only against a restored/disposable COPY of the legacy database.
-- This script creates a session-local temp table; it does not modify application data.
-- Usage: psql "$LEGACY_DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/legacy_data_preflight.sql

CREATE TEMP TABLE nexus_preflight_findings (
    check_name text NOT NULL,
    object_name text NOT NULL,
    issue_count bigint NOT NULL,
    details text
) ON COMMIT PRESERVE ROWS;

DO $preflight$
DECLARE
    tbl text;
    col text;
    n bigint;
    candidate record;
    sql_text text;
BEGIN
    -- Tenant ownership: these entities must be reviewed before tenant-scoped import.
    FOREACH tbl IN ARRAY ARRAY[
        'users','roles','partners','customers','products','accounts',
        'journal_entries','purchase_orders','sale_orders','warehouses','stock_moves'
    ] LOOP
        IF to_regclass(format('public.%I', tbl)) IS NOT NULL
           AND EXISTS (
               SELECT 1 FROM information_schema.columns
               WHERE table_schema='public' AND table_name=tbl AND column_name='tenant_id'
           ) THEN
            EXECUTE format('SELECT count(*) FROM public.%I WHERE tenant_id IS NULL', tbl) INTO n;
            INSERT INTO nexus_preflight_findings
            VALUES ('NULL_TENANT_ID', tbl, n, 'Rows require an explicit tenant mapping; do not assign a default tenant automatically.');
        END IF;
    END LOOP;

    -- Duplicate business identifiers, scoped by tenant where available.
    FOR candidate IN
        SELECT * FROM (VALUES
            ('users','email'), ('users','username'),
            ('products','sku'), ('partners','code'), ('customers','code'),
            ('purchase_orders','number'), ('sale_orders','number'),
            ('journal_entries','number')
        ) AS v(table_name, column_name)
    LOOP
        IF to_regclass(format('public.%I', candidate.table_name)) IS NOT NULL
           AND EXISTS (
               SELECT 1 FROM information_schema.columns
               WHERE table_schema='public' AND table_name=candidate.table_name
                 AND column_name=candidate.column_name
           ) THEN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name=candidate.table_name
                  AND column_name='tenant_id'
            ) THEN
                sql_text := format(
                    'SELECT count(*) FROM (SELECT tenant_id, %1$I FROM public.%2$I WHERE %1$I IS NOT NULL GROUP BY tenant_id, %1$I HAVING count(*) > 1) d',
                    candidate.column_name, candidate.table_name
                );
            ELSE
                sql_text := format(
                    'SELECT count(*) FROM (SELECT %1$I FROM public.%2$I WHERE %1$I IS NOT NULL GROUP BY %1$I HAVING count(*) > 1) d',
                    candidate.column_name, candidate.table_name
                );
            END IF;
            EXECUTE sql_text INTO n;
            INSERT INTO nexus_preflight_findings
            VALUES ('DUPLICATE_IDENTIFIER', candidate.table_name||'.'||candidate.column_name, n,
                    'Resolve duplicates before creating tenant-scoped unique constraints.');
        END IF;
    END LOOP;

    -- Products without UOM are not safe to migrate into the current required-UOM model.
    IF to_regclass('public.products') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='products' AND column_name='uom_id') THEN
        EXECUTE 'SELECT count(*) FROM public.products WHERE uom_id IS NULL' INTO n;
        INSERT INTO nexus_preflight_findings
        VALUES ('MISSING_UOM', 'products.uom_id', n, 'Map each product to a valid canonical unit of measure.');
    END IF;

    -- Report unvalidated foreign keys. Existing validated FKs are enforced by PostgreSQL.
    INSERT INTO nexus_preflight_findings
    SELECT 'UNVALIDATED_FOREIGN_KEY',
           c.conrelid::regclass::text||'.'||c.conname,
           1,
           pg_get_constraintdef(c.oid)
    FROM pg_constraint c
    JOIN pg_namespace ns ON ns.oid=c.connamespace
    WHERE c.contype='f' AND NOT c.convalidated AND ns.nspname='public';

    -- Double-entry balance check, only when the expected current line schema is present.
    IF to_regclass('public.journal_entries') IS NOT NULL
       AND to_regclass('public.journal_items') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='journal_items' AND column_name='journal_entry_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='journal_items' AND column_name='debit')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='journal_items' AND column_name='credit') THEN
        EXECUTE $q$
            SELECT count(*) FROM (
                SELECT je.id
                FROM public.journal_entries je
                JOIN public.journal_items ji ON ji.journal_entry_id=je.id
                WHERE COALESCE(je.state::text,'')='posted'
                GROUP BY je.id
                HAVING abs(sum(COALESCE(ji.debit,0))-sum(COALESCE(ji.credit,0))) > 0.0001
            ) unbalanced
        $q$ INTO n;
        INSERT INTO nexus_preflight_findings
        VALUES ('UNBALANCED_POSTED_JOURNAL', 'journal_entries/journal_items', n,
                'Investigate source totals, currency precision, rounding, and missing lines.');
    END IF;

    -- Inventory snapshot/ledger values must be reconciled; report available totals, not assumed parity.
    IF to_regclass('public.products') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='products' AND column_name='qty_on_hand')
       AND to_regclass('public.stock_moves') IS NOT NULL THEN
        EXECUTE 'SELECT count(*) FROM public.products WHERE qty_on_hand IS NOT NULL' INTO n;
        INSERT INTO nexus_preflight_findings
        VALUES ('LEGACY_STOCK_SNAPSHOT_PRESENT', 'products.qty_on_hand', n,
                'Reconcile product snapshots to posted stock movements by tenant, product, location, and UOM before import.');
    END IF;
END
$preflight$;

SELECT check_name, object_name, issue_count, details
FROM nexus_preflight_findings
ORDER BY check_name, object_name;

SELECT
    count(*) FILTER (WHERE issue_count > 0) AS checks_with_findings,
    COALESCE(sum(issue_count),0) AS total_findings
FROM nexus_preflight_findings;
