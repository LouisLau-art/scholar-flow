-- Feature 028: Workflow and UI Standardization
-- 目标：记录稿件状态机每一次流转（审计/追踪/精确 updated_at 对齐）

CREATE TABLE IF NOT EXISTS public.status_transition_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  manuscript_id uuid NOT NULL REFERENCES public.manuscripts(id) ON DELETE CASCADE,
  from_status text,
  to_status text NOT NULL,
  comment text,
  changed_by uuid REFERENCES auth.users(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_status_transition_logs_manuscript_id ON public.status_transition_logs(manuscript_id);
CREATE INDEX IF NOT EXISTS idx_status_transition_logs_created_at ON public.status_transition_logs(created_at);

