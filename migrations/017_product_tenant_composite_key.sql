-- 017_product_tenant_composite_key.sql
-- Day 45/46: Tenant-scoped product catalog and unconstrained warehouse stock SKUs.
--
-- Transition products table from a global single-column primary key (sku)
-- to a tenant-scoped composite primary key (sku, tenant_id), allowing different
-- tenants to maintain their own independent product catalogs with identical SKU names.
-- Also relaxes the foreign key constraint on stock.sku so stock entries are
-- tenant-isolated without requiring a global products.sku unique constraint.

-- 1. Drop foreign key constraint on stock.sku referencing products.sku if present.
ALTER TABLE stock DROP CONSTRAINT IF EXISTS stock_sku_fkey;

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'stock'::regclass
          AND contype = 'f'
          AND confrelid = 'products'::regclass
    ) LOOP
        EXECUTE 'ALTER TABLE stock DROP CONSTRAINT ' || quote_ident(r.conname);
    END LOOP;
END $$;

-- 2. Upgrade products primary key to composite (sku, tenant_id) if it is currently single-column.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'products'::regclass
          AND contype = 'p'
          AND conname = 'products_pkey'
    ) THEN
        -- If primary key currently consists of only 1 column (sku), upgrade to composite (sku, tenant_id)
        IF (
            SELECT count(*)
            FROM pg_constraint c
            JOIN unnest(c.conkey) AS k ON true
            WHERE c.conrelid = 'products'::regclass AND c.contype = 'p'
        ) = 1 THEN
            ALTER TABLE products DROP CONSTRAINT products_pkey;
            ALTER TABLE products ADD PRIMARY KEY (sku, tenant_id);
        END IF;
    ELSIF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'products'::regclass
          AND contype = 'p'
    ) THEN
        ALTER TABLE products ADD PRIMARY KEY (sku, tenant_id);
    END IF;
END $$;

-- 3. Ensure indexes on stock and products are present.
CREATE INDEX IF NOT EXISTS ix_stock_sku ON stock (sku);
CREATE INDEX IF NOT EXISTS ix_stock_tenant_id ON stock (tenant_id);

COMMENT ON TABLE products IS
  'Tenant-scoped product catalog identified by composite primary key (sku, tenant_id)';
