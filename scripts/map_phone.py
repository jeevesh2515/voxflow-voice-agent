#!/usr/bin/env python3
"""CLI utility to map a Twilio phone number to a VoxFlow tenant and configure Twilio's voice webhook.

Usage:
  python scripts/map_phone.py --phone +15551234567 --tenant varun --label "Varun Beverages Support"
  python scripts/map_phone.py --auto   # Auto-detects number from Twilio account and maps to varun
"""

import argparse
import sys
import os

# Ensure package root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api")))

from voxflow_api.config import get_settings
from voxflow_api.db import TenantPhoneNumber, session_scope, init_db
from voxflow_api.logging import get_logger

log = get_logger("map_phone")


def configure_twilio_webhook(phone_number: str, webhook_url: str) -> bool:
    """Configures the voice webhook URL for the specified phone number in Twilio."""
    settings = get_settings()
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        print("❌ Twilio Account SID or Auth Token missing in environment!")
        return False

    try:
        from twilio.rest import Client
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
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
        print(f"✅ Twilio Webhook Updated Successfully!")
        print(f"   Phone:      {updated.phone_number}")
        print(f"   Voice URL:  {updated.voice_url}")
        print(f"   HTTP Method: {updated.voice_method}")
        return True

    except Exception as e:
        print(f"❌ Twilio Webhook Configuration Error: {e}")
        return False


def map_tenant_phone_number(phone_number: str, tenant_id: str, label: str):
    """Inserts or updates the phone number to tenant mapping in Postgres/SQLite database."""
    init_db()
    with session_scope() as db:
        existing = db.get(TenantPhoneNumber, phone_number)
        if existing:
            existing.tenant_id = tenant_id
            existing.label = label
            existing.active = 1
            print(f"✅ Updated existing database mapping: {phone_number} -> tenant '{tenant_id}' ({label})")
        else:
            db.add(TenantPhoneNumber(phone_number=phone_number, tenant_id=tenant_id, label=label, active=1))
            print(f"✅ Inserted new database mapping: {phone_number} -> tenant '{tenant_id}' ({label})")


def main():
    parser = argparse.ArgumentParser(description="Map phone number to tenant and configure Twilio webhook.")
    parser.add_argument("--phone", type=str, help="Phone number in E.164 format (e.g. +15551234567)")
    parser.add_argument("--tenant", type=str, default="varun", help="Tenant ID (default: varun)")
    parser.add_argument("--label", type=str, default="Customer Support Line", help="Label for this line")
    parser.add_argument("--url", type=str, default=None, help="Webhook URL (default: PUBLIC_BASE_URL/twilio/voice)")
    parser.add_argument("--auto", action="store_true", help="Auto-detect first Twilio number and map it")

    args = parser.parse_args()
    settings = get_settings()
    webhook_url = args.url or f"{(settings.public_base_url or 'https://your-domain.com').rstrip('/')}/twilio/voice"

    phone = args.phone

    if args.auto or not phone:
        if settings.twilio_account_sid and settings.twilio_auth_token:
            try:
                from twilio.rest import Client
                client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
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
    print(f" VoxFlow Twilio & Tenant Mapper")
    print(f"   Target Phone:  {phone}")
    print(f"   Target Tenant: {args.tenant}")
    print(f"   Webhook URL:   {webhook_url}")
    print("==========================================================================")

    # 1. Update Twilio Webhook
    configure_twilio_webhook(phone, webhook_url)

    # 2. Update Database
    map_tenant_phone_number(phone, args.tenant, args.label)

    print("\n🎉 Complete! Test by calling the number from your phone.")


if __name__ == "__main__":
    main()
