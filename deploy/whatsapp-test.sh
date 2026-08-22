#!/usr/bin/env bash
#
# VoxFlow — prove WhatsApp delivery to a real handset, free, with no purchased number.
#
# WHY this works without buying anything: side_effect_worker_service.py swaps the
# message source to settings.twilio_whatsapp_number for the whatsapp channel
# (lines 322-326), and that setting already defaults to Twilio's Sandbox sender
# whatsapp:+14155238886. Only SMS falls back to twilio_phone_number, which is the
# DID this account does not own. So the WhatsApp half of the product is fully
# reachable on a Trial account today.
#
# PREREQUISITE you must do by hand first — the Sandbox refuses every recipient
# that has not opted in:
#   1. open console.twilio.com > Messaging > Try it out > Send a WhatsApp message
#   2. note the join phrase shown there (looks like "join amber-tiger")
#   3. from the WhatsApp app on the handset you want to test, send exactly that
#      phrase to +1 415 523 8886
#   4. WhatsApp replies confirming the sandbox is joined
# The opt-in lapses after ~72h of inactivity; re-send the phrase to renew it.
#
# Usage:
#   ./deploy/whatsapp-test.sh +919876543210
#   ./deploy/whatsapp-test.sh +919876543210 --link-supplier sup-varun-001
#
# --link-supplier repoints a seeded supplier's phone at this handset, so the
# agent's send_whatsapp_message tool (agent/tools.py:802) reaches you during a
# real call instead of a fictional seeded number. It is a plain data update and
# is reversible by re-running deploy/seed-db.sh after deleting the row.
#
set -euo pipefail

VM_HOST="${VM_HOST:-193.123.187.97}"
VM_USER="${VM_USER:-ubuntu}"
VM_KEY="${VM_KEY:-$HOME/Downloads/ssh-key-2026-08-03.key}"

TO="${1:-}"
SUPPLIER=""
if [[ "${2:-}" == "--link-supplier" ]]; then
  SUPPLIER="${3:?--link-supplier needs a supplier id, e.g. sup-varun-001}"
elif [[ -n "${2:-}" ]]; then
  echo "FAILED: unknown argument '$2'. Use --link-supplier <id>." >&2
  exit 1
fi

if [[ -z "$TO" ]]; then
  echo "FAILED: pass the recipient in E.164, e.g. ./deploy/whatsapp-test.sh +919876543210" >&2
  exit 1
fi
case "$TO" in
  +[0-9][0-9]*) ;;
  *) echo "FAILED: '$TO' is not E.164 — it must start with + and a country code." >&2; exit 1 ;;
esac

SSH=(ssh -i "$VM_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 "${VM_USER}@${VM_HOST}")
[[ -f "$VM_KEY" ]] || { echo "FAILED: SSH key not found at $VM_KEY" >&2; exit 1; }

echo "==> WhatsApp test  (to: ${TO}${SUPPLIER:+, link supplier: $SUPPLIER})"

{
  printf 'VF_TO=%q\nVF_SUPPLIER=%q\n' "$TO" "$SUPPLIER"
  cat <<'REMOTE'
set -uo pipefail
cd /home/ubuntu/voxflow-voice-agent/deploy

docker compose --env-file ../.env -f docker-compose.prod.yml \
  exec -T -e VF_TO="${VF_TO}" -e VF_SUPPLIER="${VF_SUPPLIER}" \
  api python - <<'PY' 2>&1
import os, sys

from voxflow_api.config import get_settings
from voxflow_api.db import Supplier, session_scope

to_raw = os.environ["VF_TO"]
supplier_id = os.environ["VF_SUPPLIER"]

s = get_settings()
source = s.twilio_whatsapp_number or ""
print("=== configuration ===")
print("  sandbox sender  %s" % (source or "(unset)"))
print("  recipient       %s" % to_raw)
if not source:
    print("FAILED: TWILIO_WHATSAPP_NUMBER is empty. The default is")
    print("        whatsapp:+14155238886 — something in .env overrode it to blank.")
    sys.exit(1)
if not source.startswith("whatsapp:"):
    print("FAILED: TWILIO_WHATSAPP_NUMBER must carry the whatsapp: prefix, got %r" % source)
    sys.exit(1)
if not s.twilio_account_sid or not s.twilio_auth_token:
    print("FAILED: TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN missing from .env")
    sys.exit(1)

from twilio.rest import Client
from twilio.base.exceptions import TwilioException

client = Client(s.twilio_account_sid, s.twilio_auth_token)


def err(exc):
    code = getattr(exc, "code", None)
    msg = getattr(exc, "msg", None) or str(exc)
    return msg if code is None else "%s (code %s)" % (msg, code)


target = to_raw if to_raw.startswith("whatsapp:") else "whatsapp:%s" % to_raw
body = ("VoxFlow test: your order PO-1717000000-001 is signed and shipped, "
        "tracking VRL-998877, last seen Ghaziabad Hub.")

print()
print("=== sending ===")
try:
    msg = client.messages.create(from_=source, to=target, body=body)
except TwilioException as exc:
    code = getattr(exc, "code", None)
    print("FAILED: %s" % err(exc))
    # The three failures that actually happen here, and what each really means.
    if code in (63016, 63015):
        print("        The handset has not joined the Sandbox, or the 72h opt-in")
        print("        lapsed. Send the join phrase from console.twilio.com >")
        print("        Messaging > Try it out > Send a WhatsApp message to")
        print("        +1 415 523 8886, then re-run this.")
    elif code == 63007:
        print("        Twilio does not recognise %s as a WhatsApp sender." % source)
        print("        On a Trial the only valid sender is the Sandbox number.")
    elif code == 21910:
        print("        Channel mismatch — from_ and to must BOTH carry the")
        print("        whatsapp: prefix.")
    sys.exit(1)

print("  sid     %s" % msg.sid)
print("  status  %s" % msg.status)
print("  queued to %s" % target)
print()
print("  'queued' or 'accepted' is normal — Twilio hands off asynchronously.")
print("  Delivery is confirmed by the message arriving on the handset.")

# --- optional: make the agent's tool reach this handset --------------------
if supplier_id:
    print()
    print("=== linking supplier %s ===" % supplier_id)
    with session_scope() as db:
        sup = db.get(Supplier, supplier_id)
        if sup is None:
            print("FAILED: no supplier %r. Seeded ids are sup-varun-001..003," % supplier_id)
            print("        sup-amul-001..002, sup-hal-001..002, sup-brt-001..002.")
            sys.exit(1)
        old = sup.phone
        sup.phone = to_raw
        print("  %s (%s)" % (sup.name, sup.tenant_id))
        print("  phone %s -> %s" % (old, to_raw))
    print("  send_whatsapp_message now reaches this handset when the agent")
    print("  notifies that supplier during a call.")
PY
rc=${PIPESTATUS[0]}
[[ $rc -eq 0 ]] || { echo "RESULT: failed"; exit 1; }

echo
echo "RESULT: MESSAGE ACCEPTED BY TWILIO — check the handset"
REMOTE
} | "${SSH[@]}" 'f=$(mktemp /tmp/voxflow-remote.XXXXXX); cat > "$f"; bash "$f" </dev/null; rc=$?; rm -f "$f"; exit $rc'
