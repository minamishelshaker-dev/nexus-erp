CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 001_initial_schema

CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    username VARCHAR(100) NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    first_name VARCHAR(100), 
    last_name VARCHAR(100), 
    phone VARCHAR(20), 
    avatar_url VARCHAR(500), 
    is_active BOOLEAN NOT NULL, 
    is_verified BOOLEAN NOT NULL, 
    is_superuser BOOLEAN NOT NULL, 
    last_login TIMESTAMP WITH TIME ZONE, 
    preferences JSONB NOT NULL, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    is_deleted BOOLEAN NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    UNIQUE (email), 
    UNIQUE (username)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE UNIQUE INDEX ix_users_username ON users (username);

CREATE INDEX ix_users_tenant ON users (tenant_id);

CREATE TABLE roles (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    description TEXT, 
    is_system BOOLEAN NOT NULL, 
    permissions JSONB NOT NULL, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name), 
    UNIQUE (code)
);

CREATE UNIQUE INDEX ix_roles_code ON roles (code);

CREATE TABLE user_roles (
    user_id UUID NOT NULL, 
    role_id UUID NOT NULL, 
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (user_id, role_id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE
);

CREATE TABLE refresh_tokens (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID NOT NULL, 
    token_hash VARCHAR(255) NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    revoked BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    UNIQUE (token_hash)
);

CREATE UNIQUE INDEX ix_refresh_tokens_hash ON refresh_tokens (token_hash);

CREATE TABLE categories (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    description TEXT, 
    parent_id UUID, 
    is_active BOOLEAN NOT NULL, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    is_deleted BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (code), 
    FOREIGN KEY(parent_id) REFERENCES categories (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_categories_code ON categories (code);

CREATE TABLE products (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    sku VARCHAR(100) NOT NULL, 
    barcode VARCHAR(100), 
    description TEXT, 
    category_id UUID, 
    product_type VARCHAR(50) NOT NULL, 
    is_saleable BOOLEAN NOT NULL, 
    is_purchasable BOOLEAN NOT NULL, 
    is_storable BOOLEAN NOT NULL, 
    list_price NUMERIC(12, 2) NOT NULL, 
    cost_price NUMERIC(12, 2) NOT NULL, 
    average_cost NUMERIC(12, 2) NOT NULL, 
    quantity_on_hand NUMERIC(12, 2) NOT NULL, 
    quantity_available NUMERIC(12, 2) NOT NULL, 
    quantity_reserved NUMERIC(12, 2) NOT NULL, 
    reorder_point NUMERIC(12, 2) NOT NULL, 
    reorder_quantity NUMERIC(12, 2) NOT NULL, 
    uom_id UUID, 
    uom_name VARCHAR(50) NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    track_inventory BOOLEAN NOT NULL, 
    weight NUMERIC(10, 2), 
    volume NUMERIC(10, 2), 
    image_url VARCHAR(500), 
    attributes JSONB NOT NULL, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    is_deleted BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (sku), 
    FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_products_sku ON products (sku);

CREATE INDEX ix_products_category ON products (category_id);

CREATE TABLE warehouses (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    address TEXT, 
    city VARCHAR(100), 
    country VARCHAR(100), 
    is_active BOOLEAN NOT NULL, 
    is_default BOOLEAN NOT NULL, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    is_deleted BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (code)
);

CREATE UNIQUE INDEX ix_warehouses_code ON warehouses (code);

CREATE TABLE stock_moves (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    reference VARCHAR(100) NOT NULL, 
    product_id UUID NOT NULL, 
    warehouse_id UUID NOT NULL, 
    location_id UUID, 
    move_type VARCHAR(50) NOT NULL, 
    quantity NUMERIC(12, 2) NOT NULL, 
    uom VARCHAR(50) NOT NULL, 
    cost_price NUMERIC(12, 2), 
    total_value NUMERIC(12, 2), 
    state VARCHAR(50) NOT NULL, 
    origin VARCHAR(100), 
    origin_id UUID, 
    notes TEXT, 
    date_done TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID, 
    created_by_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (reference), 
    FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT, 
    FOREIGN KEY(warehouse_id) REFERENCES warehouses (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX ix_stock_moves_reference ON stock_moves (reference);

CREATE INDEX ix_stock_moves_product ON stock_moves (product_id);

CREATE INDEX ix_stock_moves_warehouse ON stock_moves (warehouse_id);

CREATE TABLE partners (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    partner_type VARCHAR(50) NOT NULL, 
    tax_id VARCHAR(50), 
    email VARCHAR(255), 
    phone VARCHAR(50), 
    website VARCHAR(255), 
    address_line1 VARCHAR(255), 
    address_line2 VARCHAR(255), 
    city VARCHAR(100), 
    state VARCHAR(100), 
    country VARCHAR(100), 
    postal_code VARCHAR(20), 
    credit_limit NUMERIC(12, 2) NOT NULL, 
    credit_used NUMERIC(12, 2) NOT NULL, 
    payment_terms INTEGER NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    notes TEXT, 
    metadata JSONB NOT NULL, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    is_deleted BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (code)
);

CREATE UNIQUE INDEX ix_partners_code ON partners (code);

CREATE INDEX ix_partners_type ON partners (partner_type);

CREATE TABLE partner_contacts (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    partner_id UUID NOT NULL, 
    first_name VARCHAR(100) NOT NULL, 
    last_name VARCHAR(100) NOT NULL, 
    title VARCHAR(100), 
    email VARCHAR(255), 
    phone VARCHAR(50), 
    is_primary BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(partner_id) REFERENCES partners (id) ON DELETE CASCADE
);

CREATE INDEX ix_partner_contacts_partner ON partner_contacts (partner_id);

CREATE TABLE leads (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    company_name VARCHAR(255), 
    email VARCHAR(255), 
    phone VARCHAR(50), 
    source VARCHAR(100), 
    status VARCHAR(50) NOT NULL, 
    priority VARCHAR(20) NOT NULL, 
    estimated_value NUMERIC(12, 2), 
    assigned_to_id UUID, 
    notes TEXT, 
    converted_at TIMESTAMP WITH TIME ZONE, 
    converted_to_id UUID, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_leads_status ON leads (status);

CREATE TABLE opportunities (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    partner_id UUID, 
    lead_id UUID, 
    stage VARCHAR(50) NOT NULL, 
    probability INTEGER NOT NULL, 
    expected_revenue NUMERIC(12, 2) NOT NULL, 
    expected_close_date DATE, 
    assigned_to_id UUID, 
    description TEXT, 
    lost_reason TEXT, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    closed_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(partner_id) REFERENCES partners (id) ON DELETE SET NULL, 
    FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE SET NULL
);

CREATE INDEX ix_opportunities_stage ON opportunities (stage);

CREATE INDEX ix_opportunities_partner ON opportunities (partner_id);

CREATE TABLE sales_quotations (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    number VARCHAR(50) NOT NULL, 
    partner_id UUID NOT NULL, 
    date_quotation DATE NOT NULL, 
    valid_until DATE, 
    state VARCHAR(50) NOT NULL, 
    amount_untaxed NUMERIC(12, 2) NOT NULL, 
    amount_tax NUMERIC(12, 2) NOT NULL, 
    amount_total NUMERIC(12, 2) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    payment_terms INTEGER NOT NULL, 
    notes TEXT, 
    terms_conditions TEXT, 
    salesperson_id UUID, 
    tenant_id UUID, 
    created_by_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (number), 
    FOREIGN KEY(partner_id) REFERENCES partners (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX ix_sales_quotations_number ON sales_quotations (number);

CREATE INDEX ix_sales_quotations_partner ON sales_quotations (partner_id);

CREATE TABLE sales_orders (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    number VARCHAR(50) NOT NULL, 
    quotation_id UUID, 
    partner_id UUID NOT NULL, 
    date_order DATE NOT NULL, 
    date_planned DATE, 
    state VARCHAR(50) NOT NULL, 
    amount_untaxed NUMERIC(12, 2) NOT NULL, 
    amount_tax NUMERIC(12, 2) NOT NULL, 
    amount_total NUMERIC(12, 2) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    payment_terms INTEGER NOT NULL, 
    shipping_address_id UUID, 
    notes TEXT, 
    salesperson_id UUID, 
    tenant_id UUID, 
    created_by_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (number), 
    FOREIGN KEY(quotation_id) REFERENCES sales_quotations (id) ON DELETE SET NULL, 
    FOREIGN KEY(partner_id) REFERENCES partners (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX ix_sales_orders_number ON sales_orders (number);

CREATE INDEX ix_sales_orders_partner ON sales_orders (partner_id);

CREATE INDEX ix_sales_orders_state ON sales_orders (state);

CREATE TABLE sales_order_lines (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    order_id UUID NOT NULL, 
    product_id UUID NOT NULL, 
    description TEXT, 
    quantity NUMERIC(12, 2) NOT NULL, 
    uom VARCHAR(50) NOT NULL, 
    price_unit NUMERIC(12, 2) NOT NULL, 
    discount NUMERIC(5, 2) NOT NULL, 
    tax_rate NUMERIC(5, 2) NOT NULL, 
    subtotal NUMERIC(12, 2) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(order_id) REFERENCES sales_orders (id) ON DELETE CASCADE, 
    FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
);

CREATE INDEX ix_sales_order_lines_order ON sales_order_lines (order_id);

CREATE TABLE purchase_requisitions (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    number VARCHAR(50) NOT NULL, 
    date_required DATE, 
    state VARCHAR(50) NOT NULL, 
    notes TEXT, 
    requested_by_id UUID, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (number)
);

CREATE TABLE purchase_orders (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    number VARCHAR(50) NOT NULL, 
    requisition_id UUID, 
    partner_id UUID NOT NULL, 
    date_order DATE NOT NULL, 
    date_planned DATE, 
    state VARCHAR(50) NOT NULL, 
    amount_untaxed NUMERIC(12, 2) NOT NULL, 
    amount_tax NUMERIC(12, 2) NOT NULL, 
    amount_total NUMERIC(12, 2) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    notes TEXT, 
    buyer_id UUID, 
    tenant_id UUID, 
    created_by_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (number), 
    FOREIGN KEY(requisition_id) REFERENCES purchase_requisitions (id) ON DELETE SET NULL, 
    FOREIGN KEY(partner_id) REFERENCES partners (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX ix_purchase_orders_number ON purchase_orders (number);

CREATE INDEX ix_purchase_orders_partner ON purchase_orders (partner_id);

CREATE INDEX ix_purchase_orders_state ON purchase_orders (state);

CREATE TABLE purchase_order_lines (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    order_id UUID NOT NULL, 
    product_id UUID NOT NULL, 
    description TEXT, 
    quantity NUMERIC(12, 2) NOT NULL, 
    quantity_received NUMERIC(12, 2) NOT NULL, 
    uom VARCHAR(50) NOT NULL, 
    price_unit NUMERIC(12, 2) NOT NULL, 
    tax_rate NUMERIC(5, 2) NOT NULL, 
    subtotal NUMERIC(12, 2) NOT NULL, 
    date_planned DATE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(order_id) REFERENCES purchase_orders (id) ON DELETE CASCADE, 
    FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
);

CREATE INDEX ix_purchase_order_lines_order ON purchase_order_lines (order_id);

CREATE TABLE chart_of_accounts (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    account_type VARCHAR(50) NOT NULL, 
    parent_id UUID, 
    balance NUMERIC(15, 2) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    is_reconcilable BOOLEAN NOT NULL, 
    description TEXT, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    is_deleted BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (code), 
    FOREIGN KEY(parent_id) REFERENCES chart_of_accounts (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_chart_of_accounts_code ON chart_of_accounts (code);

CREATE TABLE journal_entries (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    number VARCHAR(50) NOT NULL, 
    date DATE NOT NULL, 
    journal_type VARCHAR(50) NOT NULL, 
    reference VARCHAR(100), 
    narration TEXT, 
    state VARCHAR(50) NOT NULL, 
    is_posted BOOLEAN NOT NULL, 
    posted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID, 
    created_by_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (number)
);

CREATE UNIQUE INDEX ix_journal_entries_number ON journal_entries (number);

CREATE INDEX ix_journal_entries_date ON journal_entries (date);

CREATE TABLE journal_entry_lines (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    entry_id UUID NOT NULL, 
    account_id UUID NOT NULL, 
    partner_id UUID, 
    description TEXT, 
    debit NUMERIC(15, 2) NOT NULL, 
    credit NUMERIC(15, 2) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    reconciled BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(entry_id) REFERENCES journal_entries (id) ON DELETE CASCADE, 
    FOREIGN KEY(account_id) REFERENCES chart_of_accounts (id) ON DELETE RESTRICT, 
    FOREIGN KEY(partner_id) REFERENCES partners (id) ON DELETE SET NULL
);

CREATE INDEX ix_journal_entry_lines_entry ON journal_entry_lines (entry_id);

CREATE INDEX ix_journal_entry_lines_account ON journal_entry_lines (account_id);

CREATE TABLE bills_of_materials (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    product_id UUID NOT NULL, 
    product_qty NUMERIC(12, 2) NOT NULL, 
    product_uom VARCHAR(50) NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    routing TEXT, 
    notes TEXT, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (code), 
    FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX ix_bom_code ON bills_of_materials (code);

CREATE TABLE bom_lines (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    bom_id UUID NOT NULL, 
    product_id UUID NOT NULL, 
    product_qty NUMERIC(12, 2) NOT NULL, 
    product_uom VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(bom_id) REFERENCES bills_of_materials (id) ON DELETE CASCADE, 
    FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
);

CREATE INDEX ix_bom_lines_bom ON bom_lines (bom_id);

CREATE TABLE manufacturing_orders (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    number VARCHAR(50) NOT NULL, 
    bom_id UUID, 
    product_id UUID NOT NULL, 
    product_qty NUMERIC(12, 2) NOT NULL, 
    product_uom VARCHAR(50) NOT NULL, 
    date_planned_start DATE, 
    date_planned_finished DATE, 
    date_start TIMESTAMP WITH TIME ZONE, 
    date_finished TIMESTAMP WITH TIME ZONE, 
    state VARCHAR(50) NOT NULL, 
    progress NUMERIC(5, 2) NOT NULL, 
    notes TEXT, 
    tenant_id UUID, 
    created_by_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (number), 
    FOREIGN KEY(bom_id) REFERENCES bills_of_materials (id) ON DELETE SET NULL, 
    FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX ix_manufacturing_orders_number ON manufacturing_orders (number);

CREATE INDEX ix_manufacturing_orders_state ON manufacturing_orders (state);

CREATE TABLE work_centers (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    capacity NUMERIC(12, 2) NOT NULL, 
    cost_hour NUMERIC(10, 2) NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    notes TEXT, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (code)
);

CREATE UNIQUE INDEX ix_work_centers_code ON work_centers (code);

CREATE TABLE employees (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    employee_number VARCHAR(50) NOT NULL, 
    first_name VARCHAR(100) NOT NULL, 
    last_name VARCHAR(100) NOT NULL, 
    email VARCHAR(255), 
    phone VARCHAR(50), 
    department VARCHAR(100), 
    position VARCHAR(100), 
    manager_id UUID, 
    user_id UUID, 
    hire_date DATE, 
    termination_date DATE, 
    employment_type VARCHAR(50) NOT NULL, 
    status VARCHAR(50) NOT NULL, 
    salary NUMERIC(12, 2), 
    salary_currency VARCHAR(3) NOT NULL, 
    address TEXT, 
    notes TEXT, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    is_deleted BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (employee_number), 
    FOREIGN KEY(manager_id) REFERENCES employees (id) ON DELETE SET NULL, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_employees_number ON employees (employee_number);

CREATE INDEX ix_employees_status ON employees (status);

CREATE TABLE attendance_records (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    employee_id UUID NOT NULL, 
    date DATE NOT NULL, 
    check_in TIMESTAMP WITH TIME ZONE, 
    check_out TIMESTAMP WITH TIME ZONE, 
    hours_worked NUMERIC(5, 2) NOT NULL, 
    overtime_hours NUMERIC(5, 2) NOT NULL, 
    status VARCHAR(50) NOT NULL, 
    notes TEXT, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(employee_id) REFERENCES employees (id) ON DELETE CASCADE
);

CREATE INDEX ix_attendance_employee_date ON attendance_records (employee_id, date);

CREATE TABLE projects (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    description TEXT, 
    customer_id UUID, 
    manager_id UUID, 
    start_date DATE, 
    end_date DATE, 
    budget NUMERIC(15, 2) NOT NULL, 
    status VARCHAR(50) NOT NULL, 
    progress NUMERIC(5, 2) NOT NULL, 
    color VARCHAR(7) NOT NULL, 
    tenant_id UUID, 
    created_by_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (code), 
    FOREIGN KEY(customer_id) REFERENCES partners (id) ON DELETE SET NULL, 
    FOREIGN KEY(manager_id) REFERENCES employees (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_projects_code ON projects (code);

CREATE INDEX ix_projects_status ON projects (status);

CREATE TABLE project_tasks (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    project_id UUID NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    description TEXT, 
    assignee_id UUID, 
    parent_id UUID, 
    planned_hours NUMERIC(6, 2) NOT NULL, 
    spent_hours NUMERIC(6, 2) NOT NULL, 
    progress NUMERIC(5, 2) NOT NULL, 
    priority VARCHAR(20) NOT NULL, 
    status VARCHAR(50) NOT NULL, 
    due_date DATE, 
    tags JSONB NOT NULL, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
    FOREIGN KEY(assignee_id) REFERENCES employees (id) ON DELETE SET NULL, 
    FOREIGN KEY(parent_id) REFERENCES project_tasks (id) ON DELETE CASCADE
);

CREATE INDEX ix_project_tasks_project ON project_tasks (project_id);

CREATE INDEX ix_project_tasks_status ON project_tasks (status);

CREATE TABLE timesheets (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    employee_id UUID NOT NULL, 
    project_id UUID, 
    task_id UUID, 
    date DATE NOT NULL, 
    hours NUMERIC(5, 2) NOT NULL, 
    description TEXT, 
    billable BOOLEAN NOT NULL, 
    approved BOOLEAN NOT NULL, 
    approved_by_id UUID, 
    tenant_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(employee_id) REFERENCES employees (id) ON DELETE CASCADE, 
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE SET NULL, 
    FOREIGN KEY(task_id) REFERENCES project_tasks (id) ON DELETE SET NULL
);

CREATE INDEX ix_timesheets_employee ON timesheets (employee_id);

CREATE INDEX ix_timesheets_project ON timesheets (project_id);

Initial schema migration completed successfully!
INSERT INTO alembic_version (version_num) VALUES ('001_initial_schema') RETURNING alembic_version.version_num;

-- Running upgrade 001_initial_schema -> add_tenant_billing

CREATE TYPE tenant_status AS ENUM ('trial', 'active', 'past_due', 'suspended', 'cancelled', 'churned');

CREATE TYPE plan_type AS ENUM ('basic', 'pro', 'enterprise');

CREATE TYPE audit_action AS ENUM (
            'login', 'logout', 'login_failed', 'password_reset', 'password_changed',
            'create', 'read', 'update', 'delete', 'bulk_create', 'bulk_update', 'bulk_delete',
            'export', 'import', 'system_config', 'backup', 'restore',
            'user_invite', 'user_activate', 'user_deactivate', 'user_role_change',
            'subscription_create', 'subscription_update', 'subscription_cancel',
            'payment_success', 'payment_failed',
            'tenant_create', 'tenant_update', 'tenant_suspend', 'tenant_reactivate'
        );

CREATE TABLE plans (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    description TEXT, 
    plan_type plan_type NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    is_public BOOLEAN NOT NULL, 
    monthly_price NUMERIC(10, 2) NOT NULL, 
    yearly_price NUMERIC(10, 2) NOT NULL, 
    stripe_price_id_monthly VARCHAR(100), 
    stripe_price_id_yearly VARCHAR(100), 
    max_users INTEGER NOT NULL, 
    max_storage_mb INTEGER NOT NULL, 
    max_products INTEGER NOT NULL, 
    max_customers INTEGER NOT NULL, 
    trial_days INTEGER NOT NULL, 
    features JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    is_deleted BOOLEAN NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    deleted_by_id UUID, 
    created_by_id UUID, 
    updated_by_id UUID, 
    PRIMARY KEY (id), 
    UNIQUE (code)
);

CREATE UNIQUE INDEX ix_plans_code ON plans (code);

CREATE TABLE tenants (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    subdomain VARCHAR(100) NOT NULL, 
    slug VARCHAR(100) NOT NULL, 
    description TEXT, 
    logo_url VARCHAR(500), 
    contact_email VARCHAR(255) NOT NULL, 
    contact_phone VARCHAR(20), 
    address TEXT, 
    city VARCHAR(100), 
    state VARCHAR(100), 
    country VARCHAR(100), 
    postal_code VARCHAR(20), 
    status tenant_status NOT NULL, 
    plan_type plan_type NOT NULL, 
    stripe_customer_id VARCHAR(100), 
    stripe_subscription_id VARCHAR(100), 
    subscription_start TIMESTAMP WITH TIME ZONE, 
    subscription_end TIMESTAMP WITH TIME ZONE, 
    trial_start TIMESTAMP WITH TIME ZONE, 
    trial_end TIMESTAMP WITH TIME ZONE, 
    max_users INTEGER NOT NULL, 
    current_users INTEGER NOT NULL, 
    max_storage_mb INTEGER NOT NULL, 
    current_storage_mb INTEGER NOT NULL, 
    max_products INTEGER NOT NULL, 
    current_products INTEGER NOT NULL, 
    max_customers INTEGER NOT NULL, 
    current_customers INTEGER NOT NULL, 
    api_calls_limit INTEGER NOT NULL, 
    api_calls_used INTEGER NOT NULL, 
    features JSONB NOT NULL, 
    settings JSONB NOT NULL, 
    schema_name VARCHAR(100), 
    is_active BOOLEAN NOT NULL, 
    is_verified BOOLEAN NOT NULL, 
    onboarding_completed BOOLEAN NOT NULL, 
    last_activity_at TIMESTAMP WITH TIME ZONE, 
    suspended_at TIMESTAMP WITH TIME ZONE, 
    cancelled_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    is_deleted BOOLEAN NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    deleted_by_id UUID, 
    created_by_id UUID, 
    updated_by_id UUID, 
    PRIMARY KEY (id), 
    UNIQUE (subdomain), 
    UNIQUE (slug), 
    UNIQUE (stripe_customer_id), 
    UNIQUE (schema_name)
);

CREATE UNIQUE INDEX ix_tenants_subdomain ON tenants (subdomain);

CREATE INDEX ix_tenants_status ON tenants (status);

CREATE INDEX ix_tenants_plan ON tenants (plan_type);

CREATE TABLE subscriptions (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    plan_id UUID, 
    status VARCHAR(50) NOT NULL, 
    stripe_subscription_id VARCHAR(100), 
    stripe_price_id VARCHAR(100), 
    current_period_start TIMESTAMP WITH TIME ZONE, 
    current_period_end TIMESTAMP WITH TIME ZONE, 
    cancel_at_period_end BOOLEAN NOT NULL, 
    cancelled_at TIMESTAMP WITH TIME ZONE, 
    quantity INTEGER NOT NULL, 
    unit_price NUMERIC(10, 2) NOT NULL, 
    trial_start TIMESTAMP WITH TIME ZONE, 
    trial_end TIMESTAMP WITH TIME ZONE, 
    coupon_id VARCHAR(100), 
    discount_percent INTEGER, 
    metadata JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    is_deleted BOOLEAN NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    deleted_by_id UUID, 
    created_by_id UUID, 
    updated_by_id UUID, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    FOREIGN KEY(plan_id) REFERENCES plans (id) ON DELETE SET NULL, 
    UNIQUE (stripe_subscription_id)
);

CREATE INDEX ix_subscriptions_tenant ON subscriptions (tenant_id);

CREATE INDEX ix_subscriptions_status ON subscriptions (status);

CREATE INDEX ix_subscriptions_stripe ON subscriptions (stripe_subscription_id);

CREATE TABLE billing_invoices (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    subscription_id UUID, 
    stripe_invoice_id VARCHAR(100), 
    invoice_number VARCHAR(50) NOT NULL, 
    status VARCHAR(50) NOT NULL, 
    subtotal NUMERIC(12, 2) NOT NULL, 
    tax NUMERIC(12, 2) NOT NULL, 
    discount NUMERIC(12, 2) NOT NULL, 
    total NUMERIC(12, 2) NOT NULL, 
    amount_paid NUMERIC(12, 2) NOT NULL, 
    amount_due NUMERIC(12, 2) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    invoice_date TIMESTAMP WITH TIME ZONE NOT NULL, 
    due_date TIMESTAMP WITH TIME ZONE, 
    paid_at TIMESTAMP WITH TIME ZONE, 
    payment_method VARCHAR(50), 
    charge_id VARCHAR(100), 
    line_items JSONB NOT NULL, 
    description TEXT, 
    notes TEXT, 
    metadata JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    is_deleted BOOLEAN NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    deleted_by_id UUID, 
    created_by_id UUID, 
    updated_by_id UUID, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    FOREIGN KEY(subscription_id) REFERENCES subscriptions (id) ON DELETE SET NULL, 
    UNIQUE (stripe_invoice_id), 
    UNIQUE (invoice_number)
);

CREATE INDEX ix_billing_invoices_tenant ON billing_invoices (tenant_id);

CREATE INDEX ix_billing_invoices_status ON billing_invoices (status);

CREATE INDEX ix_billing_invoices_stripe ON billing_invoices (stripe_invoice_id);

CREATE TABLE audit_logs (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    user_id UUID, 
    action audit_action NOT NULL, 
    resource_type VARCHAR(100) NOT NULL, 
    resource_id VARCHAR(100), 
    resource_name VARCHAR(255), 
    old_values JSONB, 
    new_values JSONB, 
    changes JSONB, 
    ip_address VARCHAR(45), 
    user_agent VARCHAR(500), 
    request_method VARCHAR(10), 
    request_path VARCHAR(500), 
    request_id VARCHAR(100), 
    description TEXT, 
    metadata JSONB NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    error_message TEXT, 
    duration_ms INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_audit_logs_tenant ON audit_logs (tenant_id);

CREATE INDEX ix_audit_logs_user ON audit_logs (user_id);

CREATE INDEX ix_audit_logs_action ON audit_logs (action);

CREATE INDEX ix_audit_logs_resource ON audit_logs (resource_type, resource_id);

CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

INSERT INTO plans (id, code, name, description, plan_type, is_active, is_public, 
                          monthly_price, yearly_price, max_users, max_storage_mb, max_products, 
                          max_customers, trial_days, features)
        VALUES 
        (gen_random_uuid(), 'basic', 'Basic', 'Perfect for small businesses getting started', 
         'basic', true, true, 29, 290, 5, 1024, 100, 500, 14,
         '{"inventory": true, "sales": true, "purchase": true, "accounting": true, "crm": true}'::jsonb),
        (gen_random_uuid(), 'pro', 'Professional', 'Ideal for growing businesses', 
         'pro', true, true, 79, 790, 25, 10240, 1000, 5000, 14,
         '{"inventory": true, "sales": true, "purchase": true, "accounting": true, "crm": true, 
           "manufacturing": true, "ai_features": true, "api_access": true, "custom_reports": true}'::jsonb),
        (gen_random_uuid(), 'enterprise', 'Enterprise', 'For large organizations with custom needs', 
         'enterprise', true, true, 199, 1990, -1, -1, -1, -1, 30,
         '{"inventory": true, "sales": true, "purchase": true, "accounting": true, "crm": true,
           "manufacturing": true, "ai_features": true, "api_access": true, "custom_reports": true,
           "white_label": true, "dedicated_support": true, "custom_integrations": true, "sla": true}'::jsonb);

UPDATE alembic_version SET version_num='add_tenant_billing' WHERE alembic_version.version_num = '001_initial_schema';

-- Running upgrade add_tenant_billing -> add_journal_source_idempotency

CREATE UNIQUE INDEX uq_journal_entry_tenant_source ON journal_entries (tenant_id, source_model, source_id) WHERE source_model IS NOT NULL AND source_id IS NOT NULL AND is_deleted = false;

UPDATE alembic_version SET version_num='add_journal_source_idempotency' WHERE alembic_version.version_num = 'add_tenant_billing';

-- Running upgrade add_journal_source_idempotency -> add_supplier_payments_stage18

CREATE TABLE supplier_payments (
    number VARCHAR(50) NOT NULL, 
    partner_id UUID NOT NULL, 
    payment_date DATE NOT NULL, 
    amount NUMERIC(18, 4) NOT NULL, 
    currency_id UUID, 
    journal_id UUID NOT NULL, 
    bank_account_id UUID NOT NULL, 
    reference VARCHAR(100), 
    state VARCHAR(20) DEFAULT 'posted' NOT NULL, 
    journal_entry_id UUID, 
    posted_at TIMESTAMP WITH TIME ZONE, 
    posted_by_id UUID, 
    notes TEXT, 
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    deleted_by_id UUID, 
    created_by_id UUID, 
    updated_by_id UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_supplier_payment_positive_amount CHECK (amount > 0), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    FOREIGN KEY(partner_id) REFERENCES partners (id) ON DELETE RESTRICT, 
    FOREIGN KEY(journal_id) REFERENCES journals (id) ON DELETE RESTRICT, 
    FOREIGN KEY(bank_account_id) REFERENCES accounts (id) ON DELETE RESTRICT, 
    FOREIGN KEY(journal_entry_id) REFERENCES journal_entries (id) ON DELETE SET NULL, 
    CONSTRAINT uq_supplier_payment_number UNIQUE (tenant_id, number)
);

CREATE INDEX ix_supplier_payments_partner ON supplier_payments (tenant_id, partner_id);

CREATE INDEX ix_supplier_payments_date ON supplier_payments (tenant_id, payment_date);

CREATE INDEX ix_supplier_payments_state ON supplier_payments (tenant_id, state);

CREATE INDEX ix_supplier_payments_tenant_id ON supplier_payments (tenant_id);

CREATE INDEX ix_supplier_payments_is_deleted ON supplier_payments (is_deleted);

CREATE TABLE supplier_payment_allocations (
    payment_id UUID NOT NULL, 
    invoice_id UUID NOT NULL, 
    amount NUMERIC(18, 4) NOT NULL, 
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    deleted_by_id UUID, 
    created_by_id UUID, 
    updated_by_id UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_supplier_payment_allocation_positive_amount CHECK (amount > 0), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    FOREIGN KEY(payment_id) REFERENCES supplier_payments (id) ON DELETE RESTRICT, 
    FOREIGN KEY(invoice_id) REFERENCES purchase_invoices (id) ON DELETE RESTRICT, 
    CONSTRAINT uq_supplier_payment_invoice_allocation UNIQUE (tenant_id, payment_id, invoice_id)
);

CREATE INDEX ix_supplier_payment_alloc_payment ON supplier_payment_allocations (tenant_id, payment_id);

CREATE INDEX ix_supplier_payment_alloc_invoice ON supplier_payment_allocations (tenant_id, invoice_id);

CREATE INDEX ix_supplier_payment_allocations_tenant_id ON supplier_payment_allocations (tenant_id);

CREATE INDEX ix_supplier_payment_allocations_is_deleted ON supplier_payment_allocations (is_deleted);

UPDATE alembic_version SET version_num='add_supplier_payments_stage18' WHERE alembic_version.version_num = 'add_journal_source_idempotency';

-- Running upgrade add_supplier_payments_stage18 -> add_supplier_payment_reversal_stage19

ALTER TABLE supplier_payments ADD COLUMN reversal_journal_entry_id UUID;

ALTER TABLE supplier_payments ADD CONSTRAINT fk_supplier_payments_reversal_journal_entry FOREIGN KEY(reversal_journal_entry_id) REFERENCES journal_entries (id) ON DELETE SET NULL;

CREATE INDEX ix_supplier_payments_reversal_journal_entry_id ON supplier_payments (reversal_journal_entry_id);

UPDATE alembic_version SET version_num='add_supplier_payment_reversal_stage19' WHERE alembic_version.version_num = 'add_supplier_payments_stage18';

-- Running upgrade add_supplier_payment_reversal_stage19 -> add_bank_reconciliation_stage20

CREATE TYPE bankstatementstate AS ENUM ('draft', 'in_progress', 'reconciled', 'cancelled');

CREATE TABLE bank_statements (
    account_id UUID NOT NULL, 
    statement_number VARCHAR(100) NOT NULL, 
    start_date DATE NOT NULL, 
    end_date DATE NOT NULL, 
    opening_balance NUMERIC(18, 4) NOT NULL, 
    closing_balance NUMERIC(18, 4) NOT NULL, 
    total_debits NUMERIC(18, 4) DEFAULT '0' NOT NULL, 
    total_credits NUMERIC(18, 4) DEFAULT '0' NOT NULL, 
    currency_code VARCHAR(3), 
    state bankstatementstate DEFAULT 'draft' NOT NULL, 
    notes TEXT, 
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    deleted_at TIMESTAMP WITHOUT TIME ZONE, 
    deleted_by_id UUID, 
    created_by_id UUID, 
    updated_by_id UUID, 
    tenant_id UUID NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(account_id) REFERENCES accounts (id) ON DELETE RESTRICT, 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    CONSTRAINT uq_bank_statement_tenant_account_number UNIQUE (tenant_id, account_id, statement_number), 
    CONSTRAINT ck_bank_statement_date_range CHECK (end_date >= start_date)
);

CREATE INDEX ix_bank_statements_tenant_account_period ON bank_statements (tenant_id, account_id, start_date, end_date);

CREATE TABLE bank_statement_lines (
    statement_id UUID NOT NULL, 
    line_number INTEGER NOT NULL, 
    transaction_date DATE NOT NULL, 
    value_date DATE, 
    description VARCHAR(500) NOT NULL, 
    external_reference VARCHAR(150), 
    debit NUMERIC(18, 4) DEFAULT '0' NOT NULL, 
    credit NUMERIC(18, 4) DEFAULT '0' NOT NULL, 
    matched_journal_item_id UUID, 
    matched_at TIMESTAMP WITH TIME ZONE, 
    matched_by_id UUID, 
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    deleted_at TIMESTAMP WITHOUT TIME ZONE, 
    deleted_by_id UUID, 
    created_by_id UUID, 
    updated_by_id UUID, 
    tenant_id UUID NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(statement_id) REFERENCES bank_statements (id) ON DELETE CASCADE, 
    FOREIGN KEY(matched_journal_item_id) REFERENCES journal_items (id) ON DELETE RESTRICT, 
    FOREIGN KEY(matched_by_id) REFERENCES users (id) ON DELETE SET NULL, 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    CONSTRAINT uq_bank_statement_line_number UNIQUE (tenant_id, statement_id, line_number), 
    CONSTRAINT uq_bank_statement_matched_journal_item UNIQUE (tenant_id, matched_journal_item_id), 
    CONSTRAINT ck_bank_statement_line_nonnegative CHECK (debit >= 0 AND credit >= 0), 
    CONSTRAINT ck_bank_statement_line_one_side CHECK (NOT (debit > 0 AND credit > 0)), 
    CONSTRAINT ck_bank_statement_line_positive CHECK (debit > 0 OR credit > 0)
);

CREATE INDEX ix_bank_statement_lines_tenant_statement ON bank_statement_lines (tenant_id, statement_id);

CREATE UNIQUE INDEX uq_bank_statement_external_reference ON bank_statement_lines (tenant_id, statement_id, external_reference) WHERE external_reference IS NOT NULL AND is_deleted = false;

UPDATE alembic_version SET version_num='add_bank_reconciliation_stage20' WHERE alembic_version.version_num = 'add_supplier_payment_reversal_stage19';
