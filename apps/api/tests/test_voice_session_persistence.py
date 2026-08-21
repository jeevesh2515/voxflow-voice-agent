"""Regression tests for durable simulator session evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from voxflow_api.schemas import CallTurn
from voxflow_api.voice.pipeline import CallSession, _snapshot_session


def test_snapshot_serializes_datetime_turn_timestamp(monkeypatch, tmp_path):
    """A text-simulator turn uses datetime and must still leave recoverable evidence."""
    monkeypatch.setattr("voxflow_api.voice.pipeline._sessions_dir", lambda: str(tmp_path))
    session = CallSession(call_id="call_datetime_snapshot")
    session.transcript.append(
        CallTurn(
            role="caller",
            text="Check stock of cartons",
            at=datetime(2026, 8, 21, 4, 0, tzinfo=timezone.utc),
        )
    )

    _snapshot_session(session)

    snapshot = json.loads((tmp_path / "call_datetime_snapshot.json").read_text())
    assert snapshot["transcript"][0]["at"] == "2026-08-21T04:00:00+00:00"
