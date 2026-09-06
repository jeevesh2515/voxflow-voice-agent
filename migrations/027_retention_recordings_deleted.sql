-- 027_retention_recordings_deleted.sql
-- Phase 4 step 4: the purge audit log must record how many stored recording
-- objects were actually deleted, not just how many rows were anonymized.
-- Nulling calls.recording_url without deleting the S3 object orphans audio;
-- retention_service.delete_recording_object removes the bytes, and this column
-- is where the count lands so the enforcement is auditable per run.

ALTER TABLE retention_purge_logs
    ADD COLUMN IF NOT EXISTS recordings_deleted INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN retention_purge_logs.recordings_deleted IS
    'Stored recording objects (S3) actually deleted by this purge run.';
