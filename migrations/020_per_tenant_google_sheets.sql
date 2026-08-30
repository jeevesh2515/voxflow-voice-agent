-- Migration 020: Self-Serve Per-Tenant Google Sheets Integration
-- Allows each tenant workspace to connect, verify, and maintain their own Google Spreadsheet mirror.

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS google_sheet_id VARCHAR(128);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS google_sheet_name VARCHAR(255);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS google_sheet_tab VARCHAR(64) DEFAULT 'Call Log';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS google_sheet_email_tab VARCHAR(64) DEFAULT 'Email Log';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS google_sheet_connected_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS google_sheet_connected_by_user_id VARCHAR(128);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS google_sheet_status VARCHAR(32) DEFAULT 'disconnected';

CREATE INDEX IF NOT EXISTS idx_tenants_google_sheet_id ON tenants(google_sheet_id) WHERE google_sheet_id IS NOT NULL;
