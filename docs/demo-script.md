# Demo script — VoxFlow Voice Agent

This is the script for the 5-minute live demo. Goal: show the agent handling a
real supplier call, end to end, in Hindi.

## Before the demo

```bash
# Terminal 1
cd apps/api && source .venv/bin/activate && uvicorn voxflow_api.main:app --reload

# Terminal 2
cd apps/web && npm run dev

# Open http://localhost:3000/dashboard/simulator
```

## The 5-minute run

1. **Open the dashboard** — show the operations overview, recent calls, pending orders. (30s)
2. **Open the phone simulator** — click the green phone to start the call. (15s)
3. **Type or speak the first prompt** (Hindi):

   > "नमस्ते, मैं राजेश बोल रहा हूँ, Shree Traders से। मुझे अपना शिपमेंट चेक करना है।"

   Vaani will look up the supplier, then ask for the order ID. (30s)

4. **Provide the order ID:**

   > "PO-1718000001-SHREE"

   Vaani calls `get_shipment_status`, replies with the carrier, status, and ETA in Hindi. (30s)

5. **Place a new order:**

   > "अच्छा, एक और चीज़ — मुझे 50 case Pepsi 250ml और 20 case 7UP 250ml ऑर्डर करना है।"

   Vaani will read back the items for confirmation, then ask "क्या मैं यह ऑर्डर बना दूँ?" (60s)

6. **Confirm:**

   > "हाँ, बना दो।"

   Vaani calls `create_po`, replies with the new order ID. (30s)

7. **Show the dashboard updates** — refresh `/dashboard/orders`. The new order is there. (30s)
8. **Show the call in the calls log** — the transcript + actions are saved. (30s)

## What to highlight

- The agent didn't make up anything — every fact came from a tool call.
- The transcript is bilingual: Hinglish input, Hindi output.
- The new PO is in the database immediately.
- Switching `LLM_PROVIDER=groq` in `.env` and restarting swaps the brain to a faster model with zero code changes.

## What NOT to demo

- Pricing exception → escalation: Vaani will refuse and route to a human. Worth showing only if asked.
- Disconnected mic / no audio: the text input box is a reliable fallback.
