-- 清理云端 Supabase 中“孤儿 user_profiles”
-- 背景：
-- - public.user_profiles.id 目前未强制 FK 到 auth.users(id)
-- - 若存在“非真实 Auth 用户”的 mock profile（例如 big_mock_seed.sql / big_mock_seed_v2.sql 写入），
--   后端在通知/分配审稿等流程里会把这些 id 当成真实用户，从而触发外键错误：
--   notifications.user_id / review_assignments.reviewer_id 都引用 auth.users(id)
--
-- 用法（推荐在 Supabase Dashboard → SQL Editor 执行）：
-- 1) 先跑“预览”确认影响范围
-- 2) 再跑“删除”语句
--
-- 注意：
-- - 该脚本仅删除 “不在 auth.users 的 user_profiles”，不会影响真实登录用户。
-- - 删除后如需要 reviewer/editor 账号，请在 Auth → Users 创建真实用户，再用 Admin UI 赋予角色。

-- =========
-- 预览：孤儿 profile 列表
-- =========
select
  up.id,
  up.email,
  up.roles,
  up.created_at
from public.user_profiles up
left join auth.users au on au.id = up.id
where au.id is null
order by up.created_at desc;

-- =========
-- 预览：按角色统计（便于判断哪些会影响通知/分配）
-- =========
select
  coalesce(r.role, '(no role)') as role,
  count(*) as cnt
from public.user_profiles up
left join auth.users au on au.id = up.id
left join lateral unnest(up.roles) as r(role) on true
where au.id is null
group by 1
order by cnt desc;

-- =========
-- 删除：孤儿 profile（先在 Dashboard 里确认后再执行）
-- =========
-- begin;
-- delete from public.user_profiles up
-- where not exists (
--   select 1 from auth.users au where au.id = up.id
-- );
-- commit;

