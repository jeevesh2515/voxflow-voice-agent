-- 018_tenant_agent_settings.sql
-- Day 47: Per-Tenant Agent Settings & Voice Persona Configuration
--
-- Adds server-authoritative tenant configuration columns for voice persona,
-- business hours with timezone awareness, and fallback escalation rules.

ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS voice_persona VARCHAR(32) DEFAULT 'professional' NOT NULL,
    ADD COLUMN IF NOT EXISTS business_hours_enabled INTEGER DEFAULT 0 NOT NULL,
    ADD COLUMN IF NOT EXISTS business_hours_start VARCHAR(8) DEFAULT '09:00' NOT NULL,
    ADD COLUMN IF NOT EXISTS business_hours_end VARCHAR(8) DEFAULT '18:00' NOT NULL,
    ADD COLUMN IF NOT EXISTS business_hours_timezone VARCHAR(64) DEFAULT 'Asia/Kolkata' NOT NULL,
    ADD COLUMN IF NOT EXISTS business_days VARCHAR(64) DEFAULT 'mon,tue,wed,thu,fri' NOT NULL,
    ADD COLUMN IF NOT EXISTS out_of_hours_message TEXT,
    ADD COLUMN IF NOT EXISTS fallback_escalation_mode VARCHAR(32) DEFAULT 'human_callback' NOT NULL,
    ADD COLUMN IF NOT EXISTS fallback_phone VARCHAR(32),
    ADD COLUMN IF NOT EXISTS fallback_email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS max_verification_failures INTEGER DEFAULT 3 NOT NULL;

COMMENT ON COLUMN tenants.voice_persona IS 'Persona style guideline: professional | friendly | concise | assertive';
COMMENT ON COLUMN tenants.business_hours_enabled IS '1 if operating hours are enforced/injected into prompt, 0 otherwise';
COMMENT ON COLUMN tenants.fallback_escalation_mode IS 'Escalation behavior: human_callback | transfer | voicemail';
