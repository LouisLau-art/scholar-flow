-- Add round_number column to review_assignments table
-- This tracks which revision round this review belongs to

ALTER TABLE public.review_assignments 
ADD COLUMN IF NOT EXISTS round_number INTEGER NOT NULL DEFAULT 1;

-- Create index for querying by round
CREATE INDEX IF NOT EXISTS idx_review_assignments_round ON public.review_assignments(manuscript_id, round_number);

-- Add comment for documentation
COMMENT ON COLUMN public.review_assignments.round_number IS 'Tracks which review round this assignment belongs to (1 = initial, 2+ = post-revision)';
