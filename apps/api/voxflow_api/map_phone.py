#!/usr/bin/env python3
"""CLI module to map a Twilio phone number to a VoxFlow tenant and configure Twilio's voice webhook.

Usage:
  python -m voxflow_api.map_phone --phone +15551234567 --tenant varun --label "Varun Beverages Support"
  python -m voxflow_api.map_phone --auto   # Auto-detects number from Twilio account and maps to varun
"""

import argparse
import sys

from voxflow_api.config import get_settings
from voxflow_api.db import TenantPhoneNumber, session_scope, init_db
from voxflow_api.logging import get_logger
from voxflow_api.services.telephony_routing import normalize_e164, validate_provider

log = get_logger("map_phone")


def _twilio_client():
    """Return a Twilio REST client, preferring API Key auth over Account SID/Auth Token."""
    from twilio.rest import Client
    settings = get_settings()
    # Prefer API Key credentials (safer for rotation; never use the master Auth Token
    # in tooling if you can avoid it).  Fall back to Account SID + Auth Token.
    if settings.twilio_api_key and settings.twilio_api_secret and settings.twilio_account_sid:
        return Client(settings.twilio_api_key, settings.twilio_api_secret, settings.twilio_account_sid)
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def configure_twilio_webhook(phone_number: str, webhook_url: str) -> bool:
    """Configures the voice webhook URL for the specified phone number in Twilio."""
    settings = get_settings()
    if not settings.twilio_account_sid:
        print("❌ TWILIO_ACCOUNT_SID missing in environment!")
        return False
    if not settings.twilio_auth_token and not (settings.twilio_api_key and settings.twilio_api_secret):
        print("❌ Twilio credentials missing: set TWILIO_AUTH_TOKEN, or TWILIO_API_KEY + TWILIO_API_SECRET")
        return False

    try:
        client = _twilio_client()
        numbers = client.incoming_phone_numbers.list()
        
        target = None
        for n in numbers:
            if n.phone_number == phone_number or n.phone_number.replace("+", "") == phone_number.replace("+", ""):
                target = n
                break
        
        if not target:
            print(f"⚠️  Phone number {phone_number} not found in Twilio account list. Listing available numbers:")
            for n in numbers:
                print(f"   - {n.phone_number} (SID: {n.sid})")
            if numbers:
                target = numbers[0]
                print(f"👉 Selecting available Twilio number {target.phone_number} to configure.")
            else:
                print("❌ No active incoming phone numbers found in Twilio account.")
                print("   Please get/purchase a phone number in your Twilio Console (https://console.twilio.com) first.")
                return False

        updated = client.incoming_phone_numbers(target.sid).update(
            voice_url=webhook_url,
            voice_method="POST"
        )
        print("✅ Twilio Webhook Updated Successfully!")
        print(f"   Phone:       {updated.phone_number}")
        print(f"   Voice URL:   {updated.voice_url}")
        print(f"   HTTP Method: {updated.voice_method}")
        return True

    except Exception as e:
        print(f"❌ Twilio Webhook Configuration Error: {e}")
        return False


def map_tenant_phone_number(phone_number: str, tenant_id: str, label: str, provider: str = "connect"):
    """Insert or update one exact inbound mapping without cross-tenant transfer."""
    init_db()
    normalized_phone = normalize_e164(phone_number)
    normalized_provider = validate_provider(provider)
    with session_scope() as db:
        existing = db.get(TenantPhoneNumber, normalized_phone)
        if existing and existing.tenant_id != tenant_id:
            raise ValueError("phone_number_owned_by_another_tenant")
        if existing:
            existing.label = label
            existing.provider = normalized_provider
            existing.active = 1
            print(f"✅ Updated existing database mapping: {normalized_phone} -> tenant '{tenant_id}' ({label})")
        else:
            db.add(
                TenantPhoneNumber(
                    phone_number=normalized_phone,
                    tenant_id=tenant_id,
                    label=label,
                    provider=normalized_provider,
                    active=1,
                )
            )
            print(f"✅ Inserted new database mapping: {normalized_phone} -> tenant '{tenant_id}' ({label})")


def main():
    parser = argparse.ArgumentParser(description="Map phone number to tenant and configure Twilio webhook.")
    parser.add_argument("--phone", type=str, help="Phone number in E.164 format (e.g. +15551234567)")
    parser.add_argument("--tenant", type=str, default="varun", help="Tenant ID (default: varun)")
    parser.add_argument("--label", type=str, default="Customer Support Line", help="Label for this line")
    # "connect" (Amazon Connect) is the only provider with a live inbound
    # resolution route; it is the default so this tool cannot silently
    # create a phone mapping that will never receive a call. "twilio" and
    # "telnyx" remain selectable for forward-compatible schema storage only.
    parser.add_argument("--provider", choices=("connect", "twilio", "telnyx"), default="connect")
    parser.add_argument("--url", type=str, default=None, help="Webhook URL (default: PUBLIC_BASE_URL/twilio/voice)")
    parser.add_argument("--auto", action="store_true", help="Auto-detect first Twilio number and map it")

    args = parser.parse_args()
    settings = get_settings()
    webhook_url = args.url or f"{(settings.public_base_url or 'https://your-domain.com').rstrip('/')}/twilio/voice"

    phone = args.phone

    if args.auto or not phone:
        if settings.twilio_account_sid and (settings.twilio_auth_token or (settings.twilio_api_key and settings.twilio_api_secret)):
            try:
                client = _twilio_client()
                numbers = client.incoming_phone_numbers.list()
                if numbers:
                    phone = numbers[0].phone_number
                    print(f"📱 Auto-detected Twilio phone number: {phone}")
                else:
                    print("⚠️  No phone numbers found in Twilio account yet.")
            except Exception as e:
                print(f"⚠️  Could not auto-detect Twilio phone number: {e}")

    if not phone:
        print("Usage error: Please specify --phone <E.164_NUMBER> or buy a number in Twilio console first.")
        sys.exit(1)

    print("==========================================================================")
    print(" VoxFlow Twilio & Tenant Mapper")
    print(f"   Target Phone:  {phone}")
    print(f"   Target Tenant: {args.tenant}")
    print(f"   Webhook URL:   {webhook_url}")
    print("==========================================================================")

    # 1. Update Twilio Webhook (only meaningful if this line is actually a
    #    Twilio-provider line; Amazon Connect routing does not use it).
    if args.provider == "twilio":
        configure_twilio_webhook(phone, webhook_url)
    else:
        print(f"ℹ️  Skipping Twilio webhook configuration (provider={args.provider}).")

    # 2. Update Database
    map_tenant_phone_number(phone, args.tenant, args.label, args.provider)

    print("\n🎉 Complete! Test by calling the number from your phone.")


if __name__ == "__main__":
    main()
