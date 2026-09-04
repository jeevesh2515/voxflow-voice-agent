# Amazon Connect Setup Guide for VoxFlow (London eu-west-2)

This guide explains how to set up **Amazon Connect** with the **VoxFlow Voice Agent** in **London (`eu-west-2`)** so that inbound customer & supplier phone calls are answered by VoxFlow with:
- **Multi-turn conversational dialog** (up to 10 back-and-forth turns via the native Connect Loop block)
- **UK GDPR explicit recording consent** (recording only starts after affirmative consent)
- **Lex V2 speech barge-in** (`x-amz-lex:barge-in-enabled = "true"`)
- **Sub-200ms edge turn latency** with HMAC-authenticated Lambda bridge.

---

## Architecture Overview

```
Inbound Caller (UK DID +44)
       │
       ▼
Amazon Connect (eu-west-2 London)
       │
       ├── 1. Set Voice (Amy, en-GB) & Barge-In (x-amz-lex:barge-in-enabled)
       ├── 2. Consent Capture (Lex V2: VoxFlowInbound)
       │       └── Lambda Classification (consent_granted: true/false)
       │            ├── True: Dual-Channel Recording Enabled (Agent + Customer)
       │            └── False: Recording Disabled (GDPR Default)
       ▼
Conversation Loop (Max 10 Turns)
       ├── Prompt / Re-Prompt ("Is there anything else I can help you with?")
       ├── Lex V2 Speech Transcription
       └── Invoke Lambda: VoxFlow-Connect-Bridge
               │ (HMAC-SHA256 Signed Turn Request)
               ▼
       VoxFlow API (London eu-west-2 / ECS / VM)
               ├── AgentRunner (LLM reasoning & tool execution)
               ├── Order Tracking / Inventory Check / Caller PIN Verification
               └── Google Sheets Mirror & PostgreSQL Persistence
```

---

## Step 1: Create an Amazon Connect Instance (London eu-west-2)

1. Open AWS Console and navigate to **Amazon Connect** in region **Europe (London) `eu-west-2`**.
2. Click **Add an instance**.
3. Choose **Store users in Amazon Connect** (specify an access URL alias, e.g. `voxflow-ops-uk`).
4. In Step 2, create an administrator user.
5. In Step 3 (Telephony Options), check both **Incoming calls** and **Outgoing calls**.
6. In Step 4 (Data Storage), enable call recordings to your dedicated S3 bucket (`eu-west-2`).
7. Click **Create instance** and wait ~1 minute for provisioning.

---

## Step 2: Claim a UK DID Phone Number (+44)

1. Log into your Amazon Connect Admin Console (`https://<your-alias>.awsapps.com/connect/login`).
2. Go to **Channels → Phone Numbers → Claim a number**.
3. Select **DID (Direct Inward Dialing)**.
4. Choose **United Kingdom (+44)** and select a London/UK number (e.g. `+44 20 7946 0991`).
5. Save the claimed phone number.

---

## Step 3: Deploy the AWS Lambda Bridge

1. Create a Lambda function named `VoxFlow-Connect-Bridge` (Python 3.12, region `eu-west-2`).
2. Set Environment Variables in Lambda:
   - `VOXFLOW_API_URL`: `https://your-domain.com` (or your AWS ECS Fargate domain)
   - `VOXFLOW_SECRET`: `your_random_hmac_secret` (must equal `CONNECT_LAMBDA_SECRET` in VoxFlow `.env`)
   - `VOXFLOW_DEFAULT_LANG`: `en` (or `hi` for Hindi)
3. Deploy the code from [`deploy/aws/lambda_handler.py`](file:///Users/jeeveshsingale/VoxFlow/voxflow-voice-agent/deploy/aws/lambda_handler.py).
4. Under **Configuration → Permissions → Resource-based policy**:
   - Grant `connect.amazonaws.com` permission to invoke this Lambda function.
5. In Amazon Connect Console:
   - Go to **Contact Flows → AWS Lambda** and register `VoxFlow-Connect-Bridge`.

---

## Step 4: Import the Multi-Turn UK GDPR Contact Flow

1. Open [`deploy/aws/connect-contact-flow.json`](file:///Users/jeeveshsingale/VoxFlow/voxflow-voice-agent/deploy/aws/connect-contact-flow.json).
2. Replace the 3 ARN placeholders with your real AWS identifiers:
   - `YOUR_AWS_ACCOUNT_ID`: Your 12-digit AWS Account ID (e.g. `123456789012`)
   - `YOUR_LEX_BOT_ID`: Your Lex V2 Bot ID
   - `YOUR_LEX_ALIAS_ID`: Your Lex V2 Bot Alias ID (e.g. `TSTALIASID` or `PRODALIASID`)
3. In Amazon Connect Admin Console, go to **Routing → Contact Flows**.
4. Click **Create contact flow**.
5. Click the top-right menu dropdown (`...`) and select **Import flow (beta)**.
6. Select your updated `deploy/aws/connect-contact-flow.json`.
7. Verify that:
   - Voice is set to **Amy (en-GB)**
   - Consent announcement routes to `InvokeLambdaConsent` $\rightarrow$ `CompareConsent`
   - `SetRecordingOn` / `SetRecordingOff` branches are mapped
   - `ConversationLoop` loop block is linked with max 10 iterations.
8. Click **Save** and **Publish**.

---

## Step 5: Assign the UK Phone Number to the Contact Flow

1. Go to **Channels → Phone Numbers**.
2. Click on your claimed +44 UK phone number.
3. Under **Contact flow / IVR**, select the published **VoxFlow Contact Flow**.
4. Click **Save**.

---

## Step 6: Test Inbound UK Voice Flow

1. Dial your UK DID (`+44 ...`) from any phone.
2. The agent will greet you with the UK GDPR recording disclosure:
   > *"Hello, and welcome to VoxFlow. Please note that calls may be recorded for quality and training purposes. If you are happy to continue, tell me how I can help you."*
3. State your query (e.g. *"Check status for PO-1002"* or *"Is stock available for SKU-4001?"*).
4. If you say *"No, do not record"*, recording is immediately turned off, and the agent continues helping you seamlessly.
5. After the agent responds, it will ask *"Is there anything else I can help you with?"* allowing up to 10 natural conversational turns before completing or escalating!
