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
REPO_ROOT = ROOT.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO_ROOT))

# Deterministic, fully offline test configuration. Each pytest process receives
# a fresh database so schema state cannot leak between runs or working folders.
TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="voxflow-test-data-"))
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATA_DIR / 'voxflow_test.db'}"
os.environ["CONNECT_LAMBDA_SECRET"] = ""
os.environ["DATA_DIR"] = str(TEST_DATA_DIR)
os.environ["STT_PROVIDER"] = "groq"
os.environ["GROQ_API_KEY"] = "test-key-never-used"
os.environ["SHEETS_ENABLED"] = "false"
os.environ["PILOT_READINESS_ENFORCED"] = "false"
os.environ["TENANT_AUTHORIZATION_ENFORCED"] = "false"

from voxflow_api.config import get_settings  # noqa: E402
from voxflow_api.db import init_db  # noqa: E402

get_settings.cache_clear()
init_db()


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
