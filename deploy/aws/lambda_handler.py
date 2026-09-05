"""AWS Lambda function bridging Amazon Connect Contact Flows to VoxFlow Voice Agent API.

This function is invoked by Amazon Connect 'Invoke AWS Lambda function' blocks.
It forwards the caller's transcribed speech (from the Amazon Lex V2 en-GB bot,
exposed to the flow as $.Lex.InputTranscript) to the hosted VoxFlow API and
returns the agent's response text to be spoken via Amazon Polly.

Key features:
  - Multi-turn conversation support with turn counter tracking
  - UK GDPR explicit recording consent classification (consent_granted: true/false)
  - Barge-in compatible session attribute forwarding
  - Fail-safe English fallback and human escalation triggers

Environment Variables:
  - VOXFLOW_API_URL: e.g. 'https://api.yourdomain.com' (or AWS ECS/Fargate)
  - VOXFLOW_SECRET: shared HMAC secret for request authentication
                    (must equal the API's CONNECT_LAMBDA_SECRET)
  - VOXFLOW_DEFAULT_LANG: session language for a new call (default 'en' for UK-English)
"""

import hashlib
import hmac
import json
import os
import re
import time
import urllib.request


def _sign_request(secret: str, timestamp: str, path: str, body: bytes) -> str:
    message = (
        timestamp.encode("utf-8")
        + b":"
        + path.encode("utf-8")
        + b":"
        + body
    )
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _post_json(url: str, payload: dict, secret: str, path: str) -> dict:
    if not secret:
        raise RuntimeError("VOXFLOW_SECRET is required")

    data = json.dumps(payload).encode("utf-8")
    timestamp = str(time.time())
    signature = _sign_request(secret, timestamp, path, data)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "VoxFlow-AWS-Connect-Bridge/1.0",
        "x-voxflow-signature": signature,
        "x-voxflow-timestamp": timestamp,
    }

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _classify_consent(transcript: str) -> bool:
    """Heuristic consent detector for Turn 1 UK GDPR recording announcement.

    Returns False if the caller explicitly rejects or objects to recording,
    otherwise True if caller agrees or proceeds with their query.
    """
    clean = transcript.strip().lower()
    if not clean:
        return False
    # Explicit negative indicators
    refusal_patterns = [
        r"\bno\b",
        r"\bdo not record\b",
        r"\bdon't record\b",
        r"\bno recording\b",
        r"\bstop recording\b",
        r"\bopt out\b",
        r"\brefuse\b",
        r"\bdisagree\b",
    ]
    for pat in refusal_patterns:
        if re.search(pat, clean):
            return False
    return True


def lambda_handler(event, context):
    api_url = os.environ.get("VOXFLOW_API_URL", "https://api.yourdomain.com").rstrip("/")
    secret = os.environ.get("VOXFLOW_SECRET", "")
    default_lang = os.environ.get("VOXFLOW_DEFAULT_LANG", "en")

    details = event.get("Details", {})
    contact_data = details.get("ContactData", {})
    parameters = details.get("Parameters", {})

    contact_id = contact_data.get("ContactId") or event.get("ContactId") or "unknown-contact"
    customer_phone = contact_data.get("CustomerEndpoint", {}).get("Address", "")
    system_phone = contact_data.get("SystemEndpoint", {}).get("Address", "")

    user_text = parameters.get("user_text") or event.get("user_text", "")
    action = parameters.get("action") or event.get("action", "turn")
    turn_raw = parameters.get("turn") or event.get("turn", "1")

    try:
        current_turn = int(str(turn_raw).strip())
    except (ValueError, TypeError):
        current_turn = 1

    if action == "end":
        outcome = parameters.get("outcome", "resolved")
        try:
            _post_json(
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
        except Exception:
            return {"statusCode": 500, "error": "connect_api_request_failed"}

    # Conversational turn
    if not user_text.strip():
        # Blank/empty speech re-prompt
        return {
            "statusCode": 200,
            "agent_reply": "Hello, this is the VoxFlow voice assistant. How can I help you today?",
            "escalate": "false",
            "end_call": "false",
            "consent_granted": "false",
            "voxflow_turn": str(current_turn + 1),
            "language": default_lang,
        }

    try:
        inferred_consent = _classify_consent(user_text)

        res = _post_json(
            f"{api_url}/api/connect/turn",
            {
                "contact_id": contact_id,
                "customer_phone": customer_phone,
                "system_phone": system_phone,
                "user_text": user_text,
                "turn": str(current_turn),
                "language": parameters.get("language") or default_lang,
            },
            secret,
            "/api/connect/turn",
        )

        agent_reply = res.get("agent_reply", "Thank you, I'm glad I could help.")
        escalate = str(res.get("escalate", False)).lower()
        end_call = str(res.get("end_call", False)).lower()
        language = res.get("language", default_lang)

        # Connect Compare block requires exact string "true" or "false"
        api_consent = res.get("consent_granted")
        if api_consent is not None:
            consent_granted = "true" if api_consent else "false"
        else:
            consent_granted = "true" if inferred_consent else "false"

        return {
            "statusCode": 200,
            "agent_reply": agent_reply,
            "escalate": escalate,
            "end_call": end_call,
            "consent_granted": consent_granted,
            "voxflow_turn": str(current_turn + 1),
            "language": language,
        }
    except Exception:
        return {
            "statusCode": 200,
            "agent_reply": "Sorry, I'm having a technical problem and can't help right now. Please call back in a few minutes.",
            "escalate": "true",
            "end_call": "true",
            "consent_granted": "false",
            "voxflow_turn": str(current_turn + 1),
            "error": "connect_api_request_failed",
        }
