#!/usr/bin/env python3
"""Automated GDPR Data Retention & Transcript Purge CLI / Cron Runner.

Usage:
    # Run purge for all tenants (standard daily cron)
    python3 scripts/run_retention_purge.py --all-tenants

    # Dry-run purge to inspect records that would be scrubbed
    python3 scripts/run_retention_purge.py --all-tenants --dry-run

    # Run for a specific tenant
    python3 scripts/run_retention_purge.py --tenant-id varun
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Ensure apps/api is in Python path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_PATH = os.path.join(REPO_ROOT, "apps", "api")
if API_PATH not in sys.path:
    sys.path.insert(0, API_PATH)

from voxflow_api.db import session_scope
from voxflow_api.services.retention_service import run_retention_purge


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="VoxFlow Automated Data Retention & Transcript Purge Runner",
    )
    parser.add_argument(
        "--tenant-id",
        type=str,
        default=None,
        help="Target specific tenant ID (default: all tenants)",
    )
    parser.add_argument(
        "--all-tenants",
        action="store_true",
        help="Explicitly run retention purge across all registered tenants",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview purge counts without committing deletions or anonymizations",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output structured JSON results for monitoring pipelines",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.tenant_id and not args.all_tenants:
        print("Error: Specify either --tenant-id <id> or --all-tenants", file=sys.stderr)
        return 1

    mode_label = "DRY-RUN (Preview)" if args.dry_run else "LIVE PURGE"
    if not args.json_output:
        print(f"🔒 VoxFlow Data Retention & GDPR Purge — {mode_label}")
        print(f"   Target: {'Tenant: ' + args.tenant_id if args.tenant_id else 'All Active Tenants'}")

    try:
        with session_scope() as db:
            result = run_retention_purge(
                db=db,
                tenant_id=args.tenant_id,
                dry_run=args.dry_run,
                triggered_by_user_id="system_cron",
                execution_type="automated_cron",
            )

        if args.json_output:
            print(json.dumps(result, indent=2))
        else:
            print("\n Execution Summary:")
            print(f"   • Records Scanned:       {result.get('records_scanned', 0)}")
            print(f"   • Transcripts Purged:    {result.get('transcripts_purged', 0)}")
            print(f"   • Calls Anonymized:      {result.get('calls_anonymized', 0)}")
            print(f"   • Execution Type:        {result.get('execution_type', 'automated_cron')}")
            print(f"   • Dry Run Mode:          {result.get('dry_run', False)}")
            print("\n Retention purge completed successfully.")

        return 0
    except Exception as exc:
        print(f"❌ Error during retention purge: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
