# Day 1: Conversational State Machines & V0 Text Chat Prototyping

Welcome to the VoxFlow developer training program. This guide covers the theoretical foundations and implementation blueprints for building structured conversational state machines (v0 text-only) using Llama 3.1 on Groq.

---

## 1. Theoretical Foundation

### A. State Machine vs. Free-form Chats

In standard chat applications, context flows freely, which often leads to unpredictability in commercial workflows (e.g. placing purchase orders, checking inventory). For reliable voice automation, we structure the conversation as a state machine:

1. **Greet & Identify:** Read the caller ID (phone number), check the database for a matching supplier, and retrieve company metadata.
2. **Intent Classification:** Map the caller's request to a supported intent (PO creation, stock lookup, shipment check, appointment schedule, note dictation).
3. **Slot-Filling:** Extract crucial parameters (SKUs, quantities, dates) conversationally. If any slot is missing, prompt for it instead of executing.
4. **Action Execution:** Read or write data from/to PostgreSQL once all slots are satisfied.
5. **Confirmation:** Synthesize a clear verification statement summarizing the action taken.
6. **Fallback/Escalation:** Transition to a safe fallback state if the user's intent is unclear or out of scope, flagging the call for human intervention.

### B. Prototyping First via Text (V0)

Speech-to-text (STT) and text-to-speech (TTS) introduce network delays, audio jitter, and transcription errors. Debugging these concurrently with conversational logic makes development slow. 
By building a **text-only state machine (v0)** first:
- Debugging is instant via standard text console or chat box.
- Tool execution, slot filling, and DB write actions can be proven 100% correct first.
- Voice/telephony capabilities can be layered on top later as simple input/output encoders.

---

## 2. State Transition Spec

```python
class AgentState:
    GREET = "greet"
    IDENTIFY = "identify"
    INTENT_ROUTE = "intent_route"
    SLOT_FILL = "slot_fill"
    CONFIRM = "confirm"
    ESCALATE = "escalate"
```

The system manages the state machine dynamically. For example, during a Place PO intent:
- **State: GREET/IDENTIFY** -> Caller says: *"This is Ramesh from Amul."* -> System queries Amul Dairy supplier records.
- **State: INTENT_ROUTE** -> Caller says: *"I want to order some butter cases."* -> System maps to `create_po` intent.
- **State: SLOT_FILL** -> System prompts: *"Sure, what pack size and quantity do you need?"* -> User: *"Send 50 cases of Amul Butter 500g."* -> System extracts `sku="BUTTER-500G"`, `quantity=50`.
- **State: CONFIRM** -> System writes order to DB, sends WhatsApp invoice, and confirms: *"I have placed PO-12345 for 50 cases. Is there anything else?"*

---

## 3. Daily Implementation Exercises

### Step 1: Database Migration
Modify `apps/api/voxflow_api/db.py` to support multi-tenant structures (`tenants`, `appointments`, `worksheet_logs`, `communication_logs`).

### Step 2: Implement `state_machine.py`
Create the transition engine in `apps/api/voxflow_api/agent/state_machine.py` to route conversations based on session context.

### Step 3: Connect Text WebSockets
Update `apps/api/voxflow_api/routes/ws.py` to receive text payloads and return structured JSON state details to the chat client.
