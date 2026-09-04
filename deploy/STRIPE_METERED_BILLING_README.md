# VoxFlow - Stripe Metered-Usage Billing (Per Call-Minute)

Uses **Stripe Billing Meters** (meter events) - the current supported API.
The legacy `usage_records` path is deprecated; Stripe removed support for
legacy usage-based prices (changelog 2025-03-31:
https://docs.stripe.com/changelog/basil/2025-03-31/deprecate-legacy-usage-based-billing).
Migration guide: https://docs.stripe.com/billing/subscriptions/usage-based-legacy/migration-guide
Meter event reference: https://docs.stripe.com/api/billing/meter-event/create

---

## 1. Files & Architecture

- `apps/api/voxflow_api/services/metering_service.py` - core: read calls,
  round to minutes, send meter events, mark billed. Idempotency via the
  `identifier` field + `metering_billed_at` flag.
- `apps/api/voxflow_api/services/retry.py` - transient/permanent
  classification + exponential backoff + jitter (same semantics as the
  recording Lambda layer).
- `scripts/run_meter_report.py` - periodic job entrypoint (dry-run by
  default; `--execute` sends).
- `migrations/024_call_metering.sql` - two columns + partial index.

---

## 2. Stripe Dashboard Setup (Once)

1. Create a Product (e.g. "VoxFlow Voice").
2. Create a Billing Meter:
   - `event_name` = `voxflow_voice_minutes` (must match `STRIPE_METER_EVENT_NAME`)
   - `event_payload_key` = `value`
   - Customer mapping: `stripe_customer_id` (default payload key)
   - Aggregation: `sum`
3. Create a metered Price on that meter and attach it to each tenant's
   Subscription (starter/growth) as a recurring price. Enterprise (unmetered,
   `included_minutes: 0`) does not need it.
   Docs: https://docs.stripe.com/billing/subscriptions/usage-based-legacy/migrate-to-meters
4. Configure Stripe's usage-reporting reminder email (optional) or rely on the
   hourly job.

---

## 3. Application Configuration

- In `config.py` Settings:
  `stripe_meter_event_name: str = "voxflow_voice_minutes"`
- In `.env.example`:
  ```bash
  STRIPE_METER_EVENT_NAME=voxflow_voice_minutes
  ```
- Ensure every billable Tenant row stores its Stripe customer id in `stripe_customer_id` (resolved at runtime; the tenant's subscription link already exists via the billing lifecycle in `services/billing_service.py`).
- Apply migration 024 and verify `Call` model in `db.py`:
  ```python
  metering_billed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
  metering_event_id:  Mapped[str] = mapped_column(Text, default="")
  ```

---

## 4. Execution & Crontab

```bash
# Dry run (safe, default): prints what would be sent, sends nothing
python scripts/run_meter_report.py

# Send for real, hourly via cron
0 * * * * cd /srv/voxflow && ./.venv/bin/python scripts/run_meter_report.py --execute >> /var/log/voxflow-meter.log 2>&1
```

---

## 5. Rounding, Idempotency & Failure Handling

- **Minutes Rounding**: `ceil(duration_sec / 60)`, min 1 minute per completed call; falls back to `ended - started` wall-clock when `duration_sec == 0`; calls with no duration are skipped.
- **Idempotency**: Identifier `voxflow-call-meter-<call.id>` (Stripe de-duplicates within rolling >=24h window; cap 100 chars). `metering_billed_at` is set ONLY after Stripe accepts, so a crash between send and mark re-sends the same identifier and Stripe ignores the duplicate.
- **Timestamping**: `timestamp = unix(ended_at)` (usage time), so usage lands in the correct billing period.
- **Customer Lookup Resilience**: Missing Stripe customer id is skipped + logged per tenant, never aborting the whole batch.
- **Transient Stripe Errors**: 429/5xx/network errors retry 3x with exponential backoff + jitter, then abort the tenant (flag unset) so the NEXT hourly run picks them up. Permanent 4xx errors (e.g. invalid meter name, wrong key) are logged in the summary and NOT marked, surfacing for operator remediation.

---

## 6. Reconciliation SQL

Compare Stripe meter event summaries ([Stripe docs](https://docs.stripe.com/api/billing/meter-event-summary/list)) against:

```sql
SELECT tenant_id,
       count(*) FILTER (WHERE metering_billed_at IS NOT NULL) AS billed_calls,
       sum(ceil(duration_sec / 60.0))::int AS total_billed_minutes
FROM calls
GROUP BY tenant_id;
```
