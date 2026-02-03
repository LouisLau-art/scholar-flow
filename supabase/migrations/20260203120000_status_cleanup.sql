-- MVP status cleanup
-- Background:
-- - Earlier versions mistakenly used `revision_required` to represent rejection in some flows.
-- - Current canonical statuses:
--   - revision_requested: waiting for author revision
--   - rejected: final rejection

update public.manuscripts
set status = 'rejected'
where status = 'revision_required';

