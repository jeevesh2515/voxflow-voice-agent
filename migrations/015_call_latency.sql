-- 015_call_latency.sql
-- Day 42: persist mean per-turn server processing latency on calls.

ALTER TABLE calls
  ADD COLUMN IF NOT EXISTS avg_turn_latency_ms INTEGER NOT NULL DEFAULT 0;
