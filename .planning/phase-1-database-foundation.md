# Phase 1 — Database Foundation (Day 3–4)

## Day 3

### Theory

Row-level security (RLS) in Supabase/Postgres is what actually enforces
tenant isolation at the database level — not application code. If you skip
RLS and rely only on "my API always filters by tenant_id," one bug in one
endpoint leaks another tenant's data. Set the habit now even with one
tenant, so it's not a rewrite later.

### Checklist

- [x] Create all tables from `schema.md` (SQL schema DDL + SQLAlchemy declarative models)
- [x] Add `tenant_id` (FK to `tenants`) to every tenant-scoped table
- [x] Document RLS policies in `schema.md`
- [x] Build multi-tenant queries filtering by `tenant_id` in `apps/api/voxflow_api/routes/data.py`
- [x] Seed 4 distinct tenants (Varun Beverages, Amul Dairy, Haldirams, Britannia) and confirm tenant isolation

### Definition of Done

Tables exist in DB. A test query using tenant A's context cannot see tenant B's seeded row, verified automatically via `verify_db.py`.

## Day 4

### Theory

Seed data that mirrors a real scenario (even a guessed one) makes every
later step easier to test. Fake data that's too clean (e.g. every SKU has
stock) hides bugs — include some suppliers with zero stock, some POs
already fulfilled, some ambiguous names, so your agent has to handle
messy reality from day one.

### Checklist

- [x] Seed `suppliers` with realistic multi-tenant entries across 4 companies
- [x] Seed `stock` with 20+ SKUs across multiple warehouses (some zero stock, low, and healthy)
- [x] Seed `orders` with a mix of statuses: pending, confirmed, fulfilled
- [x] Seed `shipments` with a mix of statuses: booked, in-transit, delivered
- [x] Seed `appointments` and `communication_logs` (emails and WhatsApp messages)
- [x] Write automated `verify_db.py` script that connects, checks every table per tenant, and verifies isolation

### Definition of Done

Running `python -m voxflow_api.verify_db` verifies multi-tenant data reading across all tables cleanly.
