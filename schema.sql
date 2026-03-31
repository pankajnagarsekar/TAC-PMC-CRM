-- TAC-PMC-CRM Project Database Schema (Relational Representation)
-- Authoritative Schema for Version 3.0 (MongoDB Edition Logical Map)
-- Generated: 2026-03-31

-- ──────────────────────────────────────────────────────────────────────────
-- 1. IDENTITY & AUTHENTICATION
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE organisations (
    id VARCHAR(24) PRIMARY KEY, -- MongoDB ObjectId
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id VARCHAR(24) PRIMARY KEY,
    organisation_id VARCHAR(24) REFERENCES organisations(id),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'Other', -- 'Admin' | 'Supervisor' | 'Other'
    active_status BOOLEAN DEFAULT TRUE,
    dpr_generation_permission BOOLEAN DEFAULT FALSE,
    assigned_projects JSONB, -- List of project_ids
    screen_permissions JSONB, -- List of permission keys
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organisation_id, email)
);

CREATE TABLE user_project_map (
    id VARCHAR(24) PRIMARY KEY,
    user_id VARCHAR(24) REFERENCES users(id),
    project_id VARCHAR(24),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE refresh_tokens (
    id VARCHAR(24) PRIMARY KEY,
    jti VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(24) REFERENCES users(id),
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ──────────────────────────────────────────────────────────────────────────
-- 2. MASTER / CONFIGURATION
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE clients (
    id VARCHAR(24) PRIMARY KEY,
    organisation_id VARCHAR(24) REFERENCES organisations(id),
    name VARCHAR(255) NOT NULL,
    address TEXT,
    phone VARCHAR(50),
    email VARCHAR(255),
    gstin VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE projects (
    id VARCHAR(24) PRIMARY KEY,
    organisation_id VARCHAR(24) REFERENCES organisations(id),
    project_name VARCHAR(255) NOT NULL,
    client_id VARCHAR(24) REFERENCES clients(id),
    project_code VARCHAR(50), -- Unique per org
    status VARCHAR(50) DEFAULT 'active', -- 'active' | 'inactive' | 'completed'
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    project_retention_percentage NUMERIC(5, 2) DEFAULT 0.0,
    project_cgst_percentage NUMERIC(5, 2) DEFAULT 9.0,
    project_sgst_percentage NUMERIC(5, 2) DEFAULT 9.0,
    completion_percentage NUMERIC(5, 2) DEFAULT 0.0,
    master_original_budget NUMERIC(20, 2) DEFAULT 0.0,
    master_remaining_budget NUMERIC(20, 2) DEFAULT 0.0,
    threshold_petty NUMERIC(20, 2) DEFAULT 0.0,
    threshold_ovh NUMERIC(20, 2) DEFAULT 0.0,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organisation_id, project_code)
);

CREATE TABLE code_master (
    id VARCHAR(24) PRIMARY KEY,
    organisation_id VARCHAR(24) REFERENCES organisations(id),
    category_name VARCHAR(255),
    code VARCHAR(50),
    code_short VARCHAR(50),
    code_description TEXT,
    budget_type VARCHAR(50), -- 'commitment' | 'fund_transfer'
    active_status BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vendors (
    id VARCHAR(24) PRIMARY KEY,
    organisation_id VARCHAR(24) REFERENCES organisations(id),
    name VARCHAR(255) NOT NULL,
    gstin VARCHAR(50),
    contact_person VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(255),
    address TEXT,
    active_status BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ──────────────────────────────────────────────────────────────────────────
-- 3. FINANCIAL TABLES
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE project_category_budgets (
    id VARCHAR(24) PRIMARY KEY,
    project_id VARCHAR(24) REFERENCES projects(id),
    category_id VARCHAR(24) REFERENCES code_master(id),
    original_budget NUMERIC(20, 2) NOT NULL,
    committed_amount NUMERIC(20, 2) DEFAULT 0.0,
    remaining_budget NUMERIC(20, 2) DEFAULT 0.0,
    description TEXT,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, category_id)
);

CREATE TABLE work_orders (
    id VARCHAR(24) PRIMARY KEY,
    organisation_id VARCHAR(24) REFERENCES organisations(id),
    project_id VARCHAR(24) REFERENCES projects(id),
    category_id VARCHAR(24) REFERENCES code_master(id),
    vendor_id VARCHAR(24) REFERENCES vendors(id),
    wo_ref VARCHAR(100) UNIQUE NOT NULL,
    subtotal NUMERIC(20, 2) DEFAULT 0.0,
    discount NUMERIC(20, 2) DEFAULT 0.0,
    total_before_tax NUMERIC(20, 2) DEFAULT 0.0,
    cgst NUMERIC(20, 2) DEFAULT 0.0,
    sgst NUMERIC(20, 2) DEFAULT 0.0,
    grand_total NUMERIC(20, 2) DEFAULT 0.0,
    retention_percent NUMERIC(5, 2) DEFAULT 0.0,
    retention_amount NUMERIC(20, 2) DEFAULT 0.0,
    total_payable NUMERIC(20, 2) DEFAULT 0.0,
    actual_payable NUMERIC(20, 2) DEFAULT 0.0,
    status VARCHAR(50), -- 'Draft' | 'Pending' | 'Completed' | 'Closed' | 'Cancelled'
    line_items JSONB, -- Array of items
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE payment_certificates (
    id VARCHAR(24) PRIMARY KEY,
    organisation_id VARCHAR(24) REFERENCES organisations(id),
    project_id VARCHAR(24) REFERENCES projects(id),
    work_order_id VARCHAR(24) REFERENCES work_orders(id),
    category_id VARCHAR(24) REFERENCES code_master(id),
    vendor_id VARCHAR(24) REFERENCES vendors(id),
    pc_ref VARCHAR(100) NOT NULL,
    subtotal NUMERIC(20, 2) DEFAULT 0.0,
    retention_percent NUMERIC(5, 2) DEFAULT 0.0,
    retention_amount NUMERIC(20, 2) DEFAULT 0.0,
    total_payable NUMERIC(20, 2) DEFAULT 0.0,
    cgst NUMERIC(20, 2) DEFAULT 0.0,
    sgst NUMERIC(20, 2) DEFAULT 0.0,
    grand_total NUMERIC(20, 2) DEFAULT 0.0,
    gst_amount NUMERIC(20, 2) DEFAULT 0.0,
    fund_request BOOLEAN DEFAULT FALSE,
    status VARCHAR(50),
    line_items JSONB,
    idempotency_key VARCHAR(255) UNIQUE,
    version INTEGER DEFAULT 1,
    vendor_name VARCHAR(255),
    invoice_number VARCHAR(100),
    date_str VARCHAR(50),
    amount NUMERIC(20, 2),
    total_amount NUMERIC(20, 2),
    ocr_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE financial_state (
    id VARCHAR(24) PRIMARY KEY,
    project_id VARCHAR(24) REFERENCES projects(id),
    code_id VARCHAR(24) REFERENCES code_master(id),
    original_budget NUMERIC(20, 2) DEFAULT 0.0,
    committed_value NUMERIC(20, 2) DEFAULT 0.0,
    certified_value NUMERIC(20, 2) DEFAULT 0.0,
    balance_budget_remaining NUMERIC(20, 2) DEFAULT 0.0,
    over_commit_flag BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMPTZ,
    version INTEGER DEFAULT 1,
    UNIQUE(project_id, code_id)
);

-- ──────────────────────────────────────────────────────────────────────────
-- 4. LIQUIDITY & LEDGER
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE fund_allocations (
    id VARCHAR(24) PRIMARY KEY,
    project_id VARCHAR(24) REFERENCES projects(id),
    category_id VARCHAR(24) REFERENCES code_master(id),
    allocation_original NUMERIC(20, 2) NOT NULL,
    allocation_received NUMERIC(20, 2) DEFAULT 0.0,
    allocation_remaining NUMERIC(20, 2) DEFAULT 0.0,
    cash_in_hand NUMERIC(20, 2) DEFAULT 0.0,
    total_expenses NUMERIC(20, 2) DEFAULT 0.0,
    last_pc_closed_date TIMESTAMPTZ,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, category_id)
);

CREATE TABLE cash_transactions (
    id VARCHAR(24) PRIMARY KEY,
    project_id VARCHAR(24) REFERENCES projects(id),
    category_id VARCHAR(24) REFERENCES code_master(id),
    amount NUMERIC(20, 2) NOT NULL,
    type VARCHAR(20) NOT NULL, -- 'DEBIT' | 'CREDIT'
    purpose TEXT,
    bill_reference VARCHAR(255),
    image_url TEXT,
    created_by VARCHAR(24) REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vendor_ledger (
    id VARCHAR(24) PRIMARY KEY,
    vendor_id VARCHAR(24) REFERENCES vendors(id),
    project_id VARCHAR(24) REFERENCES projects(id),
    ref_id VARCHAR(24), -- Ref to WO or PC
    entry_type VARCHAR(50), -- 'PC_CERTIFIED' | 'PAYMENT_MADE' | 'RETENTION_HELD'
    amount NUMERIC(20, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ──────────────────────────────────────────────────────────────────────────
-- 5. SITE OPERATIONS
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE dprs (
    id VARCHAR(24) PRIMARY KEY,
    project_id VARCHAR(24) REFERENCES projects(id),
    created_by VARCHAR(24) REFERENCES users(id),
    date TIMESTAMPTZ NOT NULL,
    notes TEXT,
    photos JSONB, -- Array of photo URLs
    status VARCHAR(50), -- 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED'
    approved_by VARCHAR(24),
    approved_at TIMESTAMPTZ,
    rejected_by VARCHAR(24),
    rejected_at TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE attendance (
    id VARCHAR(24) PRIMARY KEY,
    organisation_id VARCHAR(24) REFERENCES organisations(id),
    project_id VARCHAR(24) REFERENCES projects(id),
    supervisor_id VARCHAR(24) REFERENCES users(id),
    date TIMESTAMPTZ NOT NULL,
    selfie_url TEXT,
    gps_lat FLOAT,
    gps_lng FLOAT,
    check_in_time TIMESTAMPTZ,
    verified_by_admin BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    verified_user_id VARCHAR(24)
);

CREATE TABLE workers_daily_logs (
    id VARCHAR(24) PRIMARY KEY,
    organisation_id VARCHAR(24) REFERENCES organisations(id),
    project_id VARCHAR(24) REFERENCES projects(id),
    date DATE NOT NULL,
    supervisor_id VARCHAR(24),
    supervisor_name VARCHAR(255),
    entries JSONB, -- Vendor supplied workers
    workers JSONB, -- Direct workers
    total_workers INTEGER,
    total_hours NUMERIC(10, 2),
    weather VARCHAR(100),
    site_conditions TEXT,
    remarks TEXT,
    status VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ──────────────────────────────────────────────────────────────────────────
-- 6. PROJECT SCHEDULER (PHASE 3)
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE project_schedules (
    id VARCHAR(24) PRIMARY KEY,
    project_id VARCHAR(24) REFERENCES projects(id),
    organisation_id VARCHAR(24) REFERENCES organisations(id),
    project_name VARCHAR(255),
    tasks JSONB, -- Deeply nested task hierarchy
    total_duration_days INTEGER,
    project_start_date DATE,
    critical_path JSONB, -- List of task_ids
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ──────────────────────────────────────────────────────────────────────────
-- 7. SYSTEM & AUDIT
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE audit_logs (
    id VARCHAR(24) PRIMARY KEY,
    organisation_id VARCHAR(24) REFERENCES organisations(id),
    module_name VARCHAR(100),
    entity_type VARCHAR(100),
    entity_id VARCHAR(24),
    action_type VARCHAR(50),
    user_id VARCHAR(24) REFERENCES users(id),
    project_id VARCHAR(24),
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE operation_logs (
    id VARCHAR(24) PRIMARY KEY,
    operation_key VARCHAR(255) UNIQUE NOT NULL,
    entity_type VARCHAR(100),
    response_payload JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sequences (
    _id VARCHAR(255) PRIMARY KEY, -- Custom string ID
    seq INTEGER NOT NULL
);
