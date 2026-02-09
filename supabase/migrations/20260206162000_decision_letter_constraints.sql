-- Feature 041: constraints/indexes for draft uniqueness and optimistic locking

-- 每个 manuscript + editor 仅允许 1 条草稿，避免并发产生多条 draft
create unique index if not exists idx_decision_letters_one_draft_per_editor
  on public.decision_letters (manuscript_id, editor_id)
  where status = 'draft';

-- 附件引用检索
create index if not exists idx_decision_letters_attachment_paths_gin
  on public.decision_letters using gin (attachment_paths);

-- 更新时间戳触发器（若客户端未显式传 updated_at，DB 自动刷新）
create or replace function public.tg_set_decision_letters_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_set_decision_letters_updated_at on public.decision_letters;
create trigger trg_set_decision_letters_updated_at
before update on public.decision_letters
for each row execute function public.tg_set_decision_letters_updated_at();
