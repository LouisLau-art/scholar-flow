-- Upgrade user_profiles table for Feature 018 (User Profile & Security Center)

ALTER TABLE public.user_profiles
ADD COLUMN IF NOT EXISTS full_name text,
ADD COLUMN IF NOT EXISTS avatar_url text,
ADD COLUMN IF NOT EXISTS affiliation text,
ADD COLUMN IF NOT EXISTS title text,
ADD COLUMN IF NOT EXISTS orcid_id text,
ADD COLUMN IF NOT EXISTS google_scholar_url text,
ADD COLUMN IF NOT EXISTS research_interests text[] DEFAULT '{}'::text[];

-- Add indexes for search/filtering if needed (e.g., full_name)
CREATE INDEX IF NOT EXISTS idx_user_profiles_full_name ON public.user_profiles(full_name);
