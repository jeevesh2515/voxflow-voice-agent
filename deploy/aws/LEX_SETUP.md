# Amazon Lex V2 (en-GB) — Speech Capture Setup

**Why this exists:** without a Lex bot, the contact flow can only capture DTMF keypad
presses (`$.StoredCustomerInput`). Anything the caller *says* is discarded, so the
voice agent never hears a word. Lex is the speech-to-text front door that fixes this.

**Lex is STT only.** VoxFlow's `AgentRunner` is the brain. Do not build intents that
drive business logic — the bot exists purely to hand a transcript to the Lambda.

Time: ~30 minutes in the AWS console. Cost: £0 (Lex V2 includes 5,000 speech
requests/month free for the first 12 months).

---

## 1. Create the bot

AWS Console → **Amazon Lex** → *Create bot*.

| Field | Value |
|---|---|
| Creation method | Create a blank bot |
| Bot name | `VoxFlowInbound` |
| IAM permissions | Create a role with basic Amazon Lex permissions |
| COPPA | No |
| Idle session timeout | 5 minutes |

Next page — language:

| Field | Value |
|---|---|
| Language | **English (UK)** |
| Voice interaction | `Amy` (matches the contact flow's Polly voice) |
| Intent classification confidence threshold | **0.40** |

The low threshold matters. A high threshold makes Lex discard speech it isn't
confident maps to an intent — but we *want* every utterance to fall through to the
fallback intent so the raw transcript survives.

## 2. Configure the fallback intent (this is the important part)

The bot is created with `NewIntent` and `FallbackIntent`.

1. Open **`FallbackIntent`**.
2. Leave it otherwise empty — no slots, no closing response. An empty fallback
   returns control to the contact flow with the transcript intact in
   `$.Lex.InputTranscript`.
3. Save.

Then open **`NewIntent`** and add one sample utterance so the bot will build —
e.g. `placeholder utterance do not use`. Do not add slots. Every real caller
sentence should miss this intent and land in the fallback, which is exactly what
we want.

> If you add slots or a closing response, Lex will try to hold the conversation
> itself and VoxFlow never gets the turn. Keep both intents inert.

## 3. Build, version, alias

1. **Build** the `English (UK)` locale. Wait for *Build complete*.
2. **Versions** → *Create version* → note the version number (e.g. `1`).
3. **Aliases** → *Create alias* → name it `prod`, point it at that version.
4. Open the `prod` alias and copy its **ARN**. It looks like:
   ```
   arn:aws:lex:us-west-2:123456789012:bot-alias/ABCDEFGHIJ/KLMNOPQRST
   ```

Region must match your Amazon Connect instance (`CONNECT_REGION`, default
`us-west-2`). A bot in another region cannot be attached to the instance.

## 4. Associate the bot with the Connect instance

Amazon Connect Console → your instance → **Flows** → *Amazon Lex* section →
**Add a bot**: pick `VoxFlowInbound`, alias `prod`, then *Add Amazon Lex Bot*.

Connect will not offer the bot in a flow until this association exists.

## 5. Wire the contact flow

`deploy/aws/connect-contact-flow.json` is already updated for Lex. Two placeholder
ARNs must be replaced with your real ones before import:

| Placeholder in the JSON | Replace with |
|---|---|
| `arn:aws:lex:us-west-2:YOUR_AWS_ACCOUNT_ID:bot-alias/YOUR_LEX_BOT_ID/YOUR_LEX_ALIAS_ID` | the `prod` alias ARN from step 3 |
| `arn:aws:lambda:us-west-2:YOUR_AWS_ACCOUNT_ID:function:VoxFlow-Connect-Bridge` | your Lambda function ARN |

Then: Connect Console → **Flows** → your inbound flow → *Save as / Import flow* →
upload the JSON → **Publish**.

What changed versus the old DTMF flow:

- `SetVoiceAction` — Polly voice `Amy`, `LanguageCode` `en-GB` (was `Aditi` / `hi-IN`).
- `GetCustomerSpeech` — now carries a `LexV2Bot.AliasArn`, so it listens for speech
  instead of keypresses. `InputTimeLimitSeconds` raised 5 → 8 to give a caller room
  to finish a sentence.
- `InvokeVoxFlowLambda` — `user_text` sources `$.Lex.InputTranscript`, not
  `$.StoredCustomerInput`.
- Blank/unmatched speech now routes **to the Lambda** (which replies with an English
  re-prompt) instead of hanging up on the caller.

## 6. Verify — do not assume

**a) Lex alone.** In the Lex console, open the bot → *Test*. Speak or type
"I want to check an order". Expect it to fall through to `FallbackIntent`. If it
matches `NewIntent` instead, your sample utterance is too generic — change it.

**b) The whole chain, no phone needed.** From the repo root:

```bash
VOXFLOW_SECRET="<same as the API's CONNECT_LAMBDA_SECRET>" \
VOXFLOW_API_URL="https://voxflow-jeevesh.duckdns.org" \
  ./deploy/aws/deploy-lambda.sh
```

The script's smoke test invokes the Lambda with a synthetic Connect event carrying
a spoken sentence. `✅ Smoke test passed` proves the code is live, the API is
reachable from Lambda, and the HMAC secret matches.

**c) A real call.** Dial your claimed Connect number and speak a
sentence. Then confirm:

- **CloudWatch** → `/aws/lambda/VoxFlow-Connect-Bridge` → newest log stream →
  the `Received event` line contains your actual words in `user_text`. Empty or
  keypad digits means the flow is still on the old DTMF block.
- **VM API log:** `POST /api/connect/turn` → `200`, with a sensible `agent_reply`.
  A `403 invalid_signature` means the secret mismatches.

## 7. Rollback

Restore the previous flow version in the Connect console (flows are versioned —
*Save as new version* history), or re-import the pre-Lex JSON from git:

```bash
git show HEAD~1:deploy/aws/connect-contact-flow.json > /tmp/old-flow.json
```

The Lex bot itself is harmless when idle; leave it or de-associate it.

## 8. Known limits

- **No Hindi.** Lex V2 has no Hindi locale. Hindi/Hinglish callers need the
  `Connect → Kinesis → Groq Whisper` path, which is deliberately parked until a
  customer needs it.
- **Free tier is 5,000 speech requests/month** for the first 12 months. Every
  conversational turn is one request, so a 10-turn test call costs 10. Watch it
  during heavy testing.
- **Lex adds a hop.** Measure the added latency on a real call; it feeds the Day 43
  latency tuning.
