-- 023_call_recordings_and_consent.sql
-- GDPR/ICO: IVR consent evidence + recording pointer on every inbound call.
-- Pairs with deploy/aws/s3_recordings_handler.py and the UK contact flow.

ALTER TABLE calls ADD COLUMN consent_granted INTEGER NOT NULL DEFAULT 0;
ALTER TABLE calls ADD COLUMN consent_recorded_at TIMESTAMPTZ NULL;
ALTER TABLE calls ADD COLUMN consent_evidence_ref TEXT NOT NULL DEFAULT '';
ALTER TABLE calls ADD COLUMN recording_s3_key TEXT NOT NULL DEFAULT '';

CREATE INDEX ix_calls_consent_recorded_at ON calls (consent_recorded_at);

COMMENT ON COLUMN calls.consent_evidence_ref IS 'Immutable evidence string linking the recording to IVR consent (connect:<region>:<instance>:<contact>:consent=<state>:recorded=<y|n>:at=<iso>). Do not overwrite once set.';
