-- 016_telephony_routing_and_caller_pins.sql
-- Exact provider/DID routing and secure caller-verification PIN storage.

ALTER TABLE suppliers
  ADD COLUMN IF NOT EXISTS auth_pin_hash VARCHAR(255),
  ADD COLUMN IF NOT EXISTS pin_updated_at TIMESTAMP WITH TIME ZONE,
  ADD COLUMN IF NOT EXISTS pin_failed_attempts INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS pin_locked_until TIMESTAMP WITH TIME ZONE;

-- Legacy plaintext remains nullable only for compatibility during verification.
-- Every new/update path writes auth_pin_hash and clears auth_pin.
ALTER TABLE suppliers
  ALTER COLUMN auth_pin DROP NOT NULL,
  ALTER COLUMN auth_pin DROP DEFAULT;

ALTER TABLE tenant_phone_numbers
  ADD COLUMN IF NOT EXISTS verification_mode VARCHAR(16) NOT NULL DEFAULT 'standard',
  ADD COLUMN IF NOT EXISTS route_language VARCHAR(16) NOT NULL DEFAULT 'tenant_default',
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;

UPDATE tenant_phone_numbers
SET updated_at = created_at
WHERE updated_at IS NULL;

ALTER TABLE tenant_phone_numbers
  ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP,
  ALTER COLUMN updated_at SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_tenant_phone_provider_active
  ON tenant_phone_numbers (provider, phone_number, active);

CREATE INDEX IF NOT EXISTS ix_tenant_phone_tenant_active
  ON tenant_phone_numbers (tenant_id, active);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_tenant_phone_provider') THEN
    ALTER TABLE tenant_phone_numbers
      ADD CONSTRAINT ck_tenant_phone_provider
      CHECK (provider IN ('connect', 'twilio', 'telnyx'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_tenant_phone_verification_mode') THEN
    ALTER TABLE tenant_phone_numbers
      ADD CONSTRAINT ck_tenant_phone_verification_mode
      CHECK (verification_mode IN ('standard', 'enhanced'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_tenant_phone_route_language') THEN
    ALTER TABLE tenant_phone_numbers
      ADD CONSTRAINT ck_tenant_phone_route_language
      CHECK (route_language IN ('tenant_default', 'en', 'hi'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_tenant_phone_e164') THEN
    ALTER TABLE tenant_phone_numbers
      ADD CONSTRAINT ck_tenant_phone_e164
      CHECK (phone_number ~ '^\+[1-9][0-9]{7,14}$');
  END IF;
END
$$;

COMMENT ON COLUMN suppliers.auth_pin IS
  'Legacy plaintext caller PIN; nullable and cleared whenever a PIN is set or successfully migrated';
COMMENT ON COLUMN suppliers.auth_pin_hash IS
  'Salted PBKDF2-HMAC-SHA256 caller PIN verifier; never expose through APIs or logs';
COMMENT ON COLUMN suppliers.pin_updated_at IS
  'Timestamp of the latest caller PIN set, reset, import, or legacy-hash migration';
COMMENT ON COLUMN suppliers.pin_failed_attempts IS
  'Persistent failed-PIN counter surviving across sessions/calls; resets to 0 on success or owner reset';
COMMENT ON COLUMN suppliers.pin_locked_until IS
  'When set and in the future, verify_pin fails closed regardless of the submitted PIN';
COMMENT ON COLUMN tenant_phone_numbers.verification_mode IS
  'standard requires knowledge verification for sensitive reads; enhanced also requires caller PIN';
COMMENT ON COLUMN tenant_phone_numbers.route_language IS
  'tenant_default, en, or hi language selected when a call session starts';
