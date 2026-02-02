-- Feature 022: Reviewer Privacy (Dual-Channel Comments + Confidential Attachment)
-- Adds confidential reviewer fields to review_reports.

ALTER TABLE public.review_reports
  ADD COLUMN IF NOT EXISTS confidential_comments_to_editor TEXT;

ALTER TABLE public.review_reports
  ADD COLUMN IF NOT EXISTS attachment_path TEXT;

