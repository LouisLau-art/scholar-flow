-- Feature 029: Manuscript Details and Invoice Info Management
-- 目标：为 status_transition_logs 增加 payload（JSONB）用于记录敏感变更（例如 invoice_metadata 的 before/after）

ALTER TABLE public.status_transition_logs
  ADD COLUMN IF NOT EXISTS payload jsonb;

