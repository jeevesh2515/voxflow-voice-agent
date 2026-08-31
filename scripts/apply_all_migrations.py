"""Apply all ordered migrations to the configured PostgreSQL database."""
from __future__ import annotations

import os
from pathlib import Path
from sqlalchemy import create_engine, text

from voxflow_api.config import get_settings


def apply_migrations():
    settings = get_settings()
    db_url = settings.database_url
    print(f"Connecting to database: {db_url.split('@')[-1] if '@' in db_url else db_url}")

    engine = create_engine(db_url)
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    for sql_file in migration_files:
        print(f"Applying migration: {sql_file.name} ...")
        content = sql_file.read_text(encoding="utf-8")
        try:
            with engine.begin() as conn:
                conn.execute(text(content))
            print(f"  ✓ {sql_file.name} applied successfully.")
        except Exception as exc:
            print(f"  ⚠ {sql_file.name} notice/error: {exc}")


if __name__ == "__main__":
    apply_migrations()
