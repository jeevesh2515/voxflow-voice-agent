"""Guards the Postgres code path, which the rest of the suite never touches.

Why this file exists
--------------------
`conftest.py` points every other test at SQLite, and SQLite needs no driver at
all. That made an entire class of bug invisible: the suite stayed green at 86/86
while the application could not start against Supabase.

The specific failure: `db.py` builds a **synchronous** engine at module import
(the dashboard REST routes in `routes/data.py` are sync), and SQLAlchemy imports
the DBAPI eagerly during engine construction. `requirements.txt` declared
`asyncpg` for the async engine but no sync Postgres driver, so importing
`voxflow_api.db` against a `postgresql://` URL raised
`ModuleNotFoundError: No module named 'psycopg2'`.

Every module imports `db`, so the whole app died at startup — and because the
crash happened at *import* time, even `python -m voxflow_api.selftest` produced
no output at all, which made it look like the command itself was broken.

These tests construct engines without ever connecting, so they need no database.
"""

from __future__ import annotations

import importlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine


PG_URL = "postgresql://user:pw@db.example.supabase.co:5432/postgres"


# ── the drivers must actually be installed ─────────────────────────────────


@pytest.mark.parametrize(
    "module,why",
    [
        ("psycopg2", "SYNC Postgres driver — routes/data.py and CLI scripts"),
        ("asyncpg", "ASYNC Postgres driver — agent tools"),
        ("aiosqlite", "ASYNC SQLite driver — tests and local dev"),
    ],
)
def test_required_database_driver_is_installed(module: str, why: str):
    """A driver missing from requirements.txt is a production outage, not a warning."""
    try:
        importlib.import_module(module)
    except ModuleNotFoundError:  # pragma: no cover
        pytest.fail(
            f"{module} is not installed ({why}).\n"
            f"Add it to apps/api/requirements.txt. Without it the app cannot "
            f"start against Postgres, even though every SQLite test passes."
        )


# ── engines must be constructible for the URLs we actually deploy with ─────


def test_sync_engine_can_be_created_for_postgres():
    """This is the exact call in db.py that failed in production."""
    engine = create_engine(PG_URL, echo=False, future=True)
    assert engine.url.drivername == "postgresql"
    assert engine.dialect.driver == "psycopg2"


def test_async_engine_can_be_created_for_postgres():
    engine = create_async_engine(PG_URL.replace("postgresql://", "postgresql+asyncpg://"))
    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.dialect.driver == "asyncpg"


def test_sqlite_engines_still_work():
    """The dev/test path must keep working alongside Postgres."""
    sync = create_engine("sqlite:///./_driver_probe.db", future=True)
    assert sync.dialect.driver == "pysqlite"
    a = create_async_engine("sqlite+aiosqlite:///./_driver_probe.db")
    assert a.dialect.driver == "aiosqlite"


# ── the URL rewriting in db.py must produce drivers that exist ─────────────


def test_async_url_rewrite_targets_installed_drivers():
    """db.py rewrites the configured URL for the async engine. If it rewrites to
    a driver nobody installed, the app dies at import."""
    from voxflow_api.db import _async_db_url

    assert _async_db_url(PG_URL) == PG_URL.replace("postgresql://", "postgresql+asyncpg://")
    assert _async_db_url("sqlite:///./x.db") == "sqlite+aiosqlite:///./x.db"

    # And each rewritten URL must actually be constructible.
    for original in (PG_URL, "sqlite:///./_driver_probe.db"):
        create_async_engine(_async_db_url(original))


def test_pooler_rewrite_keeps_a_valid_url():
    """SUPABASE_USE_POOLER swaps host and port; the result must still parse."""
    from voxflow_api.config import get_settings
    from voxflow_api.db import _pooled_url

    s = get_settings()
    original = s.supabase_use_pooler
    try:
        object.__setattr__(s, "supabase_use_pooler", True)
        pooled = _pooled_url(PG_URL)
        assert ":6543/" in pooled
        assert "pooler.supabase.co" in pooled
        create_engine(pooled, future=True)  # must still be a valid URL
    finally:
        object.__setattr__(s, "supabase_use_pooler", original)


# ── the whole app must import against Postgres, not just SQLite ────────────


def test_full_app_imports_against_a_postgres_url(monkeypatch, tmp_path):
    """End-to-end guard on the actual regression.

    Spawns a fresh interpreter with DATABASE_URL pointing at Postgres and
    imports the FastAPI app. A subprocess is required because `db.py` builds its
    engines at import time and the module is already loaded in this process with
    SQLite.
    """
    import subprocess
    import sys

    code = (
        "from voxflow_api.main import create_app\n"
        "app = create_app()\n"
        "assert len(app.routes) > 5\n"
        "print('OK')\n"
    )
    env = {
        "PATH": "/usr/bin:/bin",
        "DATABASE_URL": PG_URL,
        "LLM_PROVIDER": "groq",
        "GROQ_API_KEY": "test",
        "SHEETS_ENABLED": "false",
        "TWILIO_VALIDATE_SIGNATURE": "false",
        "PYTHONPATH": str(__import__("pathlib").Path(__file__).resolve().parent.parent),
    }
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=120
    )
    assert result.returncode == 0, (
        "The app failed to import against a Postgres URL — this is the bug that "
        f"took production down.\nstdout: {result.stdout}\nstderr: {result.stderr[-1500:]}"
    )
    assert "OK" in result.stdout


def test_missing_driver_produces_an_actionable_error():
    """An opaque `No module named 'psycopg2'` cost hours of debugging.

    The hint must name both drivers and tell you how to fix it.
    """
    from voxflow_api.db import _driver_hint

    hint = _driver_hint(PG_URL, ModuleNotFoundError("No module named 'psycopg2'"))
    assert "psycopg2" in hint
    assert "asyncpg" in hint
    assert "requirements.txt" in hint
    assert "SYNC" in hint and "ASYNC" in hint
