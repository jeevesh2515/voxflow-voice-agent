"""Regression coverage for the legacy SQLite ``suppliers.auth_pin`` upgrade path.

Pre-Day-46 local SQLite databases created ``auth_pin`` as ``NOT NULL``. SQLite
cannot drop a NOT NULL constraint with a simple ALTER, so `_ensure_supplier_
auth_pin_nullable_sqlite` rebuilds the table in place. This must preserve
every row's data, keep the tenant foreign key, and recreate every index —
none of that was covered by any existing test.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text


@pytest.fixture
def legacy_sqlite_db(tmp_path: Path) -> str:
    """Build a pre-Day-46 `suppliers` table with `auth_pin NOT NULL` and a
    tenant foreign key, matching the historical schema shape exactly."""
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE tenants (
            id VARCHAR(64) NOT NULL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            agent_name VARCHAR(64) NOT NULL DEFAULT 'Vaani',
            default_language VARCHAR(8) NOT NULL DEFAULT 'en',
            plan VARCHAR(32) NOT NULL DEFAULT 'pro',
            total_minutes_used FLOAT NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE suppliers (
            id VARCHAR(64) NOT NULL PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            name VARCHAR(255) NOT NULL,
            phone VARCHAR(32) NOT NULL,
            city VARCHAR(128) NOT NULL,
            state VARCHAR(128) NOT NULL,
            pincode VARCHAR(16) NOT NULL,
            contact_person VARCHAR(255) NOT NULL DEFAULT '',
            gstin VARCHAR(32) NOT NULL DEFAULT '',
            auth_pin VARCHAR(16) NOT NULL DEFAULT '0000',
            auth_pin_hash VARCHAR(255),
            pin_updated_at DATETIME,
            pin_failed_attempts INTEGER NOT NULL DEFAULT 0,
            pin_locked_until DATETIME,
            contact_type VARCHAR(16) NOT NULL DEFAULT 'customer',
            active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(tenant_id) REFERENCES tenants (id)
        )
        """
    )
    conn.execute("CREATE INDEX ix_suppliers_name ON suppliers (name)")
    conn.execute("CREATE INDEX ix_suppliers_phone ON suppliers (phone)")
    conn.execute("CREATE INDEX ix_suppliers_tenant_id ON suppliers (tenant_id)")
    conn.execute("CREATE INDEX ix_suppliers_contact_type ON suppliers (contact_type)")
    conn.execute("INSERT INTO tenants (id, name) VALUES ('legacy-tenant', 'Legacy Co')")
    conn.execute(
        """
        INSERT INTO suppliers
            (id, tenant_id, name, phone, city, state, pincode, contact_person, gstin, auth_pin)
        VALUES
            ('sup-legacy-1', 'legacy-tenant', 'Legacy Supplier', '+919000000099',
             'Pune', 'MH', '411001', 'Old Contact', 'GST123', '1234')
        """
    )
    conn.commit()
    conn.close()
    return str(db_path)


def test_legacy_upgrade_preserves_data_fk_and_indexes(legacy_sqlite_db: str) -> None:
    from voxflow_api import db as db_module

    engine = create_engine(f"sqlite:///{legacy_sqlite_db}", future=True)
    original_engine = db_module._engine
    db_module._engine = engine
    try:
        db_module._ensure_supplier_auth_pin_nullable_sqlite()

        with engine.connect() as conn:
            columns = conn.execute(text("PRAGMA table_info(suppliers)")).mappings().all()
            column_by_name = {c["name"]: c for c in columns}
            assert column_by_name["auth_pin"]["notnull"] == 0, "auth_pin must now be nullable"

            row = conn.execute(
                text(
                    "SELECT tenant_id, name, phone, auth_pin, auth_pin_hash, "
                    "pin_failed_attempts, pin_locked_until "
                    "FROM suppliers WHERE id = 'sup-legacy-1'"
                )
            ).mappings().first()
            assert row is not None, "the pre-existing row must survive the rebuild"
            assert row["tenant_id"] == "legacy-tenant"
            assert row["name"] == "Legacy Supplier"
            assert row["phone"] == "+919000000099"
            assert row["auth_pin"] == "1234"
            assert row["auth_pin_hash"] is None
            assert row["pin_failed_attempts"] == 0
            assert row["pin_locked_until"] is None

            fk_rows = conn.execute(text("PRAGMA foreign_key_list(suppliers)")).mappings().all()
            tenant_fks = [fk for fk in fk_rows if fk["table"] == "tenants" and fk["from"] == "tenant_id"]
            assert tenant_fks, "the tenant_id -> tenants(id) foreign key must survive the rebuild"

            index_names = {
                row_["name"]
                for row_ in conn.execute(text("PRAGMA index_list(suppliers)")).mappings().all()
            }
            for expected in (
                "ix_suppliers_name",
                "ix_suppliers_phone",
                "ix_suppliers_tenant_id",
                "ix_suppliers_contact_type",
            ):
                assert expected in index_names, f"{expected} must be recreated after the rebuild"

            # A new insert that intentionally omits a plaintext PIN must now
            # succeed against the rebuilt table.
            conn.execute(
                text(
                    "INSERT INTO suppliers "
                    "(id, tenant_id, name, phone, city, state, pincode, auth_pin, auth_pin_hash, created_at) "
                    "VALUES ('sup-legacy-2', 'legacy-tenant', 'New Supplier', '+919000000098', "
                    "'Pune', 'MH', '411001', NULL, NULL, CURRENT_TIMESTAMP)"
                )
            )
            conn.commit()
    finally:
        db_module._engine = original_engine
        engine.dispose()


def test_legacy_upgrade_is_idempotent_and_a_no_op_on_a_fresh_schema(legacy_sqlite_db: str) -> None:
    """Running the upgrade twice, and running it against an already-nullable
    table, must not error or duplicate any rebuild."""
    from voxflow_api import db as db_module

    engine = create_engine(f"sqlite:///{legacy_sqlite_db}", future=True)
    original_engine = db_module._engine
    db_module._engine = engine
    try:
        db_module._ensure_supplier_auth_pin_nullable_sqlite()
        # Second call: auth_pin is already nullable, so this must be a no-op.
        db_module._ensure_supplier_auth_pin_nullable_sqlite()

        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM suppliers")).scalar_one()
            assert count == 1, "the idempotent second call must not duplicate rows"
    finally:
        db_module._engine = original_engine
        engine.dispose()


def test_legacy_upgrade_returns_immediately_when_table_is_absent(tmp_path: Path) -> None:
    """A brand-new database has no `suppliers` table yet; `create_all()` will
    define it correctly, so this function must not error."""
    from voxflow_api import db as db_module

    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}", future=True)
    original_engine = db_module._engine
    db_module._engine = engine
    try:
        db_module._ensure_supplier_auth_pin_nullable_sqlite()
    finally:
        db_module._engine = original_engine
        engine.dispose()
