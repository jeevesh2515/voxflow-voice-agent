# Phase 3 — Voice Integration (Day 9–12)

Only start this once Phase 2's Definition of Done is fully met. If the
text agent is shaky, voice will make debugging much harder, not easier.

## Day 9

### Theory

Twilio Voice works by receiving a webhook when a call comes in, to which
your server responds with TwiML (or, for streaming, opens a WebSocket via
Twilio Media Streams for real-time audio in/out). For a conversational
agent, Media Streams (WebSocket) is the right approach over simple
TwiML `<Gather>` loops, since it allows continuous audio streaming instead
of turn-based prompts.

### Checklist

- [ ] Buy/configure a Twilio number (trial number is fine for now)
- [ ] Set up a webhook endpoint in FastAPI that Twilio calls on incoming
      call
- [ ] Get a basic Twilio Media Stream connected to a WebSocket endpoint in
      your FastAPI app — confirm you're receiving raw audio frames
- [ ] Confirm you can send audio back (even just a test "hello" TTS clip)
      and hear it on the actual call

### Definition of Done

You can call your Twilio number and hear a pre-recorded/test TTS message
played back — proving the full audio path (call → your server → audio
out) works, before any STT/LLM/agent logic is wired in.

## Day 10

### Theory

Streaming STT (Deepgram or Whisper streaming) needs to handle
turn-taking: detecting when the caller has finished speaking (end-of-
utterance) before sending the transcript to your agent. Getting this
wrong causes the agent to respond mid-sentence or wait too long.

### Checklist

- [ ] Wire the incoming audio stream to your chosen STT provider
- [ ] Implement basic end-of-utterance detection (silence threshold or
      provider's built-in VAD/endpointing)
- [ ] Log transcripts to console and confirm accuracy on a handful of
      test calls to yourself, including some Hindi/English code-switching
      if that's realistic for your use case

### Definition of Done

Speaking a test sentence on a call produces a correct (or near-correct)
transcript in your logs within an acceptable delay (~1–2 sec).

## Day 11

### Theory

This is where Phase 2's text agent gets connected — the STT transcript
becomes the input to the same LangGraph agent, and the agent's text
response goes to TTS instead of a chat UI. If Phase 2 was solid, this
step should mostly be plumbing.

### Checklist

- [ ] Feed STT output into the Phase 2 LangGraph agent as if it were a
      chat message
- [ ] Feed the agent's response into your TTS provider, stream the audio
      back over the same call
- [ ] Run one full end-to-end voice call: greet → identify → intent →
      slot-fill → execute → confirm

### Definition of Done

A real phone call to your Twilio number completes one full scenario
(e.g. check stock for a known SKU) entirely by voice, correctly.

## Day 12

### Theory

Real calls are messier than test calls — background noise, interruptions,
people talking over the agent, unclear audio. Barge-in handling (letting
the caller interrupt the agent mid-sentence) is a nice-to-have, not a
requirement for v1 — don't over-invest here yet.

### Checklist

- [ ] Test with a few different real people calling in (friends/family),
      not just yourself — different accents, phone qualities
- [ ] Log every failure mode you observe (misheard word, wrong intent,
      awkward pause, etc.)
- [ ] Fix the highest-frequency failure only — don't try to fix everything
      today

### Definition of Done

At least 3 different people have completed a real test call successfully,
and you have a written list of observed failure modes for later
prioritization.
