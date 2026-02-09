# Quickstart: GAP-P0-03 Internal Collaboration Enhancement

## 1. 前置条件

1. 当前分支：`045-internal-collaboration-enhancement`
2. 已配置并可访问云端 Supabase（project ref: `mmvulyrfsorqdpdrzbkd`）
3. 本地已准备：
   - 后端依赖（`uv`）
   - 前端依赖（`bun`）
4. 目标环境已应用本特性迁移（internal mention/task 相关表）

## 2. 环境与迁移校验

```bash
cd /root/scholar-flow

# 检查 linked 项目
supabase projects list

# 预览迁移变更
supabase db push --linked --dry-run
```

最小校验 SQL：

```sql
select table_name
from information_schema.tables
where table_schema='public'
  and table_name in (
    'internal_comments',
    'internal_comment_mentions',
    'internal_tasks',
    'internal_task_activity_logs'
  );
```

## 3. 启动本地服务

```bash
# 终端 1：Backend
cd /root/scholar-flow/backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 终端 2：Frontend
cd /root/scholar-flow/frontend
bun run dev -- --port 3000
```

## 4. 后端回归（提及 + 任务 + 逾期）

```bash
cd /root/scholar-flow/backend

# 单文件验证，跳过全局覆盖率门槛（仓库约定）
uv run pytest -o addopts= \
  tests/contract/test_api_paths.py \
  tests/integration/test_internal_collaboration_flow.py \
  tests/integration/test_editor_service.py::test_process_overdue_only_query_param_is_forwarded \
  tests/unit/test_internal_collaboration_service.py \
  tests/unit/test_internal_task_service.py \
  tests/unit/test_editor_service.py
```

验收重点：
- 评论携带提及对象后可生成一次性提醒（无重复提醒）。
- 任务创建/更新会记录操作轨迹。
- Process 列表 `overdue_only` 筛选与 `overdue_tasks_count` 聚合准确。

### 2026-02-09 实测结果（本分支）

执行命令：

```bash
cd /root/scholar-flow/backend
uv run pytest -o addopts= \
  tests/contract/test_api_paths.py \
  tests/unit/test_internal_collaboration_service.py \
  tests/unit/test_internal_task_service.py \
  tests/unit/test_editor_service.py \
  tests/integration/test_internal_collaboration_flow.py \
  tests/integration/test_editor_service.py::test_process_overdue_only_query_param_is_forwarded
```

结果：`15 passed`。

## 5. 前端回归（详情 + Process）

```bash
cd /root/scholar-flow/frontend

# 单测（Notebook 提及 + Task 面板渲染）
bun run test:run \
  src/components/editor/__tests__/internal-notebook-mentions.test.tsx \
  src/components/editor/__tests__/internal-tasks-panel.test.tsx

# E2E（mocked 协作主路径）
bun run test:e2e tests/e2e/specs/internal-collaboration-overdue.spec.ts --project=chromium
```

验收重点：
- 在稿件详情发布带 `@mentions` 评论后，列表即时显示。
- 可创建任务并更新到完成状态。
- Process 可筛选仅逾期稿件，且逾期标识与详情一致。

### 2026-02-09 实测结果（本分支）

执行命令：

```bash
cd /root/scholar-flow/frontend
bun run test:run \
  src/components/editor/__tests__/internal-notebook-mentions.test.tsx \
  src/components/editor/__tests__/internal-tasks-panel.test.tsx \
  src/components/editor/__tests__/manuscript-table.overdue.test.tsx \
  src/components/editor/__tests__/manuscript-table.precheck.test.tsx

bun run test:e2e tests/e2e/specs/internal-collaboration-overdue.spec.ts --project=chromium
```

结果：Vitest `7 passed`，Playwright `1 passed`。

补充检查：

```bash
cd /root/scholar-flow/frontend
bun run lint
```

结果：命令成功，存在仓库既有的 `react-hooks/exhaustive-deps` 警告（非本特性新增阻塞）。

## 6. 手工 API 冒烟（可选）

```bash
BASE_URL="http://127.0.0.1:8000"
MANUSCRIPT_ID="<manuscript_uuid>"
ASSIGNEE_ID="<internal_user_uuid>"
MENTION_ID="<internal_user_uuid>"

# 1) 发布带提及的内部评论
curl -X POST "$BASE_URL/api/v1/editor/manuscripts/$MANUSCRIPT_ID/comments" \
  -H "Authorization: Bearer <EDITOR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d "{\"content\":\"@$MENTION_ID 请确认统计口径\",\"mention_user_ids\":[\"$MENTION_ID\"]}"

# 2) 创建内部任务
curl -X POST "$BASE_URL/api/v1/editor/manuscripts/$MANUSCRIPT_ID/tasks" \
  -H "Authorization: Bearer <EDITOR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"补充图表说明\",\"assignee_user_id\":\"$ASSIGNEE_ID\",\"due_at\":\"2026-02-11T12:00:00Z\"}"

# 3) 查看仅逾期稿件
curl -X GET "$BASE_URL/api/v1/editor/manuscripts/process?overdue_only=true" \
  -H "Authorization: Bearer <EDITOR_TOKEN>"
```

## 7. 审计验证

```sql
select id, task_id, action, actor_user_id, before_payload, after_payload, created_at
from public.internal_task_activity_logs
where manuscript_id = '<manuscript_uuid>'
order by created_at asc;
```

预期：
- 任务创建、状态更新、负责人变更等动作可追踪；
- 变更前后值可用于复盘；
- 操作者与时间戳完整。
