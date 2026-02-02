-- Create manuscript_versions table
CREATE TABLE IF NOT EXISTS public.manuscript_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manuscript_id UUID NOT NULL REFERENCES public.manuscripts(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    title TEXT,
    abstract TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    
    -- Ensure manuscript_id + version_number is unique
    UNIQUE (manuscript_id, version_number)
);

-- Add RLS policies for manuscript_versions
ALTER TABLE public.manuscript_versions ENABLE ROW LEVEL SECURITY;

-- Editors can view all versions
CREATE POLICY "Editors can view all manuscript versions" 
ON public.manuscript_versions FOR SELECT 
TO authenticated 
USING (
    EXISTS (
        SELECT 1 FROM public.user_profiles 
        WHERE id = auth.uid() 
        AND roles @> ARRAY['editor']::text[]
    )
    OR 
    EXISTS (
        SELECT 1 FROM public.user_profiles 
        WHERE id = auth.uid() 
        AND roles @> ARRAY['admin']::text[]
    )
);

-- Authors can view their own versions
CREATE POLICY "Authors can view their own manuscript versions" 
ON public.manuscript_versions FOR SELECT 
TO authenticated 
USING (
    EXISTS (
        SELECT 1 FROM public.manuscripts 
        WHERE id = manuscript_versions.manuscript_id 
        AND author_id = auth.uid()
    )
);

-- Reviewers can view versions for manuscripts they are assigned to
CREATE POLICY "Reviewers can view assigned manuscript versions" 
ON public.manuscript_versions FOR SELECT 
TO authenticated 
USING (
    EXISTS (
        SELECT 1 FROM public.review_assignments 
        WHERE manuscript_id = manuscript_versions.manuscript_id 
        AND reviewer_id = auth.uid()
    )
);

-- Authors can insert their own versions (via API)
CREATE POLICY "Authors can insert own manuscript versions" 
ON public.manuscript_versions FOR INSERT 
TO authenticated 
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.manuscripts 
        WHERE id = manuscript_versions.manuscript_id 
        AND author_id = auth.uid()
    )
);
