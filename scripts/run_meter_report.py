"""Periodic Stripe meter-event reporter for VoxFlow.

Reads unbilled completed calls from ``calls`` and reports per-call-minute
usage to Stripe Billing Meters (see services/metering_service.py for the
rounding rule, idempotency, and failure semantics).

Usage
-----
    # DRY RUN (prints what would be sent, sends nothing) - default
    python run_meter_report.py
    python run_meter_report.py --tenant <tenant_id>

    # SEND for real (requires STRIPE_SECRET_KEY + STRIPE_METER_EVENT_NAME)
    python run_meter_report.py --execute

Schedule (e.g. crontab, hourly - Stripe's late-event window means run at
least daily so usage remains in the correct billing period):
    0 * * * * cd /srv/voxflow && ./.venv/bin/python scripts/run_meter_report.py --execute >> /var/log/voxflow-meter.log 2>&1
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from voxflow_api.config import get_settings
from voxflow_api.services.metering_service import meter_all_tenants


def main() -> int:
    parser = argparse.ArgumentParser(description="Report VoxFlow call minutes to Stripe meters")
    parser.add_argument("--tenant", default=None, help="Restrict to one tenant id")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually send meter events (default is a dry run)",
    )
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)

    started = time.monotonic()
    with Session() as db:
        summary = meter_all_tenants(db, tenant_id=args.tenant, dry_run=not args.execute)

    elapsed_s = time.monotonic() - started
    print(
        f"[{datetime.now(timezone.utc).isoformat()}] mode={'EXECUTE' if args.execute else 'DRY-RUN'} "
        f"tenants={summary['tenants']} sent={summary['sent']} skipped={summary['skipped']} "
        f"errors={len(summary['errors'])} elapsed={elapsed_s:.1f}s"
    )
    if summary.get("errors"):
        for err in summary["errors"]:
            print(f"  ERROR tenant={err.get('tenant_id')} detail={err.get('err')}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
