-- 023_call_recordings_and_consent.sql
-- GDPR/ICO: IVR consent evidence + recording pointer on every inbound call.
-- Pairs with deploy/aws/s3_recordings_handler.py and the UK contact flow.

ALTER TABLE calls ADD COLUMN IF NOT EXISTS consent_granted INTEGER NOT NULL DEFAULT 0;
ALTER TABLE calls ADD COLUMN IF NOT EXISTS consent_recorded_at TIMESTAMPTZ NULL;
ALTER TABLE calls ADD COLUMN IF NOT EXISTS consent_evidence_ref TEXT NOT NULL DEFAULT '';
ALTER TABLE calls ADD COLUMN IF NOT EXISTS recording_s3_key TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS ix_calls_consent_recorded_at ON calls (consent_recorded_at);

COMMENT ON COLUMN calls.consent_evidence_ref IS 'Immutable evidence string linking the recording to IVR consent. Format connect:region:instance:contact:consent=state:recorded=y_or_n:at=iso. Do not overwrite once set.';
