"""Seed the SQLite/Postgres database with multi-tenant demo data.

Tenants:
  - varun (Varun Beverages — PepsiCo distributor)
  - amul (Amul Dairy — Dairy products distributor)
  - haldirams (Haldirams Snacks — Sweets & Namkeen distributor)
  - britannia (Britannia Industries — Bakery products distributor)

Usage:
    python -m voxflow_api.seed            # add seed data
    python -m voxflow_api.seed --reset    # drop & recreate everything
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
    WorksheetLog,
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


def seed(reset: bool = False) -> None:
    setup_logging()
    if reset:
        log.info("seed.reset")
        reset_db()
    else:
        init_db()

    with session_scope() as db:
        # 1. Tenants
        if db.query(Tenant).count() == 0:
            for t in TENANTS:
                db.add(Tenant(**t))
            log.info("seed.tenants", count=len(TENANTS))

        # 2. Products & Suppliers
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

        # 3. Stock
        if db.query(Stock).count() == 0:
            warehouses = ["Gurgaon-WH1", "Noida-WH2", "Delhi-Central", "Anand-ColdStorage", "Nagpur-Distr", "BLR-Hub"]
            for tid, prods in TENANT_PRODUCTS.items():
                for i, p in enumerate(prods):
                    wh = warehouses[i % len(warehouses)]
                    qty = 150 if i % 2 == 0 else (0 if i == 1 else 45)
                    db.add(Stock(tenant_id=tid, sku=p["sku"], warehouse=wh, quantity=qty, updated_at=datetime.now(timezone.utc)))
            log.info("seed.stock")

    # History (Orders, Shipments, Calls, Appointments, Logs)
    if reset:
        with session_scope() as db:
            now = datetime.now(timezone.utc)
            # Sample PO for Varun
            db.add(
                Order(
                    id="PO-1717000000-001",
                    tenant_id="varun",
                    supplier_id="sup-varun-001",
                    status="confirmed",
                    items_json=json.dumps([{"sku": "PEP-250ML-12", "quantity": 50}]),
                    total_qty=50,
                    notes="Urgent delivery required before weekend.",
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
            log.info("seed.orders")

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
                    history_json=json.dumps([
                        {"at": (now - timedelta(days=1)).isoformat(), "status": "booked", "note": "Order processed"},
                        {"at": (now - timedelta(hours=3)).isoformat(), "status": "in_transit", "note": "Dispatched from Gurgaon"},
                    ]),
                )
            )
            log.info("seed.shipments")

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
    parser.add_argument("--reset", action="store_true", help="Drop & recreate all tables before seeding")
    args = parser.parse_args()
    seed(reset=args.reset)


if __name__ == "__main__":
    main()
