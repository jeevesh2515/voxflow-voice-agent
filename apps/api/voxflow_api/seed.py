"""Seed the SQLite/Postgres database with multi-tenant demo data.

Tenants:
  - varun (Varun Beverages — PepsiCo distributor)
  - amul (Amul Dairy — Dairy products distributor)
  - haldirams (Haldirams Snacks — Sweets & Namkeen distributor)
  - britannia (Britannia Industries — Bakery products distributor)

Usage:
    python -m voxflow_api.seed            # add seed data (idempotent, safe to re-run)
    python -m voxflow_api.seed --reset    # SQLite only: drop & recreate everything

Every group of rows is inserted in its own transaction, parent tables first,
because the ORM's foreign keys are bare ForeignKey columns with no relationship()
behind them — SQLAlchemy cannot infer the insert order from them, so this script
supplies it explicitly. Re-running skips whatever already landed.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .db import (
    Appointment,
    Call,
    CommunicationLog,
    Order,
    Product,
    Shipment,
    Stock,
    Supplier,
    Tenant,
    TenantPhoneNumber,
    init_db,
    reset_db,
    session_scope,
)
from .logging import get_logger, setup_logging


log = get_logger(__name__)
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


TENANTS = [
    {"id": "varun", "name": "Varun Beverages (PepsiCo)", "logo_url": "/logos/pepsi.png"},
    {"id": "amul", "name": "Amul Dairy Products", "logo_url": "/logos/amul.png"},
    {"id": "haldirams", "name": "Haldirams Snacks & Sweets", "logo_url": "/logos/haldirams.png"},
    {"id": "britannia", "name": "Britannia Foods", "logo_url": "/logos/britannia.png"},
]

TENANT_PRODUCTS = {
    "varun": [
        {"sku": "PEP-250ML-12", "name": "Pepsi Can 250ml (Pack of 12)", "category": "Carbonated", "pack_size": "250ml x 12", "mrp_inr": 480.0},
        {"sku": "7UP-500ML-24", "name": "7UP Pet Bottle 500ml (Pack of 24)", "category": "Carbonated", "pack_size": "500ml x 24", "mrp_inr": 960.0},
        {"sku": "MIR-250ML-12", "name": "Mirinda Orange 250ml (Pack of 12)", "category": "Carbonated", "pack_size": "250ml x 12", "mrp_inr": 480.0},
        {"sku": "MTN-750ML-12", "name": "Mountain Dew 750ml (Pack of 12)", "category": "Carbonated", "pack_size": "750ml x 12", "mrp_inr": 600.0},
        {"sku": "TROP-1L-06", "name": "Tropicana Orange Juice 1L (Pack of 6)", "category": "Juices", "pack_size": "1L x 6", "mrp_inr": 660.0},
    ],
    "amul": [
        {"sku": "AML-BUTTER-500G", "name": "Amul Pasteurised Butter 500g", "category": "Dairy", "pack_size": "500g x 20", "mrp_inr": 5500.0},
        {"sku": "AML-MILK-1L", "name": "Amul Taaza Toned Milk 1L", "category": "Dairy", "pack_size": "1L x 12", "mrp_inr": 720.0},
        {"sku": "AML-CHEESE-200G", "name": "Amul Cheese Slices 200g", "category": "Dairy", "pack_size": "200g x 30", "mrp_inr": 4200.0},
        {"sku": "AML-GHEE-1L", "name": "Amul Pure Ghee 1L Tin", "category": "Dairy", "pack_size": "1L x 10", "mrp_inr": 6200.0},
    ],
    "haldirams": [
        {"sku": "HAL-BHUJIA-400G", "name": "Haldiram's Bikaneri Bhujia 400g", "category": "Namkeen", "pack_size": "400g x 24", "mrp_inr": 2880.0},
        {"sku": "HAL-GULAB-1KG", "name": "Haldiram's Gulab Jamun 1kg Tin", "category": "Sweets", "pack_size": "1kg x 12", "mrp_inr": 2640.0},
        {"sku": "HAL-SOAN-500G", "name": "Haldiram's Soan Papdi 500g", "category": "Sweets", "pack_size": "500g x 20", "mrp_inr": 2400.0},
        {"sku": "HAL-KHATTA-400G", "name": "Haldiram's Khatta Meetha 400g", "category": "Namkeen", "pack_size": "400g x 24", "mrp_inr": 2640.0},
    ],
    "britannia": [
        {"sku": "BRT-GOODDAY-600G", "name": "Britannia Good Day Butter Cookies", "category": "Biscuits", "pack_size": "600g x 18", "mrp_inr": 2160.0},
        {"sku": "BRT-BOURBON-400G", "name": "Britannia Bourbon Chocolate Biscuits", "category": "Biscuits", "pack_size": "400g x 20", "mrp_inr": 1800.0},
        {"sku": "BRT-MILKBIKIS-500G", "name": "Britannia Milk Bikis Cream", "category": "Biscuits", "pack_size": "500g x 20", "mrp_inr": 1600.0},
        {"sku": "BRT-HEARTS-300G", "name": "Britannia Little Hearts", "category": "Biscuits", "pack_size": "300g x 30", "mrp_inr": 1500.0},
    ],
}

TENANT_SUPPLIERS = {
    "varun": [
        {"id": "sup-varun-001", "name": "Sharma Beverages Wholesale", "phone": "+919876543210", "city": "Gurgaon", "state": "Haryana", "pincode": "122001", "contact_person": "Rajesh Sharma", "gstin": "06AAAAA0000A1Z5"},
        {"id": "sup-varun-002", "name": "Verma Traders", "phone": "+919812345678", "city": "Noida", "state": "Uttar Pradesh", "pincode": "201301", "contact_person": "Amit Verma", "gstin": "09BBBBB1111B1Z2"},
        {"id": "sup-varun-003", "name": "Delhi Retail Hub", "phone": "+919999888777", "city": "New Delhi", "state": "Delhi", "pincode": "110001", "contact_person": "Sunil Gupta", "gstin": "07CCCCC2222C1Z9"},
    ],
    "amul": [
        {"id": "sup-amul-001", "name": "Anand Dairy Supplies", "phone": "+919825012345", "city": "Anand", "state": "Gujarat", "pincode": "388001", "contact_person": "Ketan Patel", "gstin": "24DDDDD3333D1Z1"},
        {"id": "sup-amul-002", "name": "Gujarat Cold Chain", "phone": "+919898098765", "city": "Ahmedabad", "state": "Gujarat", "pincode": "380001", "contact_person": "Vikram Desai", "gstin": "24EEEEE4444E1Z4"},
    ],
    "haldirams": [
        {"id": "sup-hal-001", "name": "Nagpur Sweets Agency", "phone": "+919765432109", "city": "Nagpur", "state": "Maharashtra", "pincode": "440001", "contact_person": "Sanjay Haldiram", "gstin": "27FFFFF5555F1Z7"},
        {"id": "sup-hal-002", "name": "Kolkata Namkeen Mart", "phone": "+919830011223", "city": "Kolkata", "state": "West Bengal", "pincode": "700001", "contact_person": "Pranab Roy", "gstin": "19GGGGG6666G1Z3"},
    ],
    "britannia": [
        {"id": "sup-brt-001", "name": "Bangalore Biscuit Depot", "phone": "+919845099887", "city": "Bengaluru", "state": "Karnataka", "pincode": "560001", "contact_person": "Ramesh Rao", "gstin": "29HHHHH7777H1Z6"},
        {"id": "sup-brt-002", "name": "Chennai Foods Agency", "phone": "+919840033445", "city": "Chennai", "state": "Tamil Nadu", "pincode": "600001", "contact_person": "K. Murugan", "gstin": "33IIIII8888I1Z8"},
    ],
}


def _absent(model, pk) -> bool:
    """True when a row is missing, checked in its own short transaction.

    Used to gate each seeding stage so the whole script is re-runnable: a stage
    whose rows already landed is skipped, and a stage that never ran completes.
    """
    with session_scope() as db:
        return db.get(model, pk) is None


def seed(reset: bool = False) -> None:
    setup_logging()
    if reset:
        # reset_db() is drop_all() + create_all(). On SQLite that is a harmless
        # dev convenience. On Postgres it is destructive in a way that is easy to
        # miss: create_all() re-creates only what the ORM declares, so every
        # object the reviewed SQL migrations establish BEYOND the ORM — the 22
        # row-level-security policies above all — is dropped and never comes
        # back. The result is a database that still accepts writes but no longer
        # isolates one tenant's calls from another's. Refuse rather than warn.
        with session_scope() as probe:
            dialect = probe.get_bind().dialect.name
        if dialect != "sqlite":
            raise SystemExit(
                "refusing --reset on %s: drop_all/create_all would destroy the "
                "row-level-security policies and indexes created by migrations/, "
                "which create_all() cannot rebuild. Re-apply the SQL migrations "
                "instead, then run this script without --reset." % dialect
            )
        log.info("seed.reset")
        reset_db()
    else:
        init_db()

    # ---- Stage 1: tenants -------------------------------------------------
    # Every other table has a tenant_id foreign key, so tenants must EXIST IN THE
    # DATABASE — not merely be pending in a session — before anything else is
    # inserted. That is why each stage below gets its own session_scope() and
    # therefore its own COMMIT.
    #
    # This was one transaction, and Postgres rejected it:
    #   ForeignKeyViolation: insert or update on table "products" violates foreign
    #   key constraint "products_tenant_id_fkey"
    #   DETAIL: Key (tenant_id)=(varun) is not present in table "tenants".
    #
    # The reason is subtle and worth knowing, because it will bite anywhere else
    # this pattern appears: SQLAlchemy's unit of work orders INSERTs by MAPPER
    # dependency, and mapper dependencies come from relationship(), not from bare
    # ForeignKey columns. db.py declares exactly two relationships
    # (Supplier.orders <-> Order.supplier); Tenant -> Product is a bare FK, so the
    # unit of work had no reason to put tenants first and did not. SessionLocal is
    # autoflush=False, so nothing hit the database until the single commit, at
    # which point the order was whatever the identity map happened to produce.
    #
    # SQLite hid this for months: it does not enforce foreign keys unless
    # `PRAGMA foreign_keys=ON` is issued per connection. The seed was already
    # wrong on SQLite; only Postgres bothered to say so.
    with session_scope() as db:
        if db.query(Tenant).count() == 0:
            for t in TENANTS:
                db.add(Tenant(**t))
            log.info("seed.tenants", count=len(TENANTS))

    # ---- Stage 2: products + suppliers (need committed tenants) -----------
    with session_scope() as db:
        if db.query(Product).count() == 0:
            for tid, prods in TENANT_PRODUCTS.items():
                for p in prods:
                    db.add(Product(tenant_id=tid, **p))
            log.info("seed.products")

        if db.query(Supplier).count() == 0:
            for tid, sups in TENANT_SUPPLIERS.items():
                for s in sups:
                    db.add(Supplier(tenant_id=tid, **s))
            log.info("seed.suppliers")

    # ---- Stage 3: stock (stock.sku is a FK to products.sku) ---------------
    with session_scope() as db:
        if db.query(Stock).count() == 0:
            warehouses = ["Gurgaon-WH1", "Noida-WH2", "Delhi-Central", "Anand-ColdStorage", "Nagpur-Distr", "BLR-Hub"]
            for tid, prods in TENANT_PRODUCTS.items():
                for i, p in enumerate(prods):
                    wh = warehouses[i % len(warehouses)]
                    qty = 150 if i % 2 == 0 else (0 if i == 1 else 45)
                    db.add(Stock(tenant_id=tid, sku=p["sku"], warehouse=wh, quantity=qty, updated_at=datetime.now(timezone.utc)))
            log.info("seed.stock")

    # ---- Stage 4: orders (need committed tenants + suppliers) -------------
    # History used to be gated on `if reset:`, which meant a plain
    # `python -m voxflow_api.seed` produced tenants, products, suppliers and stock
    # but NOT A SINGLE ORDER — and orders are the only thing the order-status flow
    # actually reads. You would seed, see "seed.done", ring in to ask whether your
    # PO had been signed, and the agent would correctly report that no such order
    # exists. Worse, the workaround was `--reset`, which is exactly the flag that
    # must never touch Postgres (see the guard above).
    #
    # Gate on emptiness like every other stage. "Drop the tables first" and "is
    # there data yet" are separate questions and no longer share a flag.
    with session_scope() as _probe:
        _history_empty = _probe.query(Order).count() == 0
    if _history_empty:
        with session_scope() as db:
            now = datetime.now(timezone.utc)
            # --- Varun: a SIGNED, dispatched PO. The happy-path demo call. ---
            db.add(
                Order(
                    id="PO-1717000000-001",
                    tenant_id="varun",
                    supplier_id="sup-varun-001",
                    status="shipped",
                    items_json=json.dumps([{"sku": "PEP-250ML-12", "quantity": 500}]),
                    total_qty=500,
                    notes="Urgent delivery required before weekend.",
                    customer_po_ref="VB/PO/2026/0912",
                    po_signed=1,
                    po_signed_at=now - timedelta(days=14),
                    po_signed_by="Anita Desai",
                    dispatched_at=now - timedelta(days=10),
                    created_at=now - timedelta(days=16),
                )
            )
            # --- Varun: an UNSIGNED PO, so you can demo the other answer. ---
            db.add(
                Order(
                    id="PO-1717000000-004",
                    tenant_id="varun",
                    supplier_id="sup-varun-001",
                    status="pending",
                    items_json=json.dumps([{"sku": "PEP-250ML-12", "quantity": 120}]),
                    total_qty=120,
                    notes="Awaiting credit approval before we counter-sign.",
                    customer_po_ref="VB/PO/2026/1001",
                    po_signed=0,
                    created_at=now - timedelta(days=2),
                )
            )
            # Sample PO for Amul
            db.add(
                Order(
                    id="PO-1717000000-002",
                    tenant_id="amul",
                    supplier_id="sup-amul-001",
                    status="pending",
                    items_json=json.dumps([{"sku": "AML-BUTTER-500G", "quantity": 20}]),
                    total_qty=20,
                    notes="Requires refrigerated truck.",
                    created_at=now - timedelta(days=1),
                )
            )
            # Sample PO for Haldirams
            db.add(
                Order(
                    id="PO-1717000000-003",
                    tenant_id="haldirams",
                    supplier_id="sup-hal-001",
                    status="confirmed",
                    # HAL-BHUJIA-400G, not the HAL-BHUJIA-1KG this used to say:
                    # items_json is text with no FK, so nothing rejected the typo,
                    # but the agent reads these SKUs back to the caller and would
                    # have quoted a product that does not exist in the catalog.
                    items_json=json.dumps([{"sku": "HAL-BHUJIA-400G", "quantity": 30}]),
                    total_qty=30,
                    notes="Express dispatch",
                    created_at=now - timedelta(hours=12),
                )
            )
            log.info("seed.orders")

    # ---- Stage 5: shipments (shipments.order_id is a FK to orders.id) ------
    # Same rule as tenants -> products: Shipment -> Order is a bare ForeignKey
    # with no relationship() behind it, so the orders above must be COMMITTED,
    # not merely pending, before a shipment can reference one.
    if _absent(Shipment, "SHP-9901"):
        with session_scope() as db:
            now = datetime.now(timezone.utc)

            # Sample Shipment
            db.add(
                Shipment(
                    id="SHP-9901",
                    tenant_id="varun",
                    order_id="PO-1717000000-001",
                    status="in_transit",
                    carrier="VRL Logistics",
                    tracking_no="VRL-998877",
                    expected_delivery=now + timedelta(days=1),
                    last_update=now - timedelta(hours=3),
                    # `location` is what the agent reads out as "where it has
                    # reached" — get_order_details uses the last entry.
                    history_json=json.dumps([
                        {"at": (now - timedelta(days=10)).isoformat(), "status": "booked",
                         "location": "Gurgaon DC", "note": "Order processed"},
                        {"at": (now - timedelta(days=9)).isoformat(), "status": "dispatched",
                         "location": "Gurgaon DC", "note": "Handed to VRL Logistics"},
                        {"at": (now - timedelta(hours=3)).isoformat(), "status": "in_transit",
                         "location": "Ghaziabad Hub", "note": "In transit to destination"},
                    ]),
                )
            )
            log.info("seed.shipments")

    # ---- Stage 6: Twilio number -> tenant map ------------------------------
    # This is the ONE table you will edit by hand later (SETUP.md step 7, or
    # scripts/map_phone.py), so it gets its own stage and its own per-row guard:
    # adding your real Twilio number must not be short-circuited by some other
    # stage's "already seeded" check.
    if _absent(TenantPhoneNumber, "+15550100001"):
        with session_scope() as db:
            # --- Map active phone numbers to tenants ---
            for number, tid, label, prov in (
                ("+442046404552", "varun", "Varun Beverages Amazon Connect UK line", "connect"),
                ("+15550100001", "varun", "Varun Beverages demo line", "connect"),
                ("+15550100002", "amul", "Amul support line", "connect"),
            ):
                if not db.get(TenantPhoneNumber, number):
                    db.add(TenantPhoneNumber(phone_number=number, tenant_id=tid, label=label, provider=prov))
            log.info("seed.tenant_phone_numbers")

    # ---- Stage 7: calls, appointments, communication logs -----------------
    # These reference only tenants and suppliers, both committed in stages 1-2.
    if _absent(Call, "call_sample_01"):
        with session_scope() as db:
            now = datetime.now(timezone.utc)

            # Sample Calls
            db.add(
                Call(
                    id="call_sample_01",
                    tenant_id="varun",
                    started_at=now - timedelta(minutes=45),
                    ended_at=now - timedelta(minutes=42),
                    duration_sec=180,
                    supplier_id="sup-varun-001",
                    caller_phone="+919876543210",
                    caller_name="Rajesh Sharma",
                    language="hi",
                    intent="create_po",
                    outcome="resolved",
                    escalated=0,
                    transcript_json=json.dumps([
                        {"role": "agent", "text": "नमस्ते, VoxFlow में आपका स्वागत है।", "at": (now - timedelta(minutes=45)).timestamp()},
                        {"role": "caller", "text": "मुझे 50 केस पेप्सी 250ml का ऑर्डर देना है।", "at": (now - timedelta(minutes=44)).timestamp()},
                        {"role": "agent", "text": "ऑर्डर PO-1717000000-001 बना दिया गया है।", "at": (now - timedelta(minutes=43)).timestamp()},
                    ]),
                    actions_json=json.dumps([{"name": "create_po", "args": {"sku": "PEP-250ML-12", "quantity": 50}}]),
                )
            )
            log.info("seed.calls")

            # Sample Appointments
            db.add(
                Appointment(
                    id="app-101",
                    tenant_id="varun",
                    supplier_id="sup-varun-001",
                    datetime=now + timedelta(days=2),
                    purpose="Review monthly stock quotas and pricing tier update",
                    status="confirmed",
                )
            )
            db.add(
                Appointment(
                    id="app-102",
                    tenant_id="amul",
                    supplier_id="sup-amul-001",
                    datetime=now + timedelta(days=3),
                    purpose="Cold storage expansion discussion",
                    status="pending",
                )
            )
            log.info("seed.appointments")

            # Sample Communication logs
            db.add(
                CommunicationLog(
                    id="comm-201",
                    tenant_id="varun",
                    channel="whatsapp",
                    recipient="+919876543210",
                    subject=None,
                    body="Hello Rajesh! Your PO-1717000000-001 has been booked with tracking VRL-998877.",
                    status="sent",
                )
            )
            db.add(
                CommunicationLog(
                    id="comm-202",
                    tenant_id="amul",
                    channel="email",
                    recipient="ketan@ananddairy.com",
                    subject="PO-1717000000-002 Confirmation Notice",
                    body="Dear Ketan, Your PO for 20 cases Amul Butter 500g has been received.",
                    status="sent",
                )
            )
            log.info("seed.communications")

    log.info("seed.done")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset",
        action="store_true",
        help="SQLite only: drop & recreate all tables before seeding. Refused on "
             "Postgres, where it would delete the RLS policies from migrations/.",
    )
    args = parser.parse_args()
    seed(reset=args.reset)


if __name__ == "__main__":
    main()
