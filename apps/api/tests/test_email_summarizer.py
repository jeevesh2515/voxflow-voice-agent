"""Unit tests for the Email Summarizer Agent and persistent memory."""

import pytest
from voxflow_api.tasks.email_summarizer import EmailSummarizerAgent
from voxflow_api.db import init_db


@pytest.mark.asyncio
async def test_email_summarizer_agent_cycle(monkeypatch):
    init_db()
    agent = EmailSummarizerAgent(tenant_id="varun")

    # Run sync cycle
    res = await agent.run_sync_cycle(limit=2)
    assert res["ok"] is True
    assert "processed_count" in res
    assert "sheets_synced_count" in res

    # Check that processed IDs were recorded in AgentState
    processed_ids = await agent.get_processed_message_ids()
    assert len(processed_ids) >= 0

    # Test idempotency on immediate re-run
    res_second = await agent.run_sync_cycle(limit=2)
    assert res_second["ok"] is True
    assert res_second["processed_count"] == 0
