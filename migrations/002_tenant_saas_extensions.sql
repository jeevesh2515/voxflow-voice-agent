-- ---------------------------------------------------------------------
-- VoxFlow SaaS Schema Migration 002: Tenant Extensions
-- Adds agent persona, prompt overrides, language, webhooks, and billing plan.
-- ---------------------------------------------------------------------

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS agent_name VARCHAR(64) DEFAULT 'Vaani';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS system_prompt_override TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS welcome_message TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS default_language VARCHAR(8) DEFAULT 'hi';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS webhook_url VARCHAR(512);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS webhook_secret VARCHAR(128);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS plan VARCHAR(32) DEFAULT 'pro';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS total_minutes_used FLOAT DEFAULT 0.0;
