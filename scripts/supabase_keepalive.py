#!/usr/bin/env python3
"""Supabase PostgreSQL Keep-Alive Heartbeat Utility.

Prevents Supabase Free Tier projects from pausing due to inactivity by executing
a lightweight, indexed query on a recurring schedule.

Usage:
  # Run a single heartbeat ping:
  python3 scripts/supabase_keepalive.py --once

  # Run as a persistent background daemon every 6 hours:
  python3 scripts/supabase_keepalive.py --interval-hours 6
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

# Ensure apps/api is on sys.path for standalone script execution
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
API_DIR = os.path.join(REPO_ROOT, "apps", "api")
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from sqlalchemy import text
from voxflow_api.db import SessionLocal, _db_url


def ping_supabase() -> dict[str, Any]:
    """Execute a lightweight keep-alive heartbeat against the configured database."""
    t0 = time.perf_counter()
    now_iso = datetime.now(timezone.utc).isoformat()

    with SessionLocal() as session:
        # 1. Base engine ping
        session.execute(text("SELECT 1")).scalar()
        
        # 2. Bounded tenant count ping
        try:
            tenant_count = session.execute(text("SELECT count(*) FROM tenants")).scalar() or 0
        except Exception:
            tenant_count = 0

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    db_type = "sqlite" if _db_url.startswith("sqlite") else "postgres"

    result = {
        "ok": True,
        "timestamp": now_iso,
        "latency_ms": latency_ms,
        "database_type": db_type,
        "tenant_count": tenant_count,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Supabase Keep-Alive Heartbeat Utility")
    parser.add_argument("--once", action="store_true", help="Run a single keep-alive ping and exit")
    parser.add_argument("--interval-hours", type=float, default=6.0, help="Interval between pings in daemon mode (default: 6)")
    args = parser.parse_args()

    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] Starting Supabase Keep-Alive heartbeat...")

    if args.once:
        try:
            res = ping_supabase()
            print(f"[SUCCESS] Database keep-alive OK | Type: {res['database_type']} | Latency: {res['latency_ms']}ms | Tenants: {res['tenant_count']}")
            return 0
        except Exception as e:
            print(f"[ERROR] Database keep-alive failed: {e}", file=sys.stderr)
            return 1

    # Daemon mode
    interval_sec = int(args.interval_hours * 3600)
    print(f"[INFO] Running in daemon mode. Pinging every {args.interval_hours} hours ({interval_sec}s)...")

    while True:
        try:
            res = ping_supabase()
            print(f"[{res['timestamp']}] Keep-alive OK | Latency: {res['latency_ms']}ms | DB: {res['database_type']}")
        except Exception as e:
            print(f"[{datetime.now(timezone.utc).isoformat()}] [ERROR] Keep-alive ping error: {e}", file=sys.stderr)

        time.sleep(interval_sec)


if __name__ == "__main__":
    sys.exit(main())
