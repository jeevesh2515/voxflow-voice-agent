"""Day 43 Tests — Latency Tuning, Groq 429 Resilience, VAD Silence Re-Prompts, and Encrypted Backups."""

from __future__ import annotations

import os
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from voxflow_api.config import get_settings
from voxflow_api.llm.base import ChatTurn
from voxflow_api.llm.groq import GroqProvider
from voxflow_api.main import create_app


# ============================================================================
# 1. Groq Client Connection Pooling & Jittered 429 Handling
# ============================================================================


@pytest.mark.asyncio
async def test_groq_client_reuse_and_pooling():
    """Verify that GroqProvider reuses its pooled HTTP client across calls."""
    provider = GroqProvider(api_key="gsk_test_123", model="openai/gpt-oss-20b")
    
    client1 = provider._get_client()
    assert isinstance(client1, httpx.AsyncClient)
    assert not client1.is_closed

    client2 = provider._get_client()
    assert client1 is client2, "GroqProvider should reuse the same persistent AsyncClient"

    await provider.close()
    assert client1.is_closed
    assert provider._client is None


@pytest.mark.asyncio
async def test_groq_429_backoff_and_jitter():
    """Verify jittered exponential backoff when Groq returns HTTP 429."""
    provider = GroqProvider(api_key="gsk_test_123", model="openai/gpt-oss-20b")

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.headers = {"retry-after": "0.01"}

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "id": "chatcmpl_test",
        "model": "openai/gpt-oss-20b",
        "choices": [
            {
                "message": {"role": "assistant", "content": "Stock for SKU 1001 is 45 units."},
                "finish_reason": "stop",
            }
        ],
    }

    mock_client = AsyncMock()
    mock_client.is_closed = False
    mock_client.post.side_effect = [mock_resp_429, mock_resp_200]

    turns = [ChatTurn(role="user", content="Check stock")]
    with patch.object(provider, "_get_client", return_value=mock_client), patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        resp = await provider.chat(turns)

        assert resp.content == "Stock for SKU 1001 is 45 units."
        assert mock_sleep.called
        assert mock_client.post.call_count == 2


@pytest.mark.asyncio
async def test_groq_fallback_model_activation():
    """Verify fallback to secondary model when primary model hits capacity/rate-limits."""
    provider = GroqProvider(
        api_key="gsk_test_123",
        model="openai/gpt-oss-20b",
        fallback_model="llama-3.1-8b-instant",
    )

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.headers = {"retry-after": "0.01"}

    mock_resp_fallback = MagicMock()
    mock_resp_fallback.status_code = 200
    mock_resp_fallback.json.return_value = {
        "id": "chatcmpl_fallback",
        "model": "llama-3.1-8b-instant",
        "choices": [
            {
                "message": {"role": "assistant", "content": "Fallback response from Llama 3.1"},
                "finish_reason": "stop",
            }
        ],
    }

    mock_client = AsyncMock()
    mock_client.is_closed = False
    # 3 retries on primary -> failure, then 1 call on fallback model -> success
    mock_client.post.side_effect = [
        mock_resp_429,
        mock_resp_429,
        mock_resp_429,
        mock_resp_fallback,
    ]

    turns = [ChatTurn(role="user", content="Check status")]
    with patch.object(provider, "_get_client", return_value=mock_client), patch("asyncio.sleep", new_callable=AsyncMock):
        resp = await provider.chat(turns)

        assert resp.content == "Fallback response from Llama 3.1"
        assert resp.model == "llama-3.1-8b-instant"


# ============================================================================
# 2. Progressive VAD Silence / Input Timeout Re-Prompting
# ============================================================================


def test_progressive_silence_reprompts(monkeypatch):
    """Verify progressive re-prompting and eventual termination on consecutive silence turns."""
    monkeypatch.setattr(get_settings(), "connect_lambda_secret", "", raising=False)
    app = create_app()
    client = TestClient(app)

    contact_id = "test_silence_call_001"

    # Turn 1: initial empty speech -> Welcome / greeting re-prompt
    res1 = client.post(
        "/api/connect/turn",
        json={
            "contact_id": contact_id,
            "customer_phone": "+447700900123",
            "system_phone": "+442046404552",
            "user_text": "",
            "language": "en",
        },
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert "Hello, this is the VoxFlow voice assistant" in data1["agent_reply"]
    assert data1["end_call"] is False

    # Turn 2: consecutive silence -> "Are you still there?" or clarification re-prompt
    res2 = client.post(
        "/api/connect/turn",
        json={
            "contact_id": contact_id,
            "customer_phone": "+447700900123",
            "system_phone": "+442046404552",
            "user_text": "   ",
            "language": "en",
        },
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert "I'm still here" in data2["agent_reply"] or "still there" in data2["agent_reply"]
    assert data2["end_call"] is False

    # Turn 3: third consecutive silence -> polite termination
    res3 = client.post(
        "/api/connect/turn",
        json={
            "contact_id": contact_id,
            "customer_phone": "+447700900123",
            "system_phone": "+442046404552",
            "user_text": "",
            "language": "en",
        },
    )
    assert res3.status_code == 200
    data3 = res3.json()
    assert "end the call for now" in data3["agent_reply"]
    assert data3["end_call"] is True


def test_silence_count_resets_on_spoken_turn(monkeypatch):
    """Verify that caller speaking resets the consecutive silence counter."""
    monkeypatch.setattr(get_settings(), "connect_lambda_secret", "", raising=False)
    app = create_app()
    client = TestClient(app)

    contact_id = "test_silence_reset_002"

    # 1. First silence
    client.post(
        "/api/connect/turn",
        json={
            "contact_id": contact_id,
            "customer_phone": "+447700900123",
            "system_phone": "+442046404552",
            "user_text": "",
            "language": "en",
        },
    )

    # 2. Spoken turn
    with patch("voxflow_api.agent.runner.AgentRunner.handle_turn") as mock_turn:
        from voxflow_api.agent.runner import AgentTurnResult

        mock_turn.return_value = AgentTurnResult(reply="I can check that stock item for you.")
        res_spoken = client.post(
            "/api/connect/turn",
            json={
                "contact_id": contact_id,
                "customer_phone": "+447700900123",
                "system_phone": "+442046404552",
                "user_text": "Hello, I need stock for item 1001",
                "language": "en",
            },
        )
        assert res_spoken.status_code == 200
        assert "check that stock" in res_spoken.json()["agent_reply"]

    # 3. New silence after spoken turn should be turn 1 silence re-prompt (not termination)
    res_silence = client.post(
        "/api/connect/turn",
        json={
            "contact_id": contact_id,
            "customer_phone": "+447700900123",
            "system_phone": "+442046404552",
            "user_text": "",
            "language": "en",
        },
    )
    assert res_silence.status_code == 200
    data_silence = res_silence.json()
    assert data_silence["end_call"] is False
    assert "Are you still there?" in data_silence["agent_reply"]


# ============================================================================
# 3. Supabase Keep-Alive & Encrypted Backups
# ============================================================================


def test_supabase_keepalive_ping():
    """Verify the Supabase keepalive ping function executes successfully."""
    import sys
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from scripts.supabase_keepalive import ping_supabase

    res = ping_supabase()
    assert res["ok"] is True
    assert "latency_ms" in res
    assert res["latency_ms"] >= 0.0
    assert "timestamp" in res


def test_encrypted_backup_and_restore_cycle(tmp_path):
    """Verify backup script creates encrypted archives and restore drill verifies integrity."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    backup_script = os.path.join(repo_root, "scripts", "db_backup.sh")
    restore_script = os.path.join(repo_root, "scripts", "db_restore_test.sh")

    env = os.environ.copy()
    env["DATA_DIR"] = str(tmp_path)
    env["BACKUP_ENCRYPTION_KEY"] = "unit-test-secret-key"
    env["DATABASE_URL"] = f"sqlite:///{tmp_path}/voxflow.db"

    # Create dummy database
    db_file = tmp_path / "voxflow.db"
    import sqlite3

    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE test_items (id INT, name TEXT);")
    conn.execute("INSERT INTO test_items VALUES (1, 'widget');")
    conn.commit()
    conn.close()

    # 1. Run backup
    backup_res = subprocess.run([backup_script], env=env, capture_output=True, text=True)
    assert backup_res.returncode == 0, f"db_backup.sh failed: {backup_res.stderr}"

    # Verify encrypted archive exists
    backups_dir = tmp_path / "backups"
    enc_files = list(backups_dir.glob("voxflow_*.enc"))
    assert len(enc_files) >= 1, "Expected encrypted backup file (.enc) in backups directory"

    # 2. Run restore verification drill
    restore_res = subprocess.run([restore_script], env=env, capture_output=True, text=True)
    assert restore_res.returncode == 0, f"db_restore_test.sh failed: {restore_res.stderr}"
    assert "Backup restore verification drill passed cleanly" in restore_res.stdout
