#!/usr/bin/env python3
"""2-Minute Automated Tenant Onboarding CLI Script for VoxFlow SaaS.

Usage:
  python scripts/onboard_tenant.py \
    --tenant-id "acme_logistics" \
    --company-name "Acme Logistics Pvt Ltd" \
    --phone-number "+14155550199" \
    --agent-name "Sara" \
    --language "en" \
    --admin-email "ops@acmelogistics.com" \
    --webhook-url "https://api.acmelogistics.com/webhooks/voxflow" \
    --plan "pro"
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys

# Ensure api is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api")))

from voxflow_api.db import Tenant, TenantPhoneNumber, init_db, session_scope


def parse_args():
    p = argparse.ArgumentParser(description="Onboard a new paying SaaS client in under 2 minutes.")
    p.add_argument("--tenant-id", required=True, help="Unique slug for the client (e.g. acme_corp)")
    p.add_argument("--company-name", required=True, help="Full business name (e.g. Acme Corp)")
    p.add_argument("--phone-number", required=True, help="E.164 Twilio phone number (e.g. +14155550199)")
    p.add_argument("--agent-name", default="Vaani", help="Voice agent persona name (default: Vaani)")
    p.add_argument("--language", default="hi", choices=["hi", "en", "es"], help="Default language (hi/en/es)")
    p.add_argument("--admin-email", default="", help="Primary admin email for dashboard login")
    p.add_argument("--prompt-override", default="", help="Custom business instructions for LLM")
    p.add_argument("--welcome-message", default="", help="Custom opening greeting")
    p.add_argument("--webhook-url", default="", help="Client ERP/CRM webhook URL")
    p.add_argument("--plan", default="pro", choices=["starter", "pro", "enterprise"], help="Subscription plan")
    p.add_argument("--dry-run", action="store_true", help="Print actions without saving to database")
    return p.parse_args()


def main():
    args = parse_args()
    clean_phone = args.phone_number.strip().replace(" ", "")
    webhook_secret = f"whsec_{secrets.token_hex(16)}" if args.webhook_url else None

    print("\n" + "=" * 70)
    print(f"🏢 VoxFlow SaaS — Onboarding Client: {args.company_name} ({args.tenant_id})")
    print("=" * 70)

    print(f"• Tenant ID        : {args.tenant_id}")
    print(f"• Company Name     : {args.company_name}")
    print(f"• Assigned Phone   : {clean_phone}")
    print(f"• Agent Persona    : {args.agent_name} (Language: {args.language.upper()})")
    print(f"• Subscription Plan: {args.plan.upper()}")
    if args.webhook_url:
        print(f"• Webhook URL      : {args.webhook_url}")
        print(f"• Webhook Secret   : {webhook_secret}")
    if args.admin_email:
        print(f"• Admin Login Email: {args.admin_email}")

    if args.dry_run:
        print("\n[DRY RUN] No changes were written to the database.")
        return

    init_db()

    with session_scope() as db:
        tenant = db.get(Tenant, args.tenant_id)
        if not tenant:
            tenant = Tenant(
                id=args.tenant_id,
                name=args.company_name,
                agent_name=args.agent_name,
                default_language=args.language,
                system_prompt_override=args.prompt_override or None,
                welcome_message=args.welcome_message or None,
                webhook_url=args.webhook_url or None,
                webhook_secret=webhook_secret,
                plan=args.plan,
            )
            db.add(tenant)
            print("\n✅ Created new Tenant record in database.")
        else:
            tenant.name = args.company_name
            tenant.agent_name = args.agent_name
            tenant.default_language = args.language
            if args.prompt_override:
                tenant.system_prompt_override = args.prompt_override
            if args.webhook_url:
                tenant.webhook_url = args.webhook_url
                tenant.webhook_secret = webhook_secret
            tenant.plan = args.plan
            print("\n✅ Updated existing Tenant record in database.")

        phone_entry = db.get(TenantPhoneNumber, clean_phone)
        if phone_entry:
            phone_entry.tenant_id = args.tenant_id
            phone_entry.label = f"{args.company_name} Main Line"
        else:
            phone_entry = TenantPhoneNumber(
                phone_number=clean_phone,
                tenant_id=args.tenant_id,
                label=f"{args.company_name} Main Line",
            )
            db.add(phone_entry)

        print(f"✅ Mapped phone number {clean_phone} → {args.tenant_id}")

    print("\n" + "=" * 70)
    print("🎉 Onboarding Completed Successfully!")
    print(f"Next Steps:")
    print(f"1. In Twilio: Point {clean_phone} Webhook to https://<your-domain>/twilio/voice")
    print(f"2. Dashboard Portal: https://<your-domain>/sign-in (Tenant: {args.tenant_id})")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
