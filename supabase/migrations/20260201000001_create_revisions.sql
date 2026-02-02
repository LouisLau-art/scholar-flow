-- Create revisions table for tracking revision requests
-- This table tracks the workflow context for each revision cycle

CREATE TABLE IF NOT EXISTS public.revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manuscript_id UUID NOT NULL REFERENCES public.manuscripts(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL DEFAULT 1,
    decision_type TEXT NOT NULL CHECK (decision_type IN ('major', 'minor')),
    editor_comment TEXT NOT NULL,
    response_letter TEXT,  -- Author's response (Rich Text), null until submitted
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'submitted')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE,
    
    -- Ensure manuscript_id + round_number is unique
    UNIQUE (manuscript_id, round_number)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_revisions_manuscript_id ON public.revisions(manuscript_id);
CREATE INDEX IF NOT EXISTS idx_revisions_status ON public.revisions(status);

-- Enable RLS for revisions table
ALTER TABLE public.revisions ENABLE ROW LEVEL SECURITY;

-- Editors and admins can view and manage all revisions
CREATE POLICY "Editors can view all revisions" 
ON public.revisions FOR SELECT 
TO authenticated 
USING (
    EXISTS (
        SELECT 1 FROM public.user_profiles 
        WHERE id = auth.uid() 
        AND (roles @> ARRAY['editor']::text[] OR roles @> ARRAY['admin']::text[])
    )
);

CREATE POLICY "Editors can insert revisions" 
ON public.revisions FOR INSERT 
TO authenticated 
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.user_profiles 
        WHERE id = auth.uid() 
        AND (roles @> ARRAY['editor']::text[] OR roles @> ARRAY['admin']::text[])
    )
);

CREATE POLICY "Editors can update revisions" 
ON public.revisions FOR UPDATE 
TO authenticated 
USING (
    EXISTS (
        SELECT 1 FROM public.user_profiles 
        WHERE id = auth.uid() 
        AND (roles @> ARRAY['editor']::text[] OR roles @> ARRAY['admin']::text[])
    )
);

-- Authors can view revisions for their own manuscripts
CREATE POLICY "Authors can view their own revisions" 
ON public.revisions FOR SELECT 
TO authenticated 
USING (
    EXISTS (
        SELECT 1 FROM public.manuscripts 
        WHERE id = revisions.manuscript_id 
        AND author_id = auth.uid()
    )
);

-- Authors can update (submit response) their own revisions
CREATE POLICY "Authors can update their own revisions" 
ON public.revisions FOR UPDATE 
TO authenticated 
USING (
    EXISTS (
        SELECT 1 FROM public.manuscripts 
        WHERE id = revisions.manuscript_id 
        AND author_id = auth.uid()
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.manuscripts 
        WHERE id = revisions.manuscript_id 
        AND author_id = auth.uid()
    )
);
