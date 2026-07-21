# VoxFlow Database Schema & DDL Specification

This document provides the complete PostgreSQL database schema definition for VoxFlow. It features multi-tenant isolation via `tenant_id` foreign key columns and Supabase Row-Level Security (RLS) policies.

---

## 1. Tenant & Core Tables

```sql
-- 1. Tenants Table
CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    logo_url VARCHAR(512),
    active INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Suppliers Table
CREATE TABLE IF NOT EXISTS suppliers (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(32) NOT NULL,
    city VARCHAR(128) NOT NULL,
    state VARCHAR(128) NOT NULL,
    pincode VARCHAR(16) NOT NULL,
    contact_person VARCHAR(255) DEFAULT '',
    gstin VARCHAR(32) DEFAULT '',
    active INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_suppliers_tenant_phone ON suppliers(tenant_id, phone);

-- 3. Products Table
CREATE TABLE IF NOT EXISTS products (
    sku VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(128) NOT NULL,
    pack_size VARCHAR(64) NOT NULL,
    mrp_inr FLOAT NOT NULL
);
CREATE INDEX idx_products_tenant_sku ON products(tenant_id, sku);

-- 4. Stock Table
CREATE TABLE IF NOT EXISTS stock (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sku VARCHAR(64) NOT NULL REFERENCES products(sku) ON DELETE CASCADE,
    warehouse VARCHAR(128) NOT NULL,
    quantity INT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_stock_tenant_warehouse ON stock(tenant_id, warehouse);

-- 5. Orders Table
CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    supplier_id VARCHAR(64) NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    status VARCHAR(32) DEFAULT 'pending', -- pending | confirmed | shipped | delivered | cancelled
    items_json TEXT NOT NULL,             -- JSON array of {sku, quantity}
    total_qty INT DEFAULT 0,
    notes TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_orders_tenant_supplier ON orders(tenant_id, supplier_id);

-- 6. Shipments Table
CREATE TABLE IF NOT EXISTS shipments (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    order_id VARCHAR(64) NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    status VARCHAR(32) DEFAULT 'booked',  -- booked | in_transit | out_for_delivery | delivered | delayed
    carrier VARCHAR(128) DEFAULT '',
    tracking_no VARCHAR(128) DEFAULT '',
    expected_delivery TIMESTAMPTZ,
    last_update TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    history_json TEXT DEFAULT '[]'
);
CREATE INDEX idx_shipments_tenant_order ON shipments(tenant_id, order_id);

-- 7. Call Logs Table
CREATE TABLE IF NOT EXISTS calls (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) REFERENCES tenants(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMPTZ,
    duration_sec INT DEFAULT 0,
    supplier_id VARCHAR(64) REFERENCES suppliers(id),
    caller_phone VARCHAR(32) DEFAULT '',
    caller_name VARCHAR(255) DEFAULT '',
    language VARCHAR(8) DEFAULT 'hi',
    intent VARCHAR(64) DEFAULT '',
    outcome VARCHAR(64) DEFAULT '',
    escalated INT DEFAULT 0,
    transcript_json TEXT DEFAULT '[]',
    actions_json TEXT DEFAULT '[]'
);
CREATE INDEX idx_calls_tenant_started ON calls(tenant_id, started_at);

-- 8. Appointments Table
CREATE TABLE IF NOT EXISTS appointments (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    supplier_id VARCHAR(64) REFERENCES suppliers(id) ON DELETE CASCADE,
    datetime TIMESTAMPTZ NOT NULL,
    purpose TEXT DEFAULT '',
    status VARCHAR(32) DEFAULT 'pending', -- pending | confirmed | cancelled
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 9. Worksheet Logs Table
CREATE TABLE IF NOT EXISTS worksheet_logs (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    worksheet_name VARCHAR(128) NOT NULL,
    action_type VARCHAR(32) NOT NULL,    -- append | update | delete
    row_data_json TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 10. Communication Logs Table
CREATE TABLE IF NOT EXISTS communication_logs (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    channel VARCHAR(32) NOT NULL,         -- email | whatsapp
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(255),
    body TEXT NOT NULL,
    status VARCHAR(32) DEFAULT 'sent',     -- sent | failed
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

---

## 2. Row-Level Security (RLS) Policy Blueprint

For Supabase deployments, enable RLS on every tenant-scoped table:

```sql
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE worksheet_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE communication_logs ENABLE ROW LEVEL SECURITY;

-- Tenant Isolation RLS Policy Example:
CREATE POLICY tenant_isolation_policy ON suppliers
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant', true));
```
