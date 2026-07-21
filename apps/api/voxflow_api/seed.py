"""Seed the SQLite database with the Varun Beverages demo scenario.

Usage:
    python -m voxflow_api.seed            # add seed data (skips if rows exist)
    python -m voxflow_api.seed --reset    # drop & recreate everything
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .db import Call, Order, Product, Shipment, Stock, Supplier, init_db, reset_db, session_scope
from .logging import get_logger, setup_logging


log = get_logger(__name__)
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _read(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def seed(reset: bool = False) -> None:
    setup_logging()
    if reset:
        log.info("seed.reset")
        reset_db()
    else:
        init_db()

    suppliers_data = _read("seed_suppliers.json")
    stock_data = _read("seed_stock.json")
    history_data = _read("seed_history.json")

    with session_scope() as db:
        if db.query(Supplier).count() == 0:
            for s in suppliers_data["suppliers"]:
                db.add(Supplier(**s))
            log.info("seed.suppliers", count=len(suppliers_data["suppliers"]))

        if db.query(Product).count() == 0:
            for p in stock_data["products"]:
                db.add(Product(**p))
            log.info("seed.products", count=len(stock_data["products"]))

        if db.query(Stock).count() == 0:
            for st in stock_data["stock"]:
                db.add(Stock(**st, updated_at=datetime.now(timezone.utc)))
            log.info("seed.stock", count=len(stock_data["stock"]))

    # Orders + shipments + calls (history) — only when reset=True to keep them stable
    if reset:
        with session_scope() as db:
            now = datetime.now(timezone.utc)
            for o in history_data["orders"]:
                created = now - timedelta(days=o["created_days_ago"])
                db.add(
                    Order(
                        id=o["id"],
                        supplier_id=o["supplier_id"],
                        status=o["status"],
                        items_json=json.dumps(o["items"]),
                        total_qty=sum(i["quantity"] for i in o["items"]),
                        notes=o["notes"],
                        created_at=created,
                        updated_at=created,
                    )
                )
            log.info("seed.orders", count=len(history_data["orders"]))

            for sh in history_data["shipments"]:
                ed = now + timedelta(days=sh["expected_delivery_days"])
                last = now + timedelta(hours=sh["history"][-1]["at_offset_hours"])
                history = [
                    {
                        "at": (now + timedelta(hours=h["at_offset_hours"])).isoformat(),
                        "status": h["status"],
                        "note": h["note"],
                    }
                    for h in sh["history"]
                ]
                db.add(
                    Shipment(
                        id=sh["id"],
                        order_id=sh["order_id"],
                        status=sh["status"],
                        carrier=sh["carrier"],
                        tracking_no=sh["tracking_no"],
                        expected_delivery=ed,
                        last_update=last,
                        history_json=json.dumps(history),
                    )
                )
            log.info("seed.shipments", count=len(history_data["shipments"]))

            for c in history_data["calls"]:
                started = now - timedelta(minutes=c["minutes_ago"])
                transcript = [
                    {"role": t["role"], "text": t["text"], "at": (started + timedelta(seconds=t["at_offset_sec"])).timestamp()}
                    for t in c["transcript"]
                ]
                actions = [
                    {
                        "name": a["name"],
                        "args": a.get("args", {}),
                        "result": None,
                        "at": started.timestamp(),
                    }
                    for a in c["actions"]
                ]
                db.add(
                    Call(
                        id=c["id"],
                        started_at=started,
                        ended_at=started + timedelta(seconds=c["duration_sec"]),
                        duration_sec=c["duration_sec"],
                        supplier_id=c.get("supplier_id"),
                        caller_phone=c.get("caller_phone", ""),
                        caller_name=c.get("caller_name", ""),
                        language=c.get("language", "hi"),
                        intent=c.get("intent", ""),
                        outcome=c.get("outcome", "resolved"),
                        escalated=1 if c.get("escalated") else 0,
                        transcript_json=json.dumps(transcript),
                        actions_json=json.dumps(actions),
                    )
                )
            log.info("seed.calls", count=len(history_data["calls"]))

    log.info("seed.done")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Drop & recreate all tables before seeding")
    args = parser.parse_args()
    seed(reset=args.reset)


if __name__ == "__main__":
    main()
