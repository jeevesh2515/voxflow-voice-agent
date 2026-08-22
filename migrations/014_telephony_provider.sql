-- 014_telephony_provider.sql
-- Add telephony provider routing column to tenant_phone_numbers

ALTER TABLE tenant_phone_numbers 
  ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'twilio';

CREATE INDEX IF NOT EXISTS ix_tenant_phone_numbers_provider 
  ON tenant_phone_numbers(provider);
