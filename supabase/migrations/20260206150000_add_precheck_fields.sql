-- Feature 038: Pre-check Role Workflow Fields
-- Date: 2026-02-06
-- Purpose: Support ME -> AE -> EIC workflow by adding AE assignment and granular pre-check sub-status.

ALTER TABLE public.manuscripts
ADD COLUMN IF NOT EXISTS assistant_editor_id UUID REFERENCES public.user_profiles(id),
ADD COLUMN IF NOT EXISTS pre_check_status TEXT DEFAULT 'intake';

COMMENT ON COLUMN public.manuscripts.assistant_editor_id IS 'Assigned Assistant Editor for technical check';
COMMENT ON COLUMN public.manuscripts.pre_check_status IS 'Sub-status for PRE_CHECK: intake (ME), technical (AE), academic (EIC)';

CREATE INDEX IF NOT EXISTS idx_manuscripts_assistant_editor_id ON public.manuscripts(assistant_editor_id);
CREATE INDEX IF NOT EXISTS idx_manuscripts_pre_check_status ON public.manuscripts(pre_check_status);
