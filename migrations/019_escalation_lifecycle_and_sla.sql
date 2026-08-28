-- Migration 019: Escalation Lifecycle, SLAs, and Operator Ownership (Day 48)
-- Extends calls table with escalation state machine, SLA deadlines, and staff ownership.
-- Extends tenants table with configurable escalation SLA target minutes.

ALTER TABLE calls ADD COLUMN IF NOT EXISTS escalation_priority VARCHAR(16) DEFAULT 'medium';
ALTER TABLE calls ADD COLUMN IF NOT EXISTS escalation_status VARCHAR(16) DEFAULT 'none';
ALTER TABLE calls ADD COLUMN IF NOT EXISTS assigned_to_user_id VARCHAR(128);
ALTER TABLE calls ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE calls ADD COLUMN IF NOT EXISTS sla_due_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE calls ADD COLUMN IF NOT EXISTS resolved_by_user_id VARCHAR(128);
ALTER TABLE calls ADD COLUMN IF NOT EXISTS resolution_category VARCHAR(64);

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS escalation_sla_minutes INTEGER DEFAULT 60;

-- Backfill existing escalated / follow_up_required calls into pending/resolved escalation_status
UPDATE calls
SET escalation_status = 'resolved',
    resolution_category = COALESCE(NULLIF(resolution_category, ''), 'callback_completed')
WHERE (escalated = 1 OR follow_up_required = 1)
  AND staff_resolved_at IS NOT NULL
  AND (escalation_status IS NULL OR escalation_status = 'none');

UPDATE calls
SET escalation_status = 'pending',
    sla_due_at = COALESCE(sla_due_at, started_at + INTERVAL '60 minutes')
WHERE (escalated = 1 OR follow_up_required = 1)
  AND staff_resolved_at IS NULL
  AND (escalation_status IS NULL OR escalation_status = 'none');

-- Composite index for fast tenant-scoped queue queries and SLA breach sorting
CREATE INDEX IF NOT EXISTS idx_calls_tenant_escalation_sla
    ON calls (tenant_id, escalation_status, sla_due_at);

CREATE INDEX IF NOT EXISTS idx_calls_tenant_escalation_assigned
    ON calls (tenant_id, assigned_to_user_id);
