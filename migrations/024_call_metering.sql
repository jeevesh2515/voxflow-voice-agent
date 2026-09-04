-- 024_call_metering.sql
-- Stripe Billing Meter ledger on the calls table.
-- Pairs with apps/api/voxflow_api/services/metering_service.py and
-- scripts/run_meter_report.py.
--
-- metering_billed_at : set ONLY after Stripe accepted the meter event.
--                      NULL == pending (retry on the next run).
-- metering_event_id  : the stable identifier sent to Stripe
--                      ("voxflow-call-meter-<call.id>"); Stripe de-duplicates
--                      on it within a rolling >=24h window, so a crash between
--                      send and mark never double-bills.

ALTER TABLE calls
    ADD COLUMN metering_billed_at TIMESTAMPTZ NULL;

ALTER TABLE calls
    ADD COLUMN metering_event_id TEXT NOT NULL DEFAULT '';

-- Partial index: exactly the rows the hourly job scans.
CREATE INDEX ix_calls_metering_pending
    ON calls (metering_billed_at)
    WHERE metering_billed_at IS NULL;

COMMENT ON COLUMN calls.metering_event_id IS
    'Stripe Billing Meter event identifier; unique per call, deduped by Stripe >=24h.';
