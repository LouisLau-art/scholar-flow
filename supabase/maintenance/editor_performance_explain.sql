-- Editor 性能链路 EXPLAIN 脚本（Process / Workspace）
-- 用法：
-- 1) 在 Supabase Dashboard -> SQL Editor 执行
-- 2) 把 manuscript/owner/editor/journal/assistant_editor 的 UUID 替换成真实数据（可选）
-- 3) 对比 migration 前后执行计划与总耗时

-- 1) Process 主查询（按状态 + 更新时间排序）
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT id, title, status, updated_at, created_at, owner_id, editor_id, assistant_editor_id, journal_id
FROM public.manuscripts
WHERE status IN ('pre_check', 'under_review', 'decision', 'approved')
ORDER BY updated_at DESC, created_at DESC
LIMIT 80;

-- 2) Process - 按 owner 过滤
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT id, title, status, updated_at, created_at
FROM public.manuscripts
WHERE owner_id = '00000000-0000-0000-0000-000000000000'
  AND status IN ('pre_check', 'under_review', 'decision')
ORDER BY updated_at DESC, created_at DESC
LIMIT 80;

-- 3) AE workspace（assistant_editor + status）
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT id, title, status, pre_check_status, assistant_editor_id, updated_at, created_at
FROM public.manuscripts
WHERE assistant_editor_id = '00000000-0000-0000-0000-000000000000'
  AND status IN ('pre_check', 'under_review', 'major_revision', 'minor_revision', 'resubmitted', 'decision')
ORDER BY updated_at DESC, created_at DESC
LIMIT 80;

-- 4) ME workspace（status scope）
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT id, title, status, pre_check_status, owner_id, assistant_editor_id, journal_id, updated_at, created_at
FROM public.manuscripts
WHERE status IN (
  'pre_check', 'under_review', 'major_revision', 'minor_revision',
  'resubmitted', 'decision', 'decision_done', 'approved',
  'layout', 'english_editing', 'proofreading'
)
ORDER BY updated_at DESC, created_at DESC
LIMIT 80;

-- 5) 标题模糊搜索（验证 trgm 索引）
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT id, title, status, updated_at
FROM public.manuscripts
WHERE title ILIKE '%energy%'
ORDER BY updated_at DESC
LIMIT 50;

