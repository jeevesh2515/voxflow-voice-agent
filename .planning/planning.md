# Project Planning Document: VoxFlow Voice Agent v1.0 (V0 Text State Machine)

This planning document outlines the implementation specifications, architecture changes, and roadmaps to build a **text-only state machine prototype (v0)** of the VoxFlow agent. By simulating the voice flow as a text chat first, we prove our intent-routing, slot-filling, and database mechanics at near-zero cost, before deploying voice and telephony configurations.

---

## 1. V0 Prototype Call Flow State Machine

The conversational flow follows a structured transition loop using Llama 3.1 on Groq, routing context step-by-step:

```
[Start Session]
      │
      ▼
[1. Greet + Identify] <─── Check Caller ID / lookup_supplier
      │
      ▼
[2. Intent Classification] <─── Place PO / Stock Check / Shipment Status / Other
      │
      ▼
[3. Slot-Filling] <─── Extract SKU, Quantity, PO Number conversationally
      │
      ▼
[4. DB Action] ───> Read/Write PostgreSQL (Stock, Orders, Shipments)
      │
      ▼
[5. Confirm Verbal] <─── Read back details as TTS-ready response
      │
      ▼
[6. Log Everything] ───> Save full transcript & structured summaries to DB
      │
      ▼
[7. Fallback Gate] ───> Escalation flag if confidence or intent falls out-of-scope
```

---

## 2. Technical Stack Selection

- **Telephony (Phase 2):** Twilio.
- **Speech Integration (Phase 2):** Deepgram/Whisper (STT) + ElevenLabs/Azure Speech (TTS).
- **LLM Engine (Phase 1/2):** Groq Llama 3.1.
- **State Flow Manager (Phase 1):** LangGraph-inspired structured context machine.
- **Database (Phase 1):** Supabase (Postgres).

---

## 3. Database Schema

1. **`tenants`**: Scopes data to specific companies (e.g. Varun Beverages, Amul Dairy, Haldirams Snacks, Britannia).
2. **`suppliers`**: Scoped by `tenant_id`. Maps registered suppliers.
3. **`products`**: Stock SKU lists, mrp, and categories.
4. **`orders`**: Supplier purchase order registries.
5. **`shipments`**: Outbound delivery statuses and timelines.
6. **`appointments`**: Meeting slots scheduled via call.
7. **`worksheet_logs`**: Spreadsheet sync log audits.
8. **`communication_logs`**: Logs for emails and WhatsApp notifications.
9. **`calls`**: Detailed transcripts, intent analysis, and escalation flags.

---

## 4. Execution Phases

### Phase 1: Core V0 Text State Machine
- Configure PostgreSQL database schemas.
- Implement `state_machine.py` tracking conversation states.
- Support JSON text routes on the backend.
- Build Next.js text simulator with live State-debugging sidebar showing collected slots and transition phases.

### Phase 2: Core Voice Integration
- Layer `edge-tts` (or ElevenLabs) for text-to-speech rendering on the simulator client.
- Layer local Whisper STT (or Deepgram API) for speech-to-text recording.

### Phase 3: Telephony (Twilio integration)
- Expose Twilio Media Streams webhook to bridge live calls to the WebSocket audio server.
