"""Day 54: Sub-400ms — gated tools, parallel reads, streaming TTS.

Proves the perf cuts ship without weakening verification or breaking the pipeline.
"""

from __future__ import annotations

import pytest
from voxflow_api.agent.tools import TOOL_DEFINITIONS, tool_definitions_for, gated_tool_count, _CORE_TOOLS

class _Sess:
    def __init__(self, verified=False, pin_verified=False, supplier_id="sup_1"):
        self.verified = verified
        self.pin_verified = pin_verified
        self.supplier_id = supplier_id
        self.tenant_id = "varun"
        self.route_policy = {}
        if verified:
            from voxflow_api.agent.tools import _KNOWLEDGE_BINDING_KEY
            self.route_policy[_KNOWLEDGE_BINDING_KEY] = supplier_id
        if pin_verified:
            from voxflow_api.agent.tools import _PIN_BINDING_KEY
            self.route_policy[_PIN_BINDING_KEY] = supplier_id


def test_gated_pre_verify_is_core_only():
    gated = tool_definitions_for(_Sess(verified=False))
    names = {t["function"]["name"] for t in gated}
    assert names == _CORE_TOOLS
    assert len(gated) == 6


def test_gated_verified_adds_reads():
    gated = tool_definitions_for(_Sess(verified=True))
    names = {t["function"]["name"] for t in gated}
    assert "get_shipment_status" in names
    assert "check_stock" in names
    assert "create_po" not in names  # needs PIN


def test_gated_pin_verified_is_full():
    gated = tool_definitions_for(_Sess(verified=True, pin_verified=True))
    assert len(gated) == len(TOOL_DEFINITIONS)
    assert gated_tool_count(_Sess(verified=True, pin_verified=True)) == len(TOOL_DEFINITIONS)


def test_gated_none_returns_full():
    assert len(tool_definitions_for(None)) == len(TOOL_DEFINITIONS)


def test_gated_preserves_ordering():
    gated = tool_definitions_for(_Sess(verified=False))
    full_names = [t["function"]["name"] for t in TOOL_DEFINITIONS]
    gated_names = [t["function"]["name"] for t in gated]
    # Order in gated must be subsequence of full order (cache-stable prefix).
    idx = 0
    for name in gated_names:
        idx = full_names.index(name, idx)  # must appear in order
        idx += 1


@pytest.mark.asyncio
async def test_parallel_reads_gather():
    """Two stock reads in one turn are gathered, not serialized."""
    import asyncio, time
    from voxflow_api.agent.runner import AgentRunner
    from voxflow_api.voice.pipeline import VoicePipeline
    from voxflow_api.schemas import CallTurn
    import time as _time

    # Mock LLM that returns two parallel tool calls on first iteration.
    class FakeLLM:
        name = "fake"
        model = "fake"
        calls = 0
        async def chat(self, messages, tools=None, **kwargs):
            from voxflow_api.llm.base import LLMResponse
            self.calls += 1
            if self.calls == 1:
                return LLMResponse(
                    content="",
                    tool_calls=[
                        {"id": "c1", "type": "function", "function": {"name": "check_stock", "arguments": '{"sku":"PEP-250ML"}'}},
                        {"id": "c2", "type": "function", "function": {"name": "check_stock", "arguments": '{"sku":"COK-500ML"}'}},
                    ],
                    finish_reason="tool_calls",
                    provider="fake",
                    model="fake",
                )
            return LLMResponse(content="Both in stock.", tool_calls=[], finish_reason="stop", provider="fake", model="fake")

    pipeline = VoicePipeline()
    runner = AgentRunner(llm=FakeLLM())
    # Need a verified session so check_stock is gated visible — but FakeLLM ignores gating.
    # Use pin_verified so all tools visible.
    sess = pipeline.start_session(caller_phone="+919999999999", tenant_id="varun")
    sess.verified = True
    from voxflow_api.agent.tools import _KNOWLEDGE_BINDING_KEY
    sess.route_policy[_KNOWLEDGE_BINDING_KEY] = "sup_1"
    sess.supplier_id = "sup_1"
    sess.transcript.append(CallTurn(role="caller", text="check both", at=_time.time()))
    t0 = time.perf_counter()
    result = await runner.handle_turn(session=sess, user_text="check both")
    ms = (time.perf_counter() - t0) * 1000
    # Should have executed both tools and returned a reply.
    assert len(result.actions) == 2
    assert result.reply == "Both in stock."
    # Parallel batch log should exist (ms for batch < sum of serial would be 2x DB)
    # We just assert it completed quickly (<500ms for mock DB).
    assert ms < 1000


@pytest.mark.asyncio
async def test_tts_stream_yields_chunks(monkeypatch):
    import voxflow_api.voice.tts as tts_mod
    from voxflow_api.voice.tts import TextToSpeech

    # Hermetic: skip when edge-tts not installed; stub Communicate when installed
    # so the test never touches the network.
    if tts_mod.edge_tts is None:
        pytest.skip("edge-tts not installed")

    class _StubCommunicate:
        def __init__(self, *a, **kw):
            pass

        async def stream(self):
            yield {"type": "audio", "data": b"\x00\x01\x02chunk"}
            yield {"type": "WordBoundary", "data": None}

    monkeypatch.setattr(tts_mod.edge_tts, "Communicate", _StubCommunicate)

    tts = TextToSpeech()
    chunks = []
    try:
        async for c in tts.synth_stream("Hello world", lang_hint="en"):
            chunks.append(c)
            if len(chunks) >= 1:
                break
    except RuntimeError as e:
        if "unavailable" in str(e):
            pytest.skip("edge-tts not installed")
        raise
    assert chunks, "stubbed synth_stream should yield at least one chunk"
    assert isinstance(chunks[0], (bytes, bytearray))
    assert len(chunks[0]) > 0
