"""Regression coverage for the legacy SQLite ``products`` composite-key upgrade path.

Pre-Day-45 local SQLite databases created ``products`` with ``PRIMARY KEY (sku)``.
SQLite cannot alter primary keys in place, so ``_ensure_product_composite_key_sqlite``
rebuilds the table in place with composite ``PRIMARY KEY (sku, tenant_id)``. This must
preserve existing rows, preserve the tenant foreign key, and allow multi-tenant
duplicate SKUs.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text


@pytest.fixture
def legacy_products_db(tmp_path: Path) -> str:
    """Build a pre-Day-45 `products` table with single-column `PRIMARY KEY (sku)`."""
    db_path = tmp_path / "legacy_products.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE tenants (
            id VARCHAR(64) NOT NULL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE products (
            sku VARCHAR(64) NOT NULL PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(128) NOT NULL,
            pack_size VARCHAR(64) NOT NULL,
            mrp_inr FLOAT NOT NULL,
            FOREIGN KEY(tenant_id) REFERENCES tenants (id)
        )
        """
    )
    conn.execute("INSERT INTO tenants (id, name) VALUES ('varun', 'Varun Beverages')")
    conn.execute("INSERT INTO tenants (id, name) VALUES ('tenant2', 'Second Tenant')")
    conn.execute(
        """
        INSERT INTO products (sku, tenant_id, name, category, pack_size, mrp_inr)
        VALUES ('SKU-001', 'varun', 'Mango Slice 250ml', 'Beverages', '250ml', 40.0)
        """
    )
    conn.commit()
    conn.close()
    return f"sqlite:///{db_path}"


def test_legacy_products_upgrades_to_composite_primary_key(legacy_products_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from voxflow_api import db

    engine = create_engine(legacy_products_db)
    monkeypatch.setattr(db, "_engine", engine)

    # Before upgrade: products only has 1 PK column (sku)
    with engine.begin() as conn:
        cols_before = conn.execute(text("PRAGMA table_info(products)")).mappings().all()
        pk_cols_before = [c["name"] for c in cols_before if c["pk"] > 0]
        assert pk_cols_before == ["sku"]

    # Run upgrade helper
    db._ensure_product_composite_key_sqlite()

    # After upgrade: products has composite PK (sku, tenant_id)
    with engine.begin() as conn:
        cols_after = conn.execute(text("PRAGMA table_info(products)")).mappings().all()
        pk_cols_after = {c["name"] for c in cols_after if c["pk"] > 0}
        assert pk_cols_after == {"sku", "tenant_id"}

        # Existing row preserved
        row = conn.execute(text("SELECT sku, tenant_id, name, mrp_inr FROM products WHERE sku = 'SKU-001'")).mappings().first()
        assert row is not None
        assert row["tenant_id"] == "varun"
        assert row["name"] == "Mango Slice 250ml"
        assert row["mrp_inr"] == 40.0

        # Can now insert duplicate SKU for another tenant without collision
        conn.execute(
            text(
                "INSERT INTO products (sku, tenant_id, name, category, pack_size, mrp_inr) "
                "VALUES ('SKU-001', 'tenant2', 'Mango Drink 200ml', 'Beverages', '200ml', 35.0)"
            )
        )
        count = conn.execute(text("SELECT count(*) FROM products WHERE sku = 'SKU-001'")).scalar()
        assert count == 2


def test_product_composite_key_upgrade_preserves_fk_constraint(legacy_products_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from voxflow_api import db

    engine = create_engine(legacy_products_db)
    monkeypatch.setattr(db, "_engine", engine)

    db._ensure_product_composite_key_sqlite()

    with engine.begin() as conn:
        fks = conn.execute(text("PRAGMA foreign_key_list(products)")).mappings().all()
        assert len(fks) >= 1
        fk = next((f for f in fks if f["table"] == "tenants"), None)
        assert fk is not None, "products lost its foreign key to tenants during upgrade"
        assert fk["from"] == "tenant_id"
        assert fk["to"] == "id"


def test_product_composite_key_upgrade_idempotent(legacy_products_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from voxflow_api import db

    engine = create_engine(legacy_products_db)
    monkeypatch.setattr(db, "_engine", engine)

    # First run upgrades
    db._ensure_product_composite_key_sqlite()
    # Second run is a clean no-op
    db._ensure_product_composite_key_sqlite()

    with engine.begin() as conn:
        cols = conn.execute(text("PRAGMA table_info(products)")).mappings().all()
        pk_cols = {c["name"] for c in cols if c["pk"] > 0}
        assert pk_cols == {"sku", "tenant_id"}
