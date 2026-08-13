"""Emit the complete Postgres DDL for the ORM models.

    python -m voxflow_api.gen_schema > ../../migrations/000_base_schema.sql

Why generate rather than hand-write
-----------------------------------
The DDL previously existed only as fenced code blocks inside schema.md, to be
copied out by hand in two pieces in a specific order. Hand-copied DDL drifts
from the ORM the moment either side changes, and the drift stays invisible
until a query fails against a live database — which, for this project, means
during a phone call.

Generating from `Base.metadata` makes disagreement impossible by construction.
`tests/test_schema_sql.py` asserts the checked-in file still matches, so drift
fails CI instead of production.
"""

from __future__ import annotations

import sys

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

TABLES = [
    "tenants", "suppliers", "products", "stock", "orders", "shipments",
    "calls", "appointments", "worksheet_logs", "communication_logs",
    "tenant_phone_numbers",
]


RLS_SUFFIX = """

-- ---------------------------------------------------------------------
-- 2. Row-Level Security
-- ---------------------------------------------------------------------
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE worksheet_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE communication_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_phone_numbers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_policy ON suppliers;
CREATE POLICY tenant_isolation_policy ON suppliers
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON products;
CREATE POLICY tenant_isolation_policy ON products
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON stock;
CREATE POLICY tenant_isolation_policy ON stock
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON orders;
CREATE POLICY tenant_isolation_policy ON orders
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON shipments;
CREATE POLICY tenant_isolation_policy ON shipments
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON calls;
CREATE POLICY tenant_isolation_policy ON calls
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON appointments;
CREATE POLICY tenant_isolation_policy ON appointments
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON worksheet_logs;
CREATE POLICY tenant_isolation_policy ON worksheet_logs
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON communication_logs;
CREATE POLICY tenant_isolation_policy ON communication_logs
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON tenant_phone_numbers;
CREATE POLICY tenant_isolation_policy ON tenant_phone_numbers
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
"""


def table_ddl() -> str:
    """CREATE TABLE + CREATE INDEX for every model, in dependency order."""
    from .db import Base

    pg = postgresql.dialect()
    out: list[str] = []
    for t in Base.metadata.sorted_tables:
        out.append(str(CreateTable(t, if_not_exists=True).compile(dialect=pg)).strip() + ";")
        for ix in sorted(t.indexes, key=lambda i: i.name or ""):
            out.append(str(CreateIndex(ix, if_not_exists=True).compile(dialect=pg)).strip() + ";")
    return "\n\n".join(out) + RLS_SUFFIX


def main() -> None:
    sys.stdout.write(table_ddl() + "\n")


if __name__ == "__main__":
    main()
