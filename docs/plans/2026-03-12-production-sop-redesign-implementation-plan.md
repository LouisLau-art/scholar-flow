# Production SOP Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把当前 production MVP 重构为符合 10 步 SOP 的单一 production cycle 工作流，采用“稳定平台角色 + 每稿件责任人字段 + 独立产物/交接事件”模型，并移除详情页对 legacy production 线性推进的依赖。

**Architecture:** 在现有 `production_cycles + proofreading responses` 基础上做兼容扩展，而不是推倒重来。新增 `stage`、责任人字段、artifact/event 表，并把 `manuscripts.status` 降为兼容 bucket；所有 production 详细动作统一收口到 `production-workspace` 和 `proofreading` 页面。

**Tech Stack:** FastAPI 0.115+, Pydantic v2, Supabase PostgreSQL, Next.js 16 App Router, React 19, TypeScript 5, Vitest, Playwright, pytest

---

## Task 1: 先锁定新的 production 领域契约

**Files:**
- Modify: `backend/app/models/production_workspace.py`
- Modify: `frontend/src/types/production.ts`
- Test: `backend/tests/unit/test_production_workspace_service.py`
- Test: `frontend/tests/unit/production-workspace.test.tsx`

**Step 1: Write the failing tests**

补充后端/前端契约测试，锁定新字段存在：

- `stage`
- `coordinator_ae_id`
- `typesetter_id`
- `language_editor_id`
- `pdf_editor_id`
- `current_assignee_id`
- `artifact_kind`

并锁定旧 `status` 不再作为唯一 source of truth。

**Step 2: Run tests to verify they fail**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/unit/test_production_workspace_service.py -q
cd frontend && bun x vitest run tests/unit/production-workspace.test.tsx
```

Expected:

- FAIL，因为当前 model/type 里还没有这些字段与断言。

**Step 3: Write minimal implementation**

- 扩展 backend Pydantic model
- 扩展 frontend TS types
- 先不改业务逻辑，只让 contract 编译通过

**Step 4: Run tests to verify they pass**

Run the same commands.

**Step 5: Commit**

```bash
git add backend/app/models/production_workspace.py \
        frontend/src/types/production.ts \
        backend/tests/unit/test_production_workspace_service.py \
        frontend/tests/unit/production-workspace.test.tsx
git commit -m "feat: add production sop domain contracts"
```

## Task 2: 扩展数据库 schema 为 stage + artifacts + events

**Files:**
- Create: `supabase/migrations/20260312120000_production_sop_stage_artifacts_events.sql`
- Modify: `backend/app/models/production_workspace.py`
- Test: `backend/tests/integration/test_production_workspace_api.py`
- Test: `backend/tests/integration/test_proofreading_author_flow.py`

**Step 1: Write the failing tests**

补充集成测试，锁定数据库具备：

- `production_cycles.stage`
- 新责任人字段
- `production_cycle_artifacts`
- `production_cycle_events`
- `production_proofreading_responses` 附件字段

**Step 2: Run tests to verify they fail**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/integration/test_production_workspace_api.py tests/integration/test_proofreading_author_flow.py -q
```

Expected:

- FAIL，提示缺列或缺表。

**Step 3: Write minimal implementation**

- 新 migration 新增：
  - `stage`
  - `coordinator_ae_id`
  - `typesetter_id`
  - `language_editor_id`
  - `pdf_editor_id`
  - `current_assignee_id`
- 新建：
  - `production_cycle_artifacts`
  - `production_cycle_events`
- 扩展 author feedback attachment 字段
- 为历史 `production_cycles.status` 做 backfill 到 `stage`

**Step 4: Run tests to verify they pass**

Run the same command.

**Step 5: Commit**

```bash
git add supabase/migrations/20260312120000_production_sop_stage_artifacts_events.sql \
        backend/app/models/production_workspace.py \
        backend/tests/integration/test_production_workspace_api.py \
        backend/tests/integration/test_proofreading_author_flow.py
git commit -m "feat: extend production schema for sop workflow"
```

## Task 3: 实现新的 stage transition 与权限矩阵

**Files:**
- Modify: `backend/app/services/production_workspace_service.py`
- Modify: `backend/app/services/production_workspace_service_workflow_common.py`
- Modify: `backend/app/services/production_workspace_service_workflow_cycle.py`
- Modify: `backend/app/services/production_workspace_service_workflow_cycle_writes.py`
- Modify: `backend/app/services/production_workspace_service_workflow_cycle_context_queue.py`
- Modify: `backend/tests/unit/test_production_workspace_service.py`

**Step 1: Write the failing tests**

锁定：

- `assistant_editor` 只有在 `coordinator_ae_id` 命中时能写 production
- `production_editor` 只有在匹配当前责任字段和 stage 时能写
- 非当前责任人不能跨阶段上传 artifact
- `mark_ready_to_publish` 前必须已有 `final_confirmation_pdf` 和 `publication_pdf`

**Step 2: Run tests to verify they fail**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/unit/test_production_workspace_service.py -q
```

Expected:

- FAIL，因为当前权限仍是 legacy `production_editor/layout_editor_id` 口径。

**Step 3: Write minimal implementation**

- 新增 `stage -> allowed_actions` 映射
- 新增 `current_assignee_id` 与责任字段校验
- `production cycle` 事件写入统一 append-only log
- 兼容旧 `status` 读路径，但内部 transition 全部改按 `stage`

**Step 4: Run tests to verify they pass**

Run the same command.

**Step 5: Commit**

```bash
git add backend/app/services/production_workspace_service.py \
        backend/app/services/production_workspace_service_workflow_common.py \
        backend/app/services/production_workspace_service_workflow_cycle.py \
        backend/app/services/production_workspace_service_workflow_cycle_writes.py \
        backend/app/services/production_workspace_service_workflow_cycle_context_queue.py \
        backend/tests/unit/test_production_workspace_service.py
git commit -m "feat: add production sop stage transitions and permissions"
```

## Task 4: 重构 production API 为 assignments / artifacts / transitions

**Files:**
- Modify: `backend/app/api/v1/editor_production.py`
- Modify: `backend/app/api/v1/manuscripts.py`
- Modify: `backend/app/api/v1/manuscripts_detail_utils.py`
- Modify: `backend/tests/integration/test_production_workspace_api.py`
- Create: `backend/tests/integration/test_production_sop_flow.py`

**Step 1: Write the failing tests**

新增集成测试覆盖：

- `PATCH /production-cycles/{id}/assignments`
- `POST /production-cycles/{id}/artifacts`
- `POST /production-cycles/{id}/transitions`
- `POST /production-cycles/{id}/author-feedback`

并保留旧 `proofreading-context` 入口。

**Step 2: Run tests to verify they fail**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/integration/test_production_workspace_api.py tests/integration/test_production_sop_flow.py -q
```

Expected:

- FAIL，因为新 endpoint 或新 payload 尚未实现。

**Step 3: Write minimal implementation**

- `editor_production.py` 新增：
  - assignments patch
  - artifacts upload
  - transitions action endpoint
- `manuscripts.py` 把 author submit endpoint 改名义为 `author-feedback`，旧 URL 可兼容代理
- `manuscripts_detail_utils.py` 返回新的 proofreading task metadata

**Step 4: Run tests to verify they pass**

Run the same command.

**Step 5: Commit**

```bash
git add backend/app/api/v1/editor_production.py \
        backend/app/api/v1/manuscripts.py \
        backend/app/api/v1/manuscripts_detail_utils.py \
        backend/tests/integration/test_production_workspace_api.py \
        backend/tests/integration/test_production_sop_flow.py
git commit -m "feat: add production sop assignments artifacts and transition APIs"
```

## Task 5: 升级 author proofreading 为“反馈包”而不是替换正式稿

**Files:**
- Modify: `backend/app/services/production_workspace_service_workflow_author.py`
- Modify: `backend/app/models/production_workspace.py`
- Modify: `frontend/src/components/author/proofreading/ProofreadingForm.tsx`
- Modify: `frontend/src/app/proofreading/[id]/page.tsx`
- Modify: `frontend/tests/unit/author-proofreading.test.tsx`
- Modify: `frontend/tests/e2e/specs/production_pipeline.spec.ts`

**Step 1: Write the failing tests**

锁定：

- 作者可提交 correction list
- 作者可选上传 annotated PDF
- 提交后页面回显附件与 correction list
- 作者不能直接把稿件推进到可发布状态

**Step 2: Run tests to verify they fail**

Run:

```bash
cd frontend && bun x vitest run tests/unit/author-proofreading.test.tsx
cd frontend && bun x playwright test tests/e2e/specs/production_pipeline.spec.ts
```

Expected:

- FAIL，因为当前表单没有附件字段，mock payload 也还是旧结构。

**Step 3: Write minimal implementation**

- 后端扩展 author feedback attachment 存储
- 前端表单增加可选 annotated PDF 上传
- 页面保留当前 PDF preview + feedback form 双栏

**Step 4: Run tests to verify they pass**

Run the same commands.

**Step 5: Commit**

```bash
git add backend/app/services/production_workspace_service_workflow_author.py \
        backend/app/models/production_workspace.py \
        frontend/src/components/author/proofreading/ProofreadingForm.tsx \
        frontend/src/app/proofreading/[id]/page.tsx \
        frontend/tests/unit/author-proofreading.test.tsx \
        frontend/tests/e2e/specs/production_pipeline.spec.ts
git commit -m "feat: support author proofreading feedback package"
```

## Task 6: 重做 editor production workspace 为单一操作入口

**Files:**
- Modify: `frontend/src/app/(admin)/editor/production/[id]/page.tsx`
- Modify: `frontend/src/app/(admin)/editor/production/page.tsx`
- Modify: `frontend/src/components/editor/production/ProductionWorkspacePanel.tsx`
- Modify: `frontend/src/components/editor/production/ProductionActionPanel.tsx`
- Modify: `frontend/src/components/editor/production/ProductionTimeline.tsx`
- Modify: `frontend/src/services/editor-api/decision-production.ts`
- Modify: `frontend/tests/unit/production-workspace.test.tsx`
- Modify: `frontend/tests/unit/production-timeline.test.tsx`

**Step 1: Write the failing tests**

锁定：

- workspace 显示当前 `stage`
- action panel 只显示当前责任人可执行动作
- timeline 展示 artifact/event，而不是只展示 cycle status
- queue 支持 “assigned to me” 口径

**Step 2: Run tests to verify they fail**

Run:

```bash
cd frontend && bun x vitest run tests/unit/production-workspace.test.tsx tests/unit/production-timeline.test.tsx
```

Expected:

- FAIL，因为当前 UI 还是 legacy cycle status + approve 模型。

**Step 3: Write minimal implementation**

- workspace 改成：
  - stage summary
  - assignments
  - artifacts
  - transition actions
- queue 改按 `current_assignee_id` / responsibility filter 渲染

**Step 4: Run tests to verify they pass**

Run the same command.

**Step 5: Commit**

```bash
git add frontend/src/app/(admin)/editor/production/[id]/page.tsx \
        frontend/src/app/(admin)/editor/production/page.tsx \
        frontend/src/components/editor/production/ProductionWorkspacePanel.tsx \
        frontend/src/components/editor/production/ProductionActionPanel.tsx \
        frontend/src/components/editor/production/ProductionTimeline.tsx \
        frontend/src/services/editor-api/decision-production.ts \
        frontend/tests/unit/production-workspace.test.tsx \
        frontend/tests/unit/production-timeline.test.tsx
git commit -m "feat: redesign production workspace for sop workflow"
```

## Task 7: 移除详情页 legacy 生产推进入口，改为只读兼容摘要

**Files:**
- Modify: `frontend/src/components/editor/ProductionStatusCard.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/detail-sections.tsx`
- Modify: `backend/app/services/production_service.py`
- Modify: `backend/app/services/production_workspace_service_publish_gate.py`
- Modify: `backend/tests/integration/test_production_gates.py`
- Modify: `frontend/tests/e2e/specs/production_flow.spec.ts`

**Step 1: Write the failing tests**

锁定：

- 详情页不再能直接 `advance / revert`
- `Open Production Workspace` 成为唯一入口
- publish gate 必须同时检查：
  - `cycle.stage == ready_to_publish`
  - invoice paid/waived
  - publication artifact 存在

**Step 2: Run tests to verify they fail**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/integration/test_production_gates.py -q
cd frontend && bun x playwright test tests/e2e/specs/production_flow.spec.ts
```

Expected:

- FAIL，因为当前 detail 页和 `production_service.py` 仍允许 legacy 直接推进。

**Step 3: Write minimal implementation**

- `ProductionStatusCard` 改成只读摘要卡
- 详情页只保留跳转 workspace
- `production_service.py` 只保留 publish gate 聚合，不再负责 full chain advance/revert

**Step 4: Run tests to verify they pass**

Run the same commands.

**Step 5: Commit**

```bash
git add frontend/src/components/editor/ProductionStatusCard.tsx \
        frontend/src/app/(admin)/editor/manuscript/[id]/detail-sections.tsx \
        backend/app/services/production_service.py \
        backend/app/services/production_workspace_service_publish_gate.py \
        backend/tests/integration/test_production_gates.py \
        frontend/tests/e2e/specs/production_flow.spec.ts
git commit -m "refactor: remove legacy production direct advance flow"
```

## Task 8: 做全链路回归并同步文档

**Files:**
- Modify: `docs/GAP_ANALYSIS_AND_ACTION_PLAN.md`
- Modify: `AGENTS.md`
- Modify: `docs/DEPLOYMENT.md`
- Modify: `frontend/tests/e2e/specs/production_pipeline.spec.ts`
- Modify: `backend/tests/integration/test_production_publish_gate.py`

**Step 1: Write/update the failing tests or assertions**

补齐：

- full SOP happy path
- author correction loop
- ready_to_publish gate
- deployment docs / AGENTS workflow assumptions 与新设计一致

**Step 2: Run validation**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/integration/test_production_publish_gate.py tests/integration/test_production_sop_flow.py -q
cd frontend && bun x playwright test tests/e2e/specs/production_pipeline.spec.ts tests/e2e/specs/production_flow.spec.ts
```

Expected:

- PASS。

**Step 3: Update docs**

- 更新部署/迁移要求
- 更新生产流程说明
- 更新 AGENTS 里的关键环境假设与 production 描述

**Step 4: Re-run the same validation**

确保文档变更没有遗漏命令、路径和迁移说明。

**Step 5: Commit**

```bash
git add docs/GAP_ANALYSIS_AND_ACTION_PLAN.md \
        AGENTS.md \
        docs/DEPLOYMENT.md \
        frontend/tests/e2e/specs/production_pipeline.spec.ts \
        backend/tests/integration/test_production_publish_gate.py \
        backend/tests/integration/test_production_sop_flow.py
git commit -m "docs: sync production sop workflow rollout guidance"
```

## Execution Notes

- 历史 migration 只读，不回改；所有 schema 变更统一通过新增 migration 落地。
- 高风险改动按 TDD 执行，优先跑与当前任务直接相关的最小测试集。
- 在 UI 切换完成前，legacy 读路径仅作为兼容展示，不再新增新的 production 写入口。
