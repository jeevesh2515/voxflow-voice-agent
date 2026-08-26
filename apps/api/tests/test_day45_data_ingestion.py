"""Day 45 — Company Data Ingestion (CSV Import + Validation + Upsert Semantics) Tests."""

from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient

from sqlalchemy import select

from voxflow_api.db import (
    Order,
    Product,
    Shipment,
    Stock,
    Supplier,
    Tenant,
    TenantMember,
    reset_db,
    session_scope,
)
from voxflow_api.main import create_app
from voxflow_api.services.data_ingestion import (
    ENTITY_SCHEMAS,
    get_csv_template,
    ingest_csv_data,
    validate_csv_data,
)


@pytest.fixture(autouse=True)
def _clean_database():
    reset_db()


def _setup_test_tenants():
    with session_scope() as db:
        for tid, name in [("day45_alpha", "Alpha Supplies Ltd"), ("day45_beta", "Beta Logistics Ltd")]:
            if not db.get(Tenant, tid):
                db.add(Tenant(id=tid, name=name, plan="pro", active=1))
            member = db.execute(
                select(TenantMember).where(TenantMember.tenant_id == tid, TenantMember.user_id == f"user-{tid}")
            ).scalars().first()
            if not member:
                db.add(TenantMember(
                    id=f"tm-{tid}",
                    tenant_id=tid,
                    user_id=f"user-{tid}",
                    subject_email_hash=f"hash-{tid}",
                    role="owner",
                    status="active",
                ))
        db.commit()




def test_entity_schemas_and_templates():
    """Verify all 5 core entity templates generate valid CSVs with required columns."""
    for entity in ("products", "stock", "suppliers", "orders", "shipments"):
        assert entity in ENTITY_SCHEMAS
        csv_text = get_csv_template(entity)
        assert len(csv_text.strip()) > 0
        lines = csv_text.strip().splitlines()
        assert len(lines) >= 2  # Header + at least 1 sample row
        headers = [h.strip().lower() for h in lines[0].split(",")]
        for req in ENTITY_SCHEMAS[entity]["required_columns"]:
            assert req in headers, f"Missing required column '{req}' in template for {entity}"


def test_get_templates_api():
    """Test GET /api/data/templates/{entity} endpoints and 404 on invalid entity."""
    app = create_app()
    client = TestClient(app)

    # 1. Valid template download
    resp = client.get("/api/data/templates/products")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=\"products_template.csv\"" in resp.headers["content-disposition"]
    assert "sku,name" in resp.text

    # 2. Invalid template entity
    resp_bad = client.get("/api/data/templates/nonexistent_entity")
    assert resp_bad.status_code == 404
    assert "Unsupported entity" in resp_bad.text


def test_get_entities_api():
    """Test GET /api/data/entities metadata endpoint."""
    app = create_app()
    client = TestClient(app)

    resp = client.get("/api/data/entities")
    assert resp.status_code == 200
    data = resp.json()
    assert "entities" in data
    entity_ids = [e["id"] for e in data["entities"]]
    assert "products" in entity_ids
    assert "stock" in entity_ids
    assert "suppliers" in entity_ids
    assert "orders" in entity_ids
    assert "shipments" in entity_ids


def test_csv_validation_engine():
    """Test CSV validation logic for valid, missing header, and malformed rows."""
    # 1. Valid Products CSV
    valid_csv = (
        "sku,name,category,pack_size,mrp_inr\n"
        "TEST-001,Premium Earl Grey Tea,Beverages,50 bags,4.50\n"
        "TEST-002,English Breakfast Tea,Beverages,100 bags,7.20\n"
    )
    res = validate_csv_data("products", valid_csv, "day45_alpha")
    assert res.is_valid is True
    assert res.total_rows == 2
    assert res.valid_rows == 2
    assert res.error_count == 0
    assert len(res.preview) == 2

    # 2. Missing Required Column
    missing_hdr = (
        "name,category,price\n"
        "Mystery Tea,Beverages,4.50\n"
    )
    res_hdr = validate_csv_data("products", missing_hdr, "day45_alpha")
    assert res_hdr.is_valid is False
    assert res_hdr.error_count > 0
    assert "Missing required columns: sku" in res_hdr.errors[0]["message"]

    # 3. Invalid Row Data (non-numeric price)
    bad_price = (
        "sku,name,category,pack_size,mrp_inr\n"
        "TEST-001,Valid Tea,Beverages,50 bags,4.50\n"
        "TEST-002,Bad Price Tea,Beverages,100 bags,NOT_A_PRICE\n"
    )
    res_bad = validate_csv_data("products", bad_price, "day45_alpha")
    assert res_bad.is_valid is False
    assert res_bad.error_count == 1
    assert res_bad.errors[0]["row_number"] == 3
    assert res_bad.errors[0]["column"] == "mrp_inr"

    # 4. Stock validation (negative quantity)
    bad_stock = (
        "sku,warehouse,quantity\n"
        "TEST-001,London Hub,-25\n"
    )
    res_stock = validate_csv_data("stock", bad_stock, "day45_alpha")
    assert res_stock.is_valid is False
    assert "Quantity cannot be negative" in res_stock.errors[0]["message"]


def test_validate_endpoint_api():
    """Test POST /api/data/{entity}/validate endpoint with JSON and multipart."""
    app = create_app()
    client = TestClient(app)

    # JSON payload
    resp = client.post(
        "/api/data/products/validate",
        json={
            "csv_text": "sku,name,category,pack_size,mrp_inr\nSKU-UK-01,London Dry Gin,Spirits,70cl,28.00\n",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["total_rows"] == 1
    assert data["preview"][0]["sku"] == "SKU-UK-01"

    # Multipart file upload
    file_content = b"sku,name\nSKU-UK-02,Tonic Water\n"
    files = {"file": ("products.csv", io.BytesIO(file_content), "text/csv")}
    resp_file = client.post("/api/data/products/validate", files=files)
    assert resp_file.status_code == 200
    assert resp_file.json()["is_valid"] is True


def test_product_and_stock_ingestion_with_upsert():
    """Test importing products and stock, and verifying idempotent upsert."""
    _setup_test_tenants()

    # Step 1: Initial Products Import
    prod_csv = (
        "sku,name,category,pack_size,mrp_inr\n"
        "DAY45-PROD-A,Scottish Shortbread,Bakery,200g,3.50\n"
        "DAY45-PROD-B,Highland Spring Water,Beverages,500ml,1.20\n"
    )

    with session_scope() as db:
        res = ingest_csv_data(db, "products", prod_csv, "day45_alpha")
        assert res.success is True
        assert res.inserted == 2
        assert res.updated == 0

    # Verify rows in DB
    with session_scope() as db:
        p1 = db.execute(
            select(Product).where(Product.tenant_id == "day45_alpha", Product.sku == "DAY45-PROD-A")
        ).scalars().first()
        assert p1 is not None
        assert p1.name == "Scottish Shortbread"
        assert p1.mrp_inr == 3.50

    # Step 2: Upsert Products (update price and name of A, add product C)
    prod_csv_v2 = (
        "sku,name,category,pack_size,mrp_inr\n"
        "DAY45-PROD-A,Scottish Butter Shortbread Gold,Bakery,200g,4.00\n"
        "DAY45-PROD-C,Yorkshire Tea Box,Beverages,80 bags,3.80\n"
    )
    with session_scope() as db:
        res2 = ingest_csv_data(db, "products", prod_csv_v2, "day45_alpha")
        assert res2.success is True
        assert res2.inserted == 1  # PROD-C
        assert res2.updated == 1   # PROD-A updated

    with session_scope() as db:
        p1_updated = db.execute(
            select(Product).where(Product.tenant_id == "day45_alpha", Product.sku == "DAY45-PROD-A")
        ).scalars().first()
        assert p1_updated.name == "Scottish Butter Shortbread Gold"
        assert p1_updated.mrp_inr == 4.00

    # Step 3: Stock Import
    stock_csv = (
        "sku,warehouse,quantity\n"
        "DAY45-PROD-A,London Central Depot,300\n"
        "DAY45-PROD-B,Manchester Depot,150\n"
    )
    with session_scope() as db:
        res_stock = ingest_csv_data(db, "stock", stock_csv, "day45_alpha")
        assert res_stock.success is True
        assert res_stock.inserted == 2

    # Verify stock
    with session_scope() as db:
        s1 = db.execute(
            select(Stock).where(Stock.tenant_id == "day45_alpha", Stock.sku == "DAY45-PROD-A")
        ).scalars().first()
        assert s1 is not None
        assert s1.quantity == 300
        assert s1.warehouse == "London Central Depot"


def test_supplier_order_shipment_ingestion():
    """Test importing Suppliers, Orders, and Shipments with automatic linkage."""
    _setup_test_tenants()

    # 1. Suppliers
    supp_csv = (
        "id,name,phone,city,state,pincode,contact_person,auth_pin,contact_type\n"
        "sup-thames,Thames Valley Goods Ltd,+447700911222,Reading,Berkshire,RG1 1AA,Julian Vance,5566,supplier\n"
        "sup-cotswold,Cotswold Dairy Co,+447700933444,Gloucester,Gloucestershire,GL1 2AB,Emma Wood,1234,customer\n"
    )
    with session_scope() as db:
        res_supp = ingest_csv_data(db, "suppliers", supp_csv, "day45_alpha")
        assert res_supp.success is True
        assert res_supp.inserted == 2

    with session_scope() as db:
        s = db.execute(
            select(Supplier).where(Supplier.tenant_id == "day45_alpha", Supplier.id == "sup-thames")
        ).scalars().first()
        assert s is not None
        assert s.phone == "+447700911222"
        assert s.auth_pin == "5566"
        assert s.contact_type == "supplier"

    # 2. Orders
    order_csv = (
        "id,supplier_id,status,customer_po_ref,total_qty,notes,items\n"
        "PO-DAY45-001,sup-thames,confirmed,TVG/PO/2026/01,100,Pallet delivery,DAY45-PROD-A:100\n"
    )
    with session_scope() as db:
        res_ord = ingest_csv_data(db, "orders", order_csv, "day45_alpha")
        assert res_ord.success is True
        assert res_ord.inserted == 1

    with session_scope() as db:
        o = db.execute(
            select(Order).where(Order.tenant_id == "day45_alpha", Order.id == "PO-DAY45-001")
        ).scalars().first()
        assert o is not None
        assert o.supplier_id == "sup-thames"
        assert o.customer_po_ref == "TVG/PO/2026/01"
        assert o.total_qty == 100

    # 3. Shipments
    ship_csv = (
        "id,order_id,status,carrier,tracking_no,expected_delivery\n"
        "SHP-DAY45-001,PO-DAY45-001,in_transit,Royal Freight UK,GB-EXP-778899,2026-09-01 10:00:00\n"
    )
    with session_scope() as db:
        res_ship = ingest_csv_data(db, "shipments", ship_csv, "day45_alpha")
        assert res_ship.success is True
        assert res_ship.inserted == 1

    with session_scope() as db:
        shp = db.execute(
            select(Shipment).where(Shipment.tenant_id == "day45_alpha", Shipment.id == "SHP-DAY45-001")
        ).scalars().first()
        assert shp is not None
        assert shp.carrier == "Royal Freight UK"
        assert shp.tracking_no == "GB-EXP-778899"
        assert shp.status == "in_transit"


def test_strict_tenant_isolation_during_ingestion():
    """Verify that imports into Tenant A never leak or overwrite data in Tenant B."""
    _setup_test_tenants()

    # Ingest Product into Alpha
    alpha_csv = "sku,name,category,pack_size,mrp_inr\nISOLATION-SKU,Alpha Exclusive Tea,Beverages,50g,10.00\n"
    # Ingest same SKU with different details into Beta
    beta_csv = "sku,name,category,pack_size,mrp_inr\nISOLATION-SKU,Beta Exclusive Coffee,Beverages,500g,25.00\n"

    with session_scope() as db:
        res_a = ingest_csv_data(db, "products", alpha_csv, "day45_alpha")
        res_b = ingest_csv_data(db, "products", beta_csv, "day45_beta")
        assert res_a.success is True
        assert res_b.success is True

    with session_scope() as db:
        prod_a = db.execute(
            select(Product).where(Product.tenant_id == "day45_alpha", Product.sku == "ISOLATION-SKU")
        ).scalars().first()
        prod_b = db.execute(
            select(Product).where(Product.tenant_id == "day45_beta", Product.sku == "ISOLATION-SKU")
        ).scalars().first()

        assert prod_a is not None
        assert prod_a.name == "Alpha Exclusive Tea"
        assert prod_a.mrp_inr == 10.00

        assert prod_b is not None
        assert prod_b.name == "Beta Exclusive Coffee"
        assert prod_b.mrp_inr == 25.00


def test_import_endpoint_api_integration():
    """Test full HTTP POST /api/data/{entity}/import with demo authorization and file upload."""
    _setup_test_tenants()
    app = create_app()
    client = TestClient(app)

    # 1. Attempt import with invalid CSV (missing required field)
    bad_csv = "name,category\nNo SKU Item,Beverages\n"
    resp_bad = client.post(
        "/api/data/products/import?tenant_id=day45_alpha",
        json={"csv_text": bad_csv},
        headers={"x-voxflow-demo": "enabled", "x-voxflow-demo-tenant": "day45_alpha"},
    )
    # Rejection returns 422 with error report
    assert resp_bad.status_code in (422, 403)

    # 2. Valid CSV upload via multipart
    valid_csv = b"sku,name,category,pack_size,mrp_inr\nAPI-SKU-99,Artisan Jam,Preserves,340g,4.25\n"
    files = {"file": ("products.csv", io.BytesIO(valid_csv), "text/csv")}
    resp_good = client.post(
        "/api/data/products/import?tenant_id=day45_alpha",
        files=files,
    )
    assert resp_good.status_code == 200
    res_data = resp_good.json()
    assert res_data["success"] is True
    assert res_data["total_processed"] == 1


@pytest.mark.asyncio
async def test_agent_queries_imported_csv_data():
    """Verify that agent tools accurately query and return newly imported CSV records."""
    from voxflow_api.agent.tools import check_stock, execute_tool
    from voxflow_api.voice.pipeline import CallSession

    _setup_test_tenants()

    # Import products and stock
    prod_csv = "sku,name,category,pack_size,mrp_inr\nAGENT-TEA-01,Highland Breakfast Tea,Tea,100 bags,5.50\n"
    stock_csv = "sku,warehouse,quantity\nAGENT-TEA-01,Edinburgh Port Hub,420\n"

    with session_scope() as db:
        ingest_csv_data(db, "products", prod_csv, "day45_alpha")
        ingest_csv_data(db, "stock", stock_csv, "day45_alpha")

    session = CallSession(
        call_id="call-test-day45",
        tenant_id="day45_alpha",
        verified=True,
    )

    # Directly test check_stock tool
    stock_res = await check_stock(session, sku="AGENT-TEA-01")
    assert stock_res["available"] is True
    assert stock_res["total"] == 420
    assert stock_res["warehouses"][0]["warehouse"] == "Edinburgh Port Hub"

    # Test via execute_tool dispatcher
    disp_res = await execute_tool("check_stock", {"sku": "AGENT-TEA-01"}, session)
    assert disp_res["available"] is True
    assert disp_res["total"] == 420


