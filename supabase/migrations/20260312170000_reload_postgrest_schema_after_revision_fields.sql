-- Operational follow-up:
-- 20260312153000 added manuscript columns used by submission/pre-check flows.
-- Trigger PostgREST to refresh schema cache so hosted APIs can see the new columns.

select pg_notify('pgrst', 'reload schema');
