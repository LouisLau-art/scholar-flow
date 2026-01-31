-- Feature 016: QA Regression
-- 为引用 auth.users 的外键补齐 ON DELETE 策略，便于测试环境清理/重置数据

-- manuscripts → auth.users
alter table public.manuscripts
  drop constraint if exists manuscripts_author_id_fkey;
alter table public.manuscripts
  add constraint manuscripts_author_id_fkey
  foreign key (author_id) references auth.users(id) on delete set null;

alter table public.manuscripts
  drop constraint if exists manuscripts_editor_id_fkey;
alter table public.manuscripts
  add constraint manuscripts_editor_id_fkey
  foreign key (editor_id) references auth.users(id) on delete set null;

alter table public.manuscripts
  drop constraint if exists manuscripts_kpi_owner_id_fkey;
alter table public.manuscripts
  add constraint manuscripts_kpi_owner_id_fkey
  foreign key (kpi_owner_id) references auth.users(id) on delete set null;

-- review_reports → auth.users
alter table public.review_reports
  drop constraint if exists review_reports_reviewer_id_fkey;
alter table public.review_reports
  add constraint review_reports_reviewer_id_fkey
  foreign key (reviewer_id) references auth.users(id) on delete set null;

-- doi_audit_log → auth.users
alter table public.doi_audit_log
  drop constraint if exists doi_audit_log_created_by_fkey;
alter table public.doi_audit_log
  add constraint doi_audit_log_created_by_fkey
  foreign key (created_by) references auth.users(id) on delete set null;

