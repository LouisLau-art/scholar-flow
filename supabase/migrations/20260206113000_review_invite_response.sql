-- Feature 037: reviewer invite response workflow (accept/decline + timeline)

alter table public.review_assignments
  add column if not exists invited_at timestamptz null,
  add column if not exists opened_at timestamptz null,
  add column if not exists accepted_at timestamptz null,
  add column if not exists declined_at timestamptz null,
  add column if not exists decline_reason text null,
  add column if not exists decline_note text null;

-- 历史数据兜底：把 invited_at 回填为 created_at，避免 timeline 空洞
update public.review_assignments
set invited_at = coalesce(invited_at, created_at)
where invited_at is null;

create index if not exists idx_review_assignments_invite_timeline
  on public.review_assignments (manuscript_id, reviewer_id, invited_at desc);

