-- 修复历史数据：去重 review_assignments
-- 现象：
-- - 同一个稿件（manuscript_id）同一个审稿人（reviewer_id）在同一轮次（round_number）可能被重复插入多条
-- - UI 会显示 reviewers: 2（实际上是同一人被算了两次）
--
-- 原因：
-- - 之前后端未做幂等保护，且数据库层也未加唯一约束
--
-- 用法（Supabase Dashboard → SQL Editor 执行）：
-- 1) 先执行“预览重复”
-- 2) 再执行“删除重复（保留最新）”
-- 3) 可选：创建唯一索引，防止未来再出现

-- =========
-- 预览：找出重复组
-- =========
select
  manuscript_id,
  reviewer_id,
  coalesce(round_number, 1) as round_number,
  count(*) as dup_count
from public.review_assignments
group by manuscript_id, reviewer_id, coalesce(round_number, 1)
having count(*) > 1
order by dup_count desc;

-- =========
-- 删除：每组只保留 created_at 最新的一条
-- =========
-- begin;
-- with ranked as (
--   select
--     id,
--     row_number() over (
--       partition by manuscript_id, reviewer_id, coalesce(round_number, 1)
--       order by created_at desc nulls last, id desc
--     ) as rn
--   from public.review_assignments
-- )
-- delete from public.review_assignments ra
-- using ranked r
-- where ra.id = r.id
--   and r.rn > 1;
-- commit;

-- =========
-- 可选：加唯一索引（注意：必须先去重，否则会失败）
-- =========
-- do $$
-- begin
--   if exists (
--     select 1
--     from information_schema.columns
--     where table_schema='public' and table_name='review_assignments' and column_name='round_number'
--   ) then
--     execute 'create unique index if not exists uq_review_assignments_round on public.review_assignments(manuscript_id, reviewer_id, round_number)';
--   else
--     execute 'create unique index if not exists uq_review_assignments_round on public.review_assignments(manuscript_id, reviewer_id)';
--   end if;
-- end $$;

