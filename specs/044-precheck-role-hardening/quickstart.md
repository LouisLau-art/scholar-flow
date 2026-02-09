# Quickstart: GAP-P0-01 Pre-check Role Hardening

## 1. 前置条件

1. 当前分支：`044-precheck-role-hardening`
2. 已配置并可访问云端 Supabase（project ref: `mmvulyrfsorqdpdrzbkd`）
3. 本地已准备：
   - 后端依赖（`uv`）
   - 前端依赖（`bun`）
4. 迁移 `supabase/migrations/20260206150000_add_precheck_fields.sql` 已在目标环境生效

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
select column_name
from information_schema.columns
where table_schema='public'
  and table_name='manuscripts'
  and column_name in ('assistant_editor_id', 'pre_check_status');
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

## 4. 后端回归（预审主路径）

```bash
cd /root/scholar-flow/backend

# 单文件验证，跳过全局覆盖率门槛（仓库约定）
pytest -o addopts= \
  tests/contract/test_api_paths.py \
  tests/integration/test_editor_http_methods.py \
  tests/integration/test_editor_service.py \
  tests/integration/test_precheck_flow.py \
  tests/unit/test_precheck_role_service.py
```

验收重点：
- ME 能分派 AE，非 ME 被拒绝。
- AE 仅能处理自己被分派稿件。
- AE `revision` 必填 comment。
- EIC 仅在 `academic` 阶段可提交 `review/decision_phase`。
- 预审中禁止直接拒稿。

## 5. 前端回归（mocked E2E）

```bash
cd /root/scholar-flow/frontend

# 仅跑预审工作流 spec
bun run test:e2e tests/e2e/specs/precheck_workflow.spec.ts
```

验收重点：
- Process 列表可触发并展示预审动作结果。
- 预审阶段、责任角色、关键时间点在列表/详情可见。
- ME -> AE -> EIC 主路径可连续通过。

## 6. 本次实现验收记录（2026-02-09）

执行命令与结果：

```bash
# Frontend 单测（precheck API + ManuscriptTable）
cd /root/scholar-flow/frontend
bun run test:run src/components/editor/__tests__/manuscript-table.precheck.test.tsx src/tests/services/editor/precheck.api.test.ts
# => Test Files 2 passed, Tests 6 passed

# Frontend E2E（mocked precheck workflow）
bun run test:e2e tests/e2e/specs/precheck_workflow.spec.ts --project=chromium
# => 1 passed

# Backend 预审回归（contract + integration + unit）
cd /root/scholar-flow/backend
pytest -o addopts= tests/contract/test_api_paths.py tests/integration/test_editor_http_methods.py tests/integration/test_editor_service.py tests/integration/test_precheck_flow.py tests/unit/test_precheck_role_service.py
# => 18 passed, 3 skipped
```

说明：
- `tests/integration/test_editor_service.py` 的 3 个用例在云端缺少 `pre_check_status/assistant_editor_id` 等列时会 `skip`（PGRST204），符合仓库“云端 schema 漂移可跳过”的约定。

## 7. 手工 API 冒烟（可选）

以下示例假设你已拿到不同角色用户 token。

```bash
BASE_URL="http://127.0.0.1:8000"
MANUSCRIPT_ID="<pre_check_manuscript_uuid>"
AE_ID="<assistant_editor_uuid>"

# 1) ME 分派 AE
curl -X POST "$BASE_URL/api/v1/editor/manuscripts/$MANUSCRIPT_ID/assign-ae" \
  -H "Authorization: Bearer <ME_TOKEN>" \
  -H "Content-Type: application/json" \
  -d "{\"ae_id\":\"$AE_ID\"}"

# 2) AE 技术质检通过
curl -X POST "$BASE_URL/api/v1/editor/manuscripts/$MANUSCRIPT_ID/submit-check" \
  -H "Authorization: Bearer <AE_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"decision":"pass","comment":"format check passed"}'

# 3) EIC 学术初审送外审
curl -X POST "$BASE_URL/api/v1/editor/manuscripts/$MANUSCRIPT_ID/academic-check" \
  -H "Authorization: Bearer <EIC_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"decision":"review","comment":"scope and novelty are acceptable"}'
```

## 8. 审计验证

```sql
select
  manuscript_id,
  from_status,
  to_status,
  comment,
  payload,
  changed_by,
  created_at
from public.status_transition_logs
where manuscript_id = '<pre_check_manuscript_uuid>'
order by created_at asc;
```

预期：
- 能看到分派、技术质检、学术初审动作；
- `payload.action` 与 `pre_check_from/pre_check_to` 可读；
- `changed_by` 与 `created_at` 完整可追溯。
