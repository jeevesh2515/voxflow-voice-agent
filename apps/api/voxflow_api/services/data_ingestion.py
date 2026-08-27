"""Company Data Ingestion Service — CSV validation, template generation, and transactional upsert.

Supports 5 core supply-chain entities:
- products: Catalog items and SKUs
- stock: Warehouse inventory levels
- suppliers: Supplier & customer directory
- orders: Inbound & outbound purchase orders
- shipments: Tracking numbers and dispatch logistics
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import (
    Order,
    Product,
    Shipment,
    Stock,
    Supplier,
)
from ..logging import get_logger
from .pin_security import hash_pin, validate_pin
from .telephony_routing import normalize_e164

log = get_logger(__name__)

SUPPORTED_ENTITIES = ("products", "stock", "suppliers", "orders", "shipments")

# Maximum size & row limits
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_ROWS_PER_IMPORT = 5000


@dataclass
class RowError:
    row_number: int
    column: str
    message: str
    raw_value: str = ""


@dataclass
class IngestionValidationResult:
    entity: str
    total_rows: int
    valid_rows: int
    error_count: int
    errors: list[dict[str, Any]] = field(default_factory=list)
    preview: list[dict[str, Any]] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    is_valid: bool = False


@dataclass
class IngestionResult:
    success: bool
    entity: str
    tenant_id: str
    inserted: int
    updated: int
    total_processed: int
    message: str = ""
    errors: list[dict[str, Any]] = field(default_factory=list)


ENTITY_SCHEMAS: dict[str, dict[str, Any]] = {
    "products": {
        "required_columns": ["sku", "name"],
        "optional_columns": ["category", "pack_size", "mrp_inr", "price"],
        "description": "Product catalog with SKUs, category names, pack sizes, and prices",
        "sample_rows": [
            {"sku": "SKU-BEV-001", "name": "Classic Sparkling Water 500ml", "category": "Beverages", "pack_size": "24 x 500ml", "mrp_inr": "18.50"},
            {"sku": "SKU-BEV-002", "name": "Citrus Lemonade 330ml Can", "category": "Beverages", "pack_size": "12 x 330ml", "mrp_inr": "14.00"},
            {"sku": "SKU-SNK-001", "name": "Organic Oat Bars Box", "category": "Snacks", "pack_size": "10 x 40g", "mrp_inr": "22.00"},
        ],
    },
    "stock": {
        "required_columns": ["sku", "warehouse", "quantity"],
        "optional_columns": [],
        "description": "Warehouse stock levels and bin availability per SKU",
        "sample_rows": [
            {"sku": "SKU-BEV-001", "warehouse": "London Central Depot", "quantity": "450"},
            {"sku": "SKU-BEV-002", "warehouse": "London Central Depot", "quantity": "120"},
            {"sku": "SKU-SNK-001", "warehouse": "Manchester Freight Hub", "quantity": "80"},
        ],
    },
    "suppliers": {
        "required_columns": ["name", "phone"],
        "optional_columns": ["id", "city", "state", "pincode", "contact_person", "gstin", "auth_pin", "contact_type"],
        "description": "Supplier & customer contact book with verified PINs and addresses",
        "sample_rows": [
            {
                "id": "sup-brit-bev",
                "name": "British Beverage Supplies Ltd",
                "phone": "+447700900123",
                "city": "London",
                "state": "Greater London",
                "pincode": "EC1A 1BB",
                "contact_person": "Arthur Pendelton",
                "gstin": "GB123456789",
                "auth_pin": "",
                "contact_type": "supplier",
            },
            {
                "id": "sup-midland-dist",
                "name": "Midland Fast Haulage",
                "phone": "+447700900456",
                "city": "Birmingham",
                "state": "West Midlands",
                "pincode": "B1 1AA",
                "contact_person": "Sarah Jenkins",
                "gstin": "GB987654321",
                "auth_pin": "",
                "contact_type": "customer",
            },
        ],
    },
    "orders": {
        "required_columns": ["id", "supplier_id"],
        "optional_columns": ["status", "customer_po_ref", "total_qty", "notes", "items"],
        "description": "Purchase orders with supplier links, item lists, and delivery notes",
        "sample_rows": [
            {
                "id": "PO-2026-8001",
                "supplier_id": "sup-brit-bev",
                "status": "confirmed",
                "customer_po_ref": "BBS/PO/9901",
                "total_qty": "150",
                "notes": "Urgent pallet drop off at loading bay 3",
                "items": "SKU-BEV-001:100;SKU-BEV-002:50",
            },
            {
                "id": "PO-2026-8002",
                "supplier_id": "sup-midland-dist",
                "status": "pending",
                "customer_po_ref": "MFH/PO/7742",
                "total_qty": "80",
                "notes": "Morning dock booking required",
                "items": "SKU-SNK-001:80",
            },
        ],
    },
    "shipments": {
        "required_columns": ["id", "order_id"],
        "optional_columns": ["status", "carrier", "tracking_no", "expected_delivery"],
        "description": "Logistics shipments, freight carriers, and tracking references",
        "sample_rows": [
            {
                "id": "SHP-8801",
                "order_id": "PO-2026-8001",
                "status": "in_transit",
                "carrier": "Royal Express Logistics",
                "tracking_no": "GB-TRK-990123",
                "expected_delivery": "2026-08-30 14:00:00",
            },
            {
                "id": "SHP-8802",
                "order_id": "PO-2026-8002",
                "status": "booked",
                "carrier": "Midland Freight Carrier",
                "tracking_no": "GB-TRK-445890",
                "expected_delivery": "2026-09-02 09:30:00",
            },
        ],
    },
}


def get_csv_template(entity: str) -> str:
    """Generate a clean CSV string template with canonical headers and realistic sample rows."""
    if entity not in ENTITY_SCHEMAS:
        raise ValueError(f"Unsupported entity: {entity}. Allowed: {SUPPORTED_ENTITIES}")

    schema = ENTITY_SCHEMAS[entity]
    headers = schema["required_columns"] + schema["optional_columns"]
    unique_headers = list(dict.fromkeys(headers))

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=unique_headers, lineterminator="\n")
    writer.writeheader()
    for row in schema.get("sample_rows", []):
        writer.writerow({h: row.get(h, "") for h in unique_headers})

    return output.getvalue()


def parse_csv_content(csv_text: str) -> tuple[list[str], list[dict[str, str]]]:
    """Parse CSV text into normalized headers and row dictionaries."""
    clean_text = csv_text.strip().lstrip("\ufeff")
    if not clean_text:
        return [], []

    first_line = clean_text.splitlines()[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","

    reader = csv.reader(io.StringIO(clean_text), delimiter=delimiter)
    try:
        raw_headers = next(reader)
    except StopIteration:
        return [], []

    headers = [h.strip().lower().replace("-", "_") for h in raw_headers if h.strip()]

    rows: list[dict[str, str]] = []
    for line in reader:
        if not line or not any(cell.strip() for cell in line):
            continue
        row_dict = {}
        for idx, h in enumerate(headers):
            row_dict[h] = line[idx].strip() if idx < len(line) else ""
        rows.append(row_dict)

    return headers, rows


def _parse_items_json(raw: str, default_sku: str = "") -> str:
    """Parse item strings like 'SKU1:10;SKU2:20' or valid JSON into canonical JSON array."""
    if not raw.strip():
        if default_sku:
            return json.dumps([{"sku": default_sku, "qty": 1}])
        return json.dumps([])

    if raw.strip().startswith("[") and raw.strip().endswith("]"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return json.dumps(parsed)
        except Exception:
            pass

    items = []
    pairs = [p.strip() for p in re.split(r"[;,]", raw) if p.strip()]
    for pair in pairs:
        if ":" in pair:
            sku, qty_str = pair.split(":", 1)
            try:
                qty = int(qty_str.strip())
            except ValueError:
                qty = 1
            items.append({"sku": sku.strip(), "qty": max(1, qty)})
        else:
            items.append({"sku": pair.strip(), "qty": 1})

    return json.dumps(items)


def _parse_datetime(raw: str) -> datetime | None:
    """Parse various ISO and standard date formats safely."""
    if not raw or not raw.strip():
        return None
    val = raw.strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
    ):
        try:
            return datetime.strptime(val, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(val).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def validate_csv_data(entity: str, csv_text: str, tenant_id: str = "") -> IngestionValidationResult:
    """Validate CSV headers and field data against entity schema."""
    if entity not in ENTITY_SCHEMAS:
        return IngestionValidationResult(
            entity=entity,
            total_rows=0,
            valid_rows=0,
            error_count=1,
            errors=[{"row_number": 0, "column": "entity", "message": f"Unsupported entity '{entity}'", "raw_value": entity}],
            is_valid=False,
        )

    schema = ENTITY_SCHEMAS[entity]
    headers, rows = parse_csv_content(csv_text)

    if not headers or not rows:
        return IngestionValidationResult(
            entity=entity,
            total_rows=0,
            valid_rows=0,
            error_count=1,
            errors=[{"row_number": 0, "column": "file", "message": "CSV file is empty or contains no data rows", "raw_value": ""}],
            is_valid=False,
        )

    if len(rows) > MAX_ROWS_PER_IMPORT:
        return IngestionValidationResult(
            entity=entity,
            total_rows=len(rows),
            valid_rows=0,
            error_count=1,
            errors=[{
                "row_number": 0,
                "column": "file",
                "message": f"File exceeds maximum allowed rows ({MAX_ROWS_PER_IMPORT})",
                "raw_value": str(len(rows)),
            }],
            is_valid=False,
        )

    errors: list[RowError] = []
    missing_required = [req for req in schema["required_columns"] if req not in headers]
    if missing_required:
        errors.append(RowError(
            row_number=1,
            column="headers",
            message=f"Missing required columns: {', '.join(missing_required)}",
            raw_value=f"Found: {headers}",
        ))
        return IngestionValidationResult(
            entity=entity,
            total_rows=len(rows),
            valid_rows=0,
            error_count=len(errors),
            errors=[asdict(e) for e in errors],
            headers=headers,
            is_valid=False,
        )

    preview_rows = []
    for idx, row in enumerate(rows, start=2):
        if entity == "products":
            sku = row.get("sku", "").strip()
            name = row.get("name", "").strip()
            if not sku:
                errors.append(RowError(idx, "sku", "SKU cannot be empty", sku))
            if not name:
                errors.append(RowError(idx, "name", "Product name cannot be empty", name))
            price_val = row.get("mrp_inr") or row.get("price") or "0"
            try:
                float(price_val)
            except ValueError:
                errors.append(RowError(idx, "mrp_inr", "Price/MRP must be a valid numeric number", price_val))

        elif entity == "stock":
            sku = row.get("sku", "").strip()
            warehouse = row.get("warehouse", "").strip()
            qty_val = row.get("quantity", "").strip()
            if not sku:
                errors.append(RowError(idx, "sku", "SKU cannot be empty", sku))
            if not warehouse:
                errors.append(RowError(idx, "warehouse", "Warehouse cannot be empty", warehouse))
            try:
                q = int(qty_val)
                if q < 0:
                    errors.append(RowError(idx, "quantity", "Quantity cannot be negative", qty_val))
            except ValueError:
                errors.append(RowError(idx, "quantity", "Quantity must be an integer", qty_val))

        elif entity == "suppliers":
            name = row.get("name", "").strip()
            phone = row.get("phone", "").strip()
            if not name:
                errors.append(RowError(idx, "name", "Supplier name cannot be empty", name))
            try:
                normalize_e164(phone)
            except ValueError:
                errors.append(RowError(idx, "phone", "Phone number must be valid E.164", phone))
            configured_pin = row.get("auth_pin", "").strip()
            if configured_pin:
                try:
                    validate_pin(configured_pin)
                except ValueError:
                    errors.append(RowError(idx, "auth_pin", "PIN must be 4 to 8 digits", "[REDACTED]"))

        elif entity == "orders":
            order_id = row.get("id", "").strip()
            supplier_id = row.get("supplier_id", "").strip()
            if not order_id:
                errors.append(RowError(idx, "id", "Order ID cannot be empty", order_id))
            if not supplier_id:
                errors.append(RowError(idx, "supplier_id", "Supplier ID cannot be empty", supplier_id))
            total_qty_str = row.get("total_qty", "0").strip() or "0"
            try:
                int(total_qty_str)
            except ValueError:
                errors.append(RowError(idx, "total_qty", "Total quantity must be an integer", total_qty_str))

        elif entity == "shipments":
            shipment_id = row.get("id", "").strip()
            order_id = row.get("order_id", "").strip()
            if not shipment_id:
                errors.append(RowError(idx, "id", "Shipment ID cannot be empty", shipment_id))
            if not order_id:
                errors.append(RowError(idx, "order_id", "Order ID reference cannot be empty", order_id))

        if len(preview_rows) < 10:
            preview = dict(row)
            if "auth_pin" in preview and preview["auth_pin"]:
                preview["auth_pin"] = "[REDACTED]"
            preview_rows.append(preview)

    valid_count = len(rows) - len({e.row_number for e in errors})
    is_valid = len(errors) == 0

    return IngestionValidationResult(
        entity=entity,
        total_rows=len(rows),
        valid_rows=max(0, valid_count),
        error_count=len(errors),
        errors=[asdict(e) for e in errors],
        preview=preview_rows,
        headers=headers,
        is_valid=is_valid,
    )


def ingest_csv_data(
    db: Session,
    entity: str,
    csv_text: str,
    tenant_id: str,
    mode: str = "upsert",
) -> IngestionResult:
    """Execute transactional, all-or-nothing CSV import into Postgres/SQLite."""
    if not tenant_id:
        return IngestionResult(
            success=False,
            entity=entity,
            tenant_id="",
            inserted=0,
            updated=0,
            total_processed=0,
            message="Tenant ID is required for data ingestion",
        )

    val_res = validate_csv_data(entity, csv_text, tenant_id)
    if not val_res.is_valid:
        return IngestionResult(
            success=False,
            entity=entity,
            tenant_id=tenant_id,
            inserted=0,
            updated=0,
            total_processed=val_res.total_rows,
            message=f"Validation failed with {val_res.error_count} error(s). No records were imported.",
            errors=val_res.errors,
        )

    headers, rows = parse_csv_content(csv_text)
    inserted = 0
    updated = 0
    now = datetime.now(timezone.utc)

    try:
        if entity == "products":
            for row in rows:
                sku = row["sku"].strip()
                name = row["name"].strip()
                category = row.get("category", "").strip() or "General"
                pack_size = row.get("pack_size", "").strip() or "1 Unit"
                price_str = row.get("mrp_inr") or row.get("price") or "0"
                mrp_inr = float(price_str)

                existing = db.execute(
                    select(Product).where(Product.tenant_id == tenant_id, Product.sku == sku)
                ).scalars().first()

                if existing:
                    existing.name = name
                    existing.category = category
                    existing.pack_size = pack_size
                    existing.mrp_inr = mrp_inr
                    updated += 1
                else:
                    new_product = Product(
                        sku=sku,
                        tenant_id=tenant_id,
                        name=name,
                        category=category,
                        pack_size=pack_size,
                        mrp_inr=mrp_inr,
                    )
                    db.add(new_product)
                    inserted += 1

        elif entity == "stock":
            for row in rows:
                sku = row["sku"].strip()
                warehouse = row["warehouse"].strip()
                quantity = int(row["quantity"].strip())

                prod = db.execute(
                    select(Product).where(Product.tenant_id == tenant_id, Product.sku == sku)
                ).scalars().first()
                if not prod:
                    db.add(Product(
                        sku=sku,
                        tenant_id=tenant_id,
                        name=f"Product {sku}",
                        category="General",
                        pack_size="1 Unit",
                        mrp_inr=10.0,
                    ))
                    db.flush()

                existing_stock = db.execute(
                    select(Stock).where(
                        Stock.tenant_id == tenant_id,
                        Stock.sku == sku,
                        Stock.warehouse == warehouse,
                    )
                ).scalars().first()

                if existing_stock:
                    existing_stock.quantity = quantity
                    existing_stock.updated_at = now
                    updated += 1
                else:
                    new_stock = Stock(
                        tenant_id=tenant_id,
                        sku=sku,
                        warehouse=warehouse,
                        quantity=quantity,
                        updated_at=now,
                    )
                    db.add(new_stock)
                    inserted += 1

        elif entity == "suppliers":
            for row in rows:
                name = row["name"].strip()
                phone = normalize_e164(row["phone"])
                raw_id = row.get("id", "").strip()
                supp_id = raw_id if raw_id else f"sup-{re.sub(r'[^a-zA-Z0-9]+', '-', name.lower()).strip('-')}"

                city = row.get("city", "").strip() or "London"
                state = row.get("state", "").strip() or "Greater London"
                pincode = row.get("pincode", "").strip() or "EC1A 1BB"
                contact_person = row.get("contact_person", "").strip()
                gstin = row.get("gstin", "").strip()
                configured_pin = row.get("auth_pin", "").strip()
                contact_type = row.get("contact_type", "").strip().lower() or "supplier"
                if contact_type not in ("supplier", "customer", "both"):
                    contact_type = "supplier"

                existing_supp = db.execute(
                    select(Supplier).where(Supplier.tenant_id == tenant_id, Supplier.id == supp_id)
                ).scalars().first()

                if existing_supp:
                    existing_supp.name = name
                    existing_supp.phone = phone
                    existing_supp.city = city
                    existing_supp.state = state
                    existing_supp.pincode = pincode
                    existing_supp.contact_person = contact_person
                    existing_supp.gstin = gstin
                    if configured_pin:
                        existing_supp.auth_pin_hash = hash_pin(configured_pin)
                        existing_supp.auth_pin = None
                        existing_supp.pin_updated_at = datetime.now(timezone.utc)
                    existing_supp.contact_type = contact_type
                    updated += 1
                else:
                    new_supp = Supplier(
                        id=supp_id,
                        tenant_id=tenant_id,
                        name=name,
                        phone=phone,
                        city=city,
                        state=state,
                        pincode=pincode,
                        contact_person=contact_person,
                        gstin=gstin,
                        auth_pin=None,
                        auth_pin_hash=hash_pin(configured_pin) if configured_pin else None,
                        pin_updated_at=datetime.now(timezone.utc) if configured_pin else None,
                        contact_type=contact_type,
                        active=1,
                    )
                    db.add(new_supp)
                    inserted += 1

        elif entity == "orders":
            for row in rows:
                order_id = row["id"].strip()
                supplier_id = row["supplier_id"].strip()
                status = row.get("status", "pending").strip().lower()
                customer_po_ref = row.get("customer_po_ref", "").strip()
                total_qty = int(row.get("total_qty", "0").strip() or "0")
                notes = row.get("notes", "").strip()
                items_json = _parse_items_json(row.get("items", ""))

                supp = db.execute(
                    select(Supplier).where(Supplier.tenant_id == tenant_id, Supplier.id == supplier_id)
                ).scalars().first()
                if not supp:
                    db.add(Supplier(
                        id=supplier_id,
                        tenant_id=tenant_id,
                        name=f"Supplier {supplier_id}",
                        phone="+447700900000",
                        city="London",
                        state="Greater London",
                        pincode="EC1A 1BB",
                        auth_pin=None,
                        auth_pin_hash=None,
                        pin_updated_at=None,
                        active=1,
                    ))
                    db.flush()

                existing_order = db.execute(
                    select(Order).where(Order.tenant_id == tenant_id, Order.id == order_id)
                ).scalars().first()

                if existing_order:
                    existing_order.supplier_id = supplier_id
                    existing_order.status = status
                    existing_order.customer_po_ref = customer_po_ref
                    existing_order.total_qty = total_qty
                    existing_order.notes = notes
                    existing_order.items_json = items_json
                    existing_order.updated_at = now
                    updated += 1
                else:
                    new_order = Order(
                        id=order_id,
                        tenant_id=tenant_id,
                        supplier_id=supplier_id,
                        status=status,
                        customer_po_ref=customer_po_ref,
                        total_qty=total_qty,
                        notes=notes,
                        items_json=items_json,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(new_order)
                    inserted += 1

        elif entity == "shipments":
            for row in rows:
                shipment_id = row["id"].strip()
                order_id = row["order_id"].strip()
                status = row.get("status", "booked").strip().lower()
                carrier = row.get("carrier", "").strip()
                tracking_no = row.get("tracking_no", "").strip()
                exp_delivery = _parse_datetime(row.get("expected_delivery", ""))

                ord_rec = db.execute(
                    select(Order).where(Order.tenant_id == tenant_id, Order.id == order_id)
                ).scalars().first()
                if not ord_rec:
                    supp = db.execute(
                        select(Supplier).where(Supplier.tenant_id == tenant_id)
                    ).scalars().first()
                    supp_id = supp.id if supp else "sup-general"
                    if not supp:
                        db.add(Supplier(
                            id=supp_id,
                            tenant_id=tenant_id,
                            name="General Logistics Supplier",
                            phone="+447700900000",
                            city="London",
                            state="Greater London",
                            pincode="EC1A 1BB",
                        ))
                        db.flush()
                    db.add(Order(
                        id=order_id,
                        tenant_id=tenant_id,
                        supplier_id=supp_id,
                        status="pending",
                        items_json="[]",
                    ))
                    db.flush()

                existing_ship = db.execute(
                    select(Shipment).where(Shipment.tenant_id == tenant_id, Shipment.id == shipment_id)
                ).scalars().first()

                if existing_ship:
                    existing_ship.order_id = order_id
                    existing_ship.status = status
                    existing_ship.carrier = carrier
                    existing_ship.tracking_no = tracking_no
                    existing_ship.expected_delivery = exp_delivery
                    existing_ship.last_update = now
                    updated += 1
                else:
                    new_shipment = Shipment(
                        id=shipment_id,
                        tenant_id=tenant_id,
                        order_id=order_id,
                        status=status,
                        carrier=carrier,
                        tracking_no=tracking_no,
                        expected_delivery=exp_delivery,
                        last_update=now,
                        history_json="[]",
                    )
                    db.add(new_shipment)
                    inserted += 1

        db.commit()
        log.info(
            "data_ingestion.success",
            entity=entity,
            tenant_id=tenant_id,
            inserted=inserted,
            updated=updated,
            total=len(rows),
        )

        return IngestionResult(
            success=True,
            entity=entity,
            tenant_id=tenant_id,
            inserted=inserted,
            updated=updated,
            total_processed=len(rows),
            message=f"Successfully imported {len(rows)} {entity} records ({inserted} created, {updated} updated).",
        )

    except Exception as e:
        db.rollback()
        log.error("data_ingestion.failed", entity=entity, tenant_id=tenant_id, error=str(e))
        return IngestionResult(
            success=False,
            entity=entity,
            tenant_id=tenant_id,
            inserted=0,
            updated=0,
            total_processed=len(rows),
            message=f"Database transaction failed: {str(e)}",
            errors=[{"row_number": 0, "column": "database", "message": str(e), "raw_value": ""}],
        )
