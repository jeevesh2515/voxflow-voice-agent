"""Database verification script — tests multi-tenant queries and database state."""

from __future__ import annotations

import sys
from sqlalchemy import select
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
    session_scope,
)
from .logging import get_logger, setup_logging

log = get_logger(__name__)


def verify() -> bool:
    setup_logging()
    log.info("verify_db.start")

    with session_scope() as db:
        tenants = db.execute(select(Tenant)).scalars().all()
        log.info("verify_db.tenants", count=len(tenants), ids=[t.id for t in tenants])
        if len(tenants) < 4:
            log.error("verify_db.failed", reason="expected at least 4 tenants")
            return False

        for t in tenants:
            sup_count = len(db.execute(select(Supplier).where(Supplier.tenant_id == t.id)).scalars().all())
            prod_count = len(db.execute(select(Product).where(Product.tenant_id == t.id)).scalars().all())
            stock_count = len(db.execute(select(Stock).where(Stock.tenant_id == t.id)).scalars().all())
            log.info("verify_db.tenant_summary", tenant=t.id, suppliers=sup_count, products=prod_count, stock=stock_count)

            if sup_count == 0 or prod_count == 0:
                log.error("verify_db.empty_tenant", tenant=t.id)
                return False

        appointments = db.execute(select(Appointment)).scalars().all()
        comms = db.execute(select(CommunicationLog)).scalars().all()
        log.info("verify_db.logs", appointments=len(appointments), communications=len(comms))

    log.info("verify_db.success")
    return True


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
