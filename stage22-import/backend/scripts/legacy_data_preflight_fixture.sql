-- Synthetic legacy-shape fixture for CI only. Never run against production.
CREATE TABLE users (
    id integer PRIMARY KEY,
    tenant_id integer NULL,
    email text,
    username text
);
INSERT INTO users VALUES
    (1, 10, 'duplicate@example.test', 'same-user'),
    (2, 10, 'duplicate@example.test', 'same-user'),
    (3, NULL, 'tenantless@example.test', 'tenantless-user');

CREATE TABLE products (
    id integer PRIMARY KEY,
    tenant_id integer NULL,
    sku text,
    uom_id integer NULL,
    qty_on_hand numeric(18,4)
);
INSERT INTO products VALUES
    (1, 10, 'SKU-DUP', NULL, 12.0000),
    (2, 10, 'SKU-DUP', 1, 0.0000),
    (3, NULL, 'SKU-LEGACY', 1, 0.0000);

CREATE TABLE journal_entries (
    id integer PRIMARY KEY,
    tenant_id integer NULL,
    number text,
    state text
);
CREATE TABLE journal_items (
    id integer PRIMARY KEY,
    journal_entry_id integer NOT NULL REFERENCES journal_entries(id),
    debit numeric(18,4) NOT NULL DEFAULT 0,
    credit numeric(18,4) NOT NULL DEFAULT 0
);
INSERT INTO journal_entries VALUES (1, 10, 'JE-001', 'posted');
INSERT INTO journal_items VALUES
    (1, 1, 100.00, 0.00),
    (2, 1, 0.00, 90.00);

CREATE TABLE legacy_fk_parent (id integer PRIMARY KEY);
CREATE TABLE legacy_fk_child (parent_id integer);
-- Load an orphan before adding the NOT VALID constraint, matching a legacy
-- table that receives a constraint without validating historical rows.
INSERT INTO legacy_fk_child(parent_id) VALUES (999);
ALTER TABLE legacy_fk_child
    ADD CONSTRAINT legacy_fk_child_parent_fk
    FOREIGN KEY (parent_id) REFERENCES legacy_fk_parent(id) NOT VALID;
