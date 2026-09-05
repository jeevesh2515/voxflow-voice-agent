#!/usr/bin/env python3
"""Verify the live database schema matches the ORM + migration DDL.

Read-only. Creates nothing, alters nothing, drops nothing.

The ORM (`Base.metadata`) is this project's schema source of truth —
`voxflow_api.gen_schema` emits `migrations/000_base_schema.sql` from it and
`tests/test_schema_sql.py` fails CI on drift. So parity means: every table and
column the ORM declares exists in the live database. Tables added by the later
numbered migrations are checked too, parsed straight from their
`CREATE TABLE IF NOT EXISTS <name>` statements.

Extra objects in the live database are reported but are not failures: Supabase
ships its own schemas, and a migration may legitimately add a column the ORM
does not model.

Usage:
  python scripts/verify_schema_parity.py            # uses DATABASE_URL
  python scripts/verify_schema_parity.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_DIR = REPO_ROOT / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

# The ORM must not open a session on import, and config must not treat this as a
# test run, so DATABASE_URL is read as-is from the environment.
from sqlalchemy import create_engine, inspect  # noqa: E402

from voxflow_api.db import Base  # noqa: E402

_CREATE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"']?(\w+)[\"']?",
    re.IGNORECASE,
)


def migration_tables() -> dict[str, str]:
    """Map table name -> migration file that creates it."""
    found: dict[str, str] = {}
    for sql_file in sorted((REPO_ROOT / "migrations").glob("*.sql")):
        for name in _CREATE_TABLE.findall(sql_file.read_text(encoding="utf-8")):
            found.setdefault(name.lower(), sql_file.name)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify live schema parity (read-only)")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        try:
            from dotenv import load_dotenv
            load_dotenv(REPO_ROOT / ".env")
            db_url = os.environ.get("DATABASE_URL", "").strip()
        except ImportError:
            pass

    if not db_url:
        print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
        return 2

    redacted = re.sub(r"(://[^:]+:)[^@]+(@)", r"\1***\2", db_url)
    dialect = "postgres" if db_url.startswith(("postgres", "postgresql")) else "sqlite"

    engine = create_engine(db_url)
    inspector = inspect(engine)
    live_tables = {name.lower() for name in inspector.get_table_names()}

    missing_tables: list[str] = []
    missing_columns: dict[str, list[str]] = {}

    for table in Base.metadata.sorted_tables:
        name = table.name.lower()
        if name not in live_tables:
            missing_tables.append(name)
            continue
        live_cols = {c["name"].lower() for c in inspector.get_columns(table.name)}
        absent = sorted(c.name.lower() for c in table.columns if c.name.lower() not in live_cols)
        if absent:
            missing_columns[name] = absent

    orm_names = {t.name.lower() for t in Base.metadata.sorted_tables}
    mig_tables = migration_tables()
    missing_migration_tables = {
        name: src for name, src in sorted(mig_tables.items())
        if name not in live_tables and name not in orm_names
    }

    ok = not missing_tables and not missing_columns and not missing_migration_tables

    report = {
        "ok": ok,
        "database": redacted,
        "dialect": dialect,
        "live_table_count": len(live_tables),
        "orm_table_count": len(orm_names),
        "migration_declared_tables": len(mig_tables),
        "missing_orm_tables": sorted(missing_tables),
        "missing_orm_columns": missing_columns,
        "missing_migration_tables": missing_migration_tables,
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if ok else 1

    print(f"Database : {redacted}")
    print(f"Dialect  : {dialect}")
    print(f"Live tables            : {len(live_tables)}")
    print(f"ORM-declared tables    : {len(orm_names)}")
    print(f"Migration-declared     : {len(mig_tables)}")
    print("-" * 62)

    if missing_tables:
        print(f"MISSING ORM TABLES ({len(missing_tables)}):")
        for name in sorted(missing_tables):
            print(f"  - {name}")
    if missing_columns:
        total = sum(len(v) for v in missing_columns.values())
        print(f"MISSING ORM COLUMNS ({total}):")
        for table, cols in sorted(missing_columns.items()):
            print(f"  - {table}: {', '.join(cols)}")
    if missing_migration_tables:
        print(f"MISSING MIGRATION TABLES ({len(missing_migration_tables)}):")
        for name, src in missing_migration_tables.items():
            print(f"  - {name}  (from {src})")

    if ok:
        print("PARITY OK — every ORM and migration table/column is present in the live database.")
    else:
        print("PARITY FAILED — apply the missing migrations before relying on this database.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
