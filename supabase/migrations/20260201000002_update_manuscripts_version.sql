-- Add version column to manuscripts table
-- This tracks the current active version number for each manuscript

ALTER TABLE public.manuscripts 
ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

-- Add comment for documentation
COMMENT ON COLUMN public.manuscripts.version IS 'Current active version number, starts at 1 for initial submission';
