-- Feature 036: Internal Collaboration (Notebook)
-- Goal: Create a dedicated table for internal staff discussions on a manuscript.

CREATE TABLE IF NOT EXISTS public.internal_comments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  manuscript_id uuid NOT NULL REFERENCES public.manuscripts(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id),
  content text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_internal_comments_manuscript_id ON public.internal_comments(manuscript_id);
CREATE INDEX IF NOT EXISTS idx_internal_comments_created_at ON public.internal_comments(created_at);

-- RLS Policies
ALTER TABLE public.internal_comments ENABLE ROW LEVEL SECURITY;

-- Only authenticated users (likely staff) can read/write
-- Ideally we check user_profiles.is_internal_staff, but for MVP checking auth is a good start.
-- Assuming Editor/Admin roles are enforced via application logic or broader policies.

CREATE POLICY "Internal staff can view comments"
  ON public.internal_comments FOR SELECT
  USING (auth.uid() IN (
    SELECT id FROM public.user_profiles WHERE is_internal_staff = true
  ));

CREATE POLICY "Internal staff can insert comments"
  ON public.internal_comments FOR INSERT
  WITH CHECK (auth.uid() IN (
    SELECT id FROM public.user_profiles WHERE is_internal_staff = true
  ));

CREATE POLICY "Staff can update their own comments"
  ON public.internal_comments FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Staff can delete their own comments"
  ON public.internal_comments FOR DELETE
  USING (auth.uid() = user_id);
