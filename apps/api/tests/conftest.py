"""Shared test configuration.

`get_settings()` is `lru_cache`d, so the very first import of `voxflow_api`
freezes configuration for the whole session. Setting these in individual test
modules is unreliable — whichever module pytest imports first wins. conftest
runs before any test module is imported, so this is the only place these can
live.
"""

from __future__ import annotations

import glob
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Deterministic, fully offline test configuration.
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("DATABASE_URL", "sqlite:///./voxflow_test.db")
# Session recovery writes snapshots under DATA_DIR. Give every pytest process an
# isolated directory so a prior local simulator run cannot change test results.
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="voxflow-test-data-"))

# STT/Sheets must never reach the network during tests.
os.environ.setdefault("STT_PROVIDER", "groq")
os.environ.setdefault("GROQ_API_KEY", "test-key-never-used")
os.environ.setdefault("SHEETS_ENABLED", "false")

# Day 35 production defaults enforce a fail-closed pilot admission gate. Legacy
# Day 25–34 fixtures intentionally exercise their historical policy contracts,
# so dedicated Day 35 tests toggle this back on with an isolated Settings cache.
os.environ.setdefault("PILOT_READINESS_ENFORCED", "false")

# Legacy endpoint tests predate the tenant_members ledger. New authorization
# tests explicitly enable the production-default fail-closed gate and supply a
# verified identity plus active membership fixture.
os.environ.setdefault("TENANT_AUTHORIZATION_ENFORCED", "false")


@pytest.fixture(autouse=True)
def _clear_leaked_session_snapshots():
    """Isolate every test from disk session snapshots left by earlier tests.

    Sessions started via the API/Connect endpoints snapshot to DATA_DIR/sessions
    for crash recovery. That directory is shared across the whole pytest process,
    and `reset_db()` clears only database tables — not these files. Any test that
    then starts the app recovers those stale snapshots and persists them as calls
    under the default tenant, inflating counts (e.g. analytics total_calls). In
    production this recovery is a feature; in tests it is cross-test leakage.

    Clearing at setup makes tests order-independent without touching product code.
    Tests that monkeypatch `data_dir`/`_sessions_dir` to a tmp_path are unaffected:
    they write and recover their own snapshots inside the test body, after this runs.
    """
    from voxflow_api.voice.pipeline import _sessions_dir

    sdir = _sessions_dir()
    for snapshot in glob.glob(os.path.join(sdir, "*.json")):
        try:
            os.remove(snapshot)
        except OSError:
            pass
    yield
