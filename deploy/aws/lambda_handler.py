"""AWS Lambda function bridging Amazon Connect Contact Flows to VoxFlow Voice Agent API.

This function is invoked by Amazon Connect 'Invoke AWS Lambda function' blocks.
It forwards the caller's transcribed speech (from the Amazon Lex V2 en-GB bot,
exposed to the flow as $.Lex.InputTranscript) to the hosted VoxFlow API and
returns the agent's response text to be spoken via Amazon Polly.

Environment Variables:
  - VOXFLOW_API_URL: e.g. 'https://voxflow-jeevesh.duckdns.org' (the always-on VM)
  - VOXFLOW_SECRET: shared HMAC secret for request authentication
                    (must equal the VM's CONNECT_LAMBDA_SECRET)
  - VOXFLOW_DEFAULT_LANG: session language for a new call (default 'en' for the
                          UK-English market; the API/agent still mirror the caller).
"""

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request


def _sign_request(secret: str, timestamp: str, path: str) -> str:
    message = f"{timestamp}:{path}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _post_json(url: str, payload: dict, secret: str, path: str) -> dict:
    data = json.dumps(payload).encode("utf-8")
    timestamp = str(time.time())
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "VoxFlow-AWS-Connect-Bridge/1.0",
    }
    if secret:
        signature = _sign_request(secret, timestamp, path)
        headers["x-voxflow-signature"] = signature
        headers["x-voxflow-timestamp"] = timestamp

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))


def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    # Default to the always-on Oracle VM. Amazon Connect gives this Lambda ~8s;
    # a Render Free cold start blows that budget and drops the call. Override in
    # AWS with the VOXFLOW_API_URL env var (env wins; this is only a safety net).
    api_url = os.environ.get("VOXFLOW_API_URL", "https://voxflow-jeevesh.duckdns.org").rstrip("/")
    secret = os.environ.get("VOXFLOW_SECRET", "")

    # First market is UK English. The session starts in English; the agent still
    # mirrors whatever language the caller actually speaks (see agent/prompts.py).
    default_lang = os.environ.get("VOXFLOW_DEFAULT_LANG", "en")

    details = event.get("Details", {})
    contact_data = details.get("ContactData", {})
    parameters = details.get("Parameters", {})

    contact_id = contact_data.get("ContactId") or event.get("ContactId") or "unknown-contact"
    customer_phone = contact_data.get("CustomerEndpoint", {}).get("Address", "")
    system_phone = contact_data.get("SystemEndpoint", {}).get("Address", "")

    # Caller speech transcribed by the Amazon Lex V2 bot and passed by the contact
    # flow as $.Lex.InputTranscript. (Legacy DTMF paths may still send user_text.)
    user_text = parameters.get("user_text") or event.get("user_text", "")
    action = parameters.get("action") or event.get("action", "turn")

    if action == "end":
        outcome = parameters.get("outcome", "resolved")
        try:
            res = _post_json(
                f"{api_url}/api/connect/end",
                {"contact_id": contact_id, "outcome": outcome},
                secret,
                "/api/connect/end",
            )
            return {
                "statusCode": 200,
                "status": "ended",
                "contact_id": contact_id,
            }
        except Exception as e:
            print("Error ending session:", str(e))
            return {"statusCode": 500, "error": str(e)}

    # Conversational turn
    if not user_text.strip():
        # Caller gave blank/empty speech (Lex returned no transcript). Re-prompt in
        # English without an API call to conserve latency/cost.
        return {
            "statusCode": 200,
            "agent_reply": "Hello, this is the VoxFlow voice assistant. How can I help you today?",
            "escalate": "false",
            "end_call": "false",
            "language": default_lang,
        }

    try:
        res = _post_json(
            f"{api_url}/api/connect/turn",
            {
                "contact_id": contact_id,
                "customer_phone": customer_phone,
                "system_phone": system_phone,
                "user_text": user_text,
                "language": parameters.get("language") or default_lang,
            },
            secret,
            "/api/connect/turn",
        )

        agent_reply = res.get("agent_reply", "Thank you, I'm glad I could help.")
        escalate = str(res.get("escalate", False)).lower()
        end_call = str(res.get("end_call", False)).lower()
        language = res.get("language", default_lang)

        return {
            "statusCode": 200,
            "agent_reply": agent_reply,
            "escalate": escalate,
            "end_call": end_call,
            "language": language,
        }
    except Exception as e:
        print("Error processing turn:", str(e))
        return {
            "statusCode": 200,
            "agent_reply": "Sorry, I'm having a technical problem and can't help right now. Please call back in a few minutes.",
            "escalate": "true",
            "end_call": "true",
            "error": str(e),
        }
