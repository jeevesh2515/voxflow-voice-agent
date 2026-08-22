# Amazon Connect Setup Guide for VoxFlow

This guide explains how to set up **Amazon Connect** with the **VoxFlow Voice Agent** so that inbound customer & supplier phone calls are answered by VoxFlow on AWS (90 minutes/month free tier).

---

## Architecture Overview

```
Inbound Caller
      │
      ▼
Amazon Connect (Phone Number / DID)
      │
      ▼
Contact Flow (Speech Input & Polly TTS)
      │
      ▼
AWS Lambda (VoxFlow-Connect-Bridge)
      │  (HMAC Signed REST Turn)
      ▼
VoxFlow API (Render / Oracle VM)
      ├── AgentRunner (LLM reasoning & tool execution)
      ├── Order Tracking / Inventory Check / Appointment Booking
      └── Google Sheets & PostgreSQL Persistence
```

---

## Step 1: Create an Amazon Connect Instance (Free)

1. Open AWS Console and navigate to **Amazon Connect** (recommended region: `us-east-1` N. Virginia).
2. Click **Add an instance**.
3. Choose **Store users in Amazon Connect** (specify an access URL alias, e.g. `voxflow-agent`).
4. In Step 2, create an administrator user.
5. In Step 3 (Telephony Options), check both **Incoming calls** and **Outgoing calls**.
6. Click **Create instance** and wait ~1 minute for provisioning.

---

## Step 2: Claim a Free Phone Number

1. Log into your Amazon Connect Admin Console (`https://<your-alias>.awsapps.com/connect/login`).
2. Go to **Channels → Phone Numbers → Claim a number**.
3. Select **DID (Direct Inward Dialing)** or **Toll-Free**.
4. Choose your country (US, UK, India, etc.) and select a free phone number.
5. Save the claimed phone number.

---

## Step 3: Deploy the AWS Lambda Bridge

1. Create a Lambda function named `VoxFlow-Connect-Bridge` (Python 3.12).
2. Set Environment Variables in Lambda:
   - `VOXFLOW_API_URL`: `https://voxflow-voice-agent.onrender.com` (or your domain)
   - `VOXFLOW_SECRET`: `your_random_hmac_secret` (matches `CONNECT_LAMBDA_SECRET` in VoxFlow `.env`)
3. Copy the code from [`deploy/aws/lambda_handler.py`](file:///Users/jeeveshsingale/VoxFlow/voxflow-voice-agent/deploy/aws/lambda_handler.py) or deploy using `./deploy/aws/deploy-lambda.sh`.
4. In AWS Lambda → **Configuration → Permissions → Resource-based policy**:
   - Grant `connect.amazonaws.com` permission to invoke this Lambda function.
5. In Amazon Connect Console:
   - Go to **Contact Flows → AWS Lambda** and add the `VoxFlow-Connect-Bridge` Lambda function.

---

## Step 4: Import the Contact Flow

1. In Amazon Connect Admin Console, go to **Routing → Contact Flows**.
2. Click **Create contact flow**.
3. Click the top-right menu dropdown (`...`) and select **Import flow (beta)**.
4. Select the file [`deploy/aws/connect-contact-flow.json`](file:///Users/jeeveshsingale/VoxFlow/voxflow-voice-agent/deploy/aws/connect-contact-flow.json).
5. In the **Invoke AWS Lambda function** block, select your `VoxFlow-Connect-Bridge` function from the dropdown.
6. Click **Save** and **Publish**.

---

## Step 5: Assign the Phone Number to the Contact Flow

1. Go to **Channels → Phone Numbers**.
2. Click on your claimed phone number.
3. Under **Contact flow / IVR**, select the published **VoxFlow Contact Flow**.
4. Click **Save**.

---

## Step 6: Test Your Voice Agent!

1. Dial your Amazon Connect phone number from any mobile or landline.
2. The agent will greet you in Hindi/English:
   *"नमस्ते, वॉक्सफ़्लो में आपका स्वागत है। मैं आपकी क्या मदद कर सकता हूँ?"*
3. Speak your request (e.g. *"PO-101 का स्टेटस क्या है?"* or *"मुझे नया ऑर्डर देना है"*).
4. The agent will execute tools, answer your questions, and automatically log outcomes to Google Sheets and your database!
