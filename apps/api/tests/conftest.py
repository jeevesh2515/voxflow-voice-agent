"""Shared test configuration.

`get_settings()` is `lru_cache`d, so the very first import of `voxflow_api`
freezes configuration for the whole session. Setting these in individual test
modules is unreliable — whichever module pytest imports first wins. conftest
runs before any test module is imported, so this is the only place these can
live.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Deterministic, fully offline test configuration.
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("DATABASE_URL", "sqlite:///./voxflow_test.db")

# Most tests post unsigned requests to /twilio/voice. The signature tests turn
# validation back on explicitly for themselves.
os.environ.setdefault("TWILIO_VALIDATE_SIGNATURE", "false")

# STT/Sheets must never reach the network during tests.
os.environ.setdefault("STT_PROVIDER", "groq")
os.environ.setdefault("GROQ_API_KEY", "test-key-never-used")
os.environ.setdefault("SHEETS_ENABLED", "false")

# Day 35 production defaults enforce a fail-closed pilot admission gate. Legacy
# Day 25–34 fixtures intentionally exercise their historical policy contracts,
# so dedicated Day 35 tests toggle this back on with an isolated Settings cache.
os.environ.setdefault("PILOT_READINESS_ENFORCED", "false")
