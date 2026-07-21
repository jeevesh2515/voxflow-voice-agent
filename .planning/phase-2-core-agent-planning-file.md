# Phase 2 — Core Conversation Agent, Text-Only (Day 5–8)

This is the most important phase. Do not touch Twilio, STT, or TTS until
this works reliably as a text chat. Voice adds latency and transcription
noise on top of whatever logic bugs exist here — isolate them first.

## Day 5

### Theory

A LangGraph state machine for this use case needs at minimum these nodes:
identify caller → classify intent → slot-fill → execute (DB read/write) →
confirm → log. Model it as an explicit graph, not a single giant prompt —
this is what makes it debuggable and what makes escalation/fallback
possible at any step.

### Checklist

- [ ] Sketch the LangGraph graph on paper: nodes, edges, and what state
      is carried between them (caller_id, intent, entities, db_result,
      confidence)
- [ ] Set up the LangGraph project skeleton with Groq as the LLM backend
      (reuse config pattern from ExpertIQ if you have it saved)
- [ ] Implement the "identify caller" node: given a phone number (or typed
      ID for now), look up `suppliers` table, return match or "unknown"

### Definition of Done

Given a fake phone number, the graph correctly identifies a known supplier
or reports "unknown caller" — testable via a simple Python script, no
UI needed yet.

## Day 6

### Theory

Intent classification for a narrow domain (PO / stock check / shipment
status / other) is much more reliable with structured function-calling
than free-text classification. Define the intents as a fixed enum/schema
and have the LLM select one via tool-calling, not raw text parsing.

### Checklist

- [ ] Define the intent schema (structured output / function call):
      `place_order`, `check_stock`, `check_shipment`, `other`
- [ ] Implement the "classify intent" node using Groq structured output/
      tool calling
- [ ] Test with 10+ varied sample utterances per intent, including
      ambiguous ones, and check the classification holds up
- [ ] Log every misclassification you find — these become test cases

### Definition of Done

A test script with 40+ sample utterances (10 per intent) classifies
correctly at least 80% of the time on first pass; failures are logged
for iteration, not ignored.

## Day 7

### Theory

Slot-filling means extracting structured entities (SKU, quantity, PO
number) from natural conversation, potentially across multiple turns if
the caller doesn't give everything at once. The agent needs to know what's
still missing and ask for it — not assume or guess a value.

### Checklist

- [ ] Implement slot-filling node per intent (different required fields
      for place_order vs check_stock vs check_shipment)
- [ ] Implement a "missing slot" loop: if a required field is missing,
      the agent asks a follow-up question instead of proceeding
- [ ] Test multi-turn scenarios: caller gives partial info, agent asks,
      caller completes it

### Definition of Done

A multi-turn text conversation (5+ exchanges) correctly fills all required
slots for at least one full "place an order" scenario without the agent
proceeding on incomplete data.

## Day 8

### Theory

The execute → confirm → log sequence is where correctness matters most —
this is the actual business value (accurate data, not guesses). Confidence
thresholds should gate any DB write: if the agent isn't confident about
an extracted value, it should ask for confirmation before writing, not
after.

### Checklist

- [ ] Implement the "execute" node: query/write to Supabase based on
      filled slots (e.g. check_stock → SELECT, place_order → INSERT
      pending order)
- [ ] Implement "confirm" node: agent reads back what it found/did in
      plain language before finalizing any write
- [ ] Implement "log" node: write full transcript + structured summary
      to `call_logs`
- [ ] Implement fallback: if confidence is low at classify or slot-fill
      stage, agent says it'll escalate to a human, logs as `escalated`,
      does not attempt a DB write

### Definition of Done

Run 3 full end-to-end text conversations (one per intent) that correctly
read/write data and produce a correct `call_logs` row each. Run 1
deliberately confusing conversation and confirm it escalates instead of
guessing.
