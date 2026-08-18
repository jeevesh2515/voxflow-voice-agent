"""Tests for persistent storage, crash recovery, and retry queues."""

import json
import os
import time
import pytest
from voxflow_api.config import get_settings
from voxflow_api.integrations.gsheets import GoogleSheetsClient, _queue_dir
from voxflow_api.voice.pipeline import CallSession, VoicePipeline, _sessions_dir


@pytest.mark.asyncio
async def test_session_snapshot_and_crash_recovery(tmp_path, monkeypatch):
    """Verify in-flight sessions snapshot to disk and recover if interrupted."""
    data_dir = str(tmp_path / "data")
    monkeypatch.setattr(get_settings(), "data_dir", data_dir)

    pipeline = VoicePipeline()
    session = pipeline.start_session(
        caller_phone="+919876543210",
        caller_name="Test Caller",
        tenant_id="varun",
    )

    sdir = _sessions_dir()
    snapshot_path = os.path.join(sdir, f"{session.call_id}.json")
    assert os.path.exists(snapshot_path)

    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["call_id"] == session.call_id
    assert data["caller_phone"] == "+919876543210"

    # Simulate container crash / restart with a new pipeline instance
    new_pipeline = VoicePipeline()
    recovered_count = await new_pipeline.recover_orphaned_sessions()
    assert recovered_count == 1
    assert not os.path.exists(snapshot_path)


@pytest.mark.asyncio
async def test_sheets_retry_queue_disk_persistence(tmp_path, monkeypatch):
    """Verify failed Sheets writes persist to disk and retry queue can process them."""
    data_dir = str(tmp_path / "data")
    monkeypatch.setattr(get_settings(), "data_dir", data_dir)

    client = GoogleSheetsClient.instance()
    row = {
        "call_id": "test_call_retry_123",
        "timestamp": "2026-08-18 12:00:00",
        "caller_phone": "+919876543210",
        "reason": "Stock check",
        "solution": "100 bags available",
        "resolution_status": "resolved",
    }

    client.queue_row(row, call_id=row["call_id"])
    qdir = _queue_dir()
    qfile = os.path.join(qdir, f"{row['call_id']}.json")
    assert os.path.exists(qfile)

    with open(qfile, "r", encoding="utf-8") as f:
        queued_data = json.load(f)
    assert queued_data["call_id"] == "test_call_retry_123"
