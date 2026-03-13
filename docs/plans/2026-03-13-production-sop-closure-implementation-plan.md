# Production SOP Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把已经落地的 production SOP 重构收口为单入口、单契约、可回归的稳定状态，移除 legacy 生产旁路，并明确 migration 未应用时的兼容行为。

**Architecture:** 以现有 `production_cycles.stage + assignments + artifacts + transitions + author feedback` 为唯一生产详细流程，不再扩展新功能面。执行上先锁测试与入口边界，再收口 backend 兼容与 publish gate，最后做最小回归和文档同步。

**Tech Stack:** FastAPI 0.115+, Pydantic v2, Supabase PostgreSQL, Next.js 16 App Router, React 19, TypeScript 5, Vitest, Playwright, pytest

---

## Execution Update

`2026-03-13` 当前会话已完成的收口：

- `frontend`：完成一轮 production workspace 文案去 legacy 化，`ProductionWorkspacePanel` 改为中性 SOP 口径（`Initial Assignee`、`Open Current Proof PDF`），`/editor/production` 队列描述改为只强调当前分配与 SOP 阶段；同时把 detail 页上的 `Publish Manuscript` 移出，改由 `/editor/production/[id]` 的 workspace action panel 接管，并更新 mocked Playwright 规格锁定这条边界。
- `backend`：补齐 `ProductionService` 当前契约测试，明确只允许 `approved_for_publish -> published`，把 `editor_production.py` 的 `advance/revert` 接口注释改成当前 SOP 语义，并新增 `/production/revert` 的 API 层集成契约测试。
- `backend schema fallback`：统一 production schema-missing 口径为 `503 + Production SOP schema not migrated: ...`，并移除 `create_cycle / update_assignments / transition_stage` 等写路径的 silent fallback；`editor_production.py` 入口层也会把旧 `DB not migrated: ...` / raw `PGRST205|PGRST204` 归一成新口径。
- `backend tests`：已通过定向回归 `tests/unit/test_production_service.py`、`tests/integration/test_production_gates.py`、`tests/integration/test_production_publish_gate.py`，结果为 `10 passed, 4 skipped`。
- `frontend tests`：已通过 mocked Playwright 定向回归 `tests/e2e/specs/production_flow.spec.ts`、`tests/e2e/specs/publish_flow.spec.ts`。
- `backend task 3 tests`：已通过 `tests/unit/test_production_workspace_service.py`、`tests/integration/test_production_workspace_api.py`、`tests/integration/test_production_sop_flow.py`，结果为 `19 passed, 7 skipped`。

当前完成度判断：

- `Task 1` 已完成核心边界收口：detail 页不再直接发布，workspace 成为发布动作入口；仍可后续再压缩重复入口 UI。
- `Task 2` 已实质完成，当前 publish gate / manuscript status 契约已锁定到测试与接口文档。
- `Task 3` 已实质完成，当前 production schema-missing / migration fallback 行为已统一到明确错误口径，且写路径不再静默回退到 legacy schema。
- `Task 4` 已完成前端文案和入口口径的一部分，但尚未覆盖作者反馈链路的完整对齐。

---

### Task 1: 锁定 production 单入口与 detail 页边界

**Files:**
- Modify: `frontend/src/components/editor/ProductionStatusCard.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- Test: `frontend/tests/e2e/specs/production_flow.spec.ts`

**Step 1: Write the failing test**

在 `frontend/tests/e2e/specs/production_flow.spec.ts` 增加断言：

- 稿件详情页不再出现中间生产阶段的 direct transition 按钮
- production 操作跳转或集中到 `/editor/production`
- detail 页最多保留状态摘要和进入 workspace 的入口

示例断言方向：

```ts
await expect(page.getByRole("button", { name: /advance to layout/i })).toHaveCount(0)
await expect(page.getByRole("link", { name: /open production workspace/i })).toBeVisible()
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && bun run test:e2e -- production_flow.spec.ts
```

Expected:

- FAIL，因为当前页面上仍可能保留 legacy 文案、按钮或错误入口。

**Step 3: Write minimal implementation**

- 在 `ProductionStatusCard.tsx` 删除或屏蔽所有中间生产阶段 direct actions
- 在 `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx` 只保留生产摘要和 workspace 入口
- 不在 detail 页重复实现 transition 逻辑

**Step 4: Run test to verify it passes**

Run the same command.

**Step 5: Commit**

```bash
git add frontend/src/components/editor/ProductionStatusCard.tsx \
        frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx \
        frontend/tests/e2e/specs/production_flow.spec.ts
git commit -m "refactor: enforce production workspace as sole action entry"
```

### Task 2: 锁定 publish gate 与 stage 契约

**Files:**
- Modify: `backend/app/services/production_workspace_service.py`
- Modify: `backend/app/services/production_workspace_service_publish_gate.py`
- Modify: `backend/app/services/production_service.py`
- Test: `backend/tests/unit/test_production_workspace_service.py`
- Test: `backend/tests/integration/test_production_gates.py`

**Step 1: Write the failing tests**

补充测试锁定：

- `ready_to_publish` 之前不能发布
- 没有满足 artifacts / final confirmation 条件时不能通过 publish gate
- `ProductionService.advance` 不能恢复旧的 `layout -> english_editing -> proofreading` 旁路

示例断言方向：

```python
with pytest.raises(HTTPException):
    service.advance(manuscript_id=mid, action="advance")
assert cycle.stage != "ready_to_publish"
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' \
  tests/unit/test_production_workspace_service.py \
  tests/integration/test_production_gates.py -q
```

Expected:

- FAIL，暴露仍可绕过 gate 或遗留旧推进路径的行为。

**Step 3: Write minimal implementation**

- 把 publish gate 判断收敛到 `production_workspace_service_publish_gate.py`
- 把 `production_service.py` 进一步限制为只处理 SOP 终点发布，而不是中间阶段推进
- 在 `production_workspace_service.py` 明确 `stage` 是详细流程唯一真相

**Step 4: Run test to verify it passes**

Run the same command.

**Step 5: Commit**

```bash
git add backend/app/services/production_workspace_service.py \
        backend/app/services/production_workspace_service_publish_gate.py \
        backend/app/services/production_service.py \
        backend/tests/unit/test_production_workspace_service.py \
        backend/tests/integration/test_production_gates.py
git commit -m "fix: harden production sop publish gate"
```

### Task 3: 收口 schema-missing 与 migration 兼容行为

**Files:**
- Modify: `backend/app/services/production_workspace_service.py`
- Modify: `backend/app/services/production_workspace_service_publish_gate.py`
- Modify: `backend/app/services/production_workspace_service_workflow_cycle_writes.py`
- Modify: `backend/app/services/production_workspace_service_workflow_author.py`
- Modify: `backend/app/services/production_workspace_service_workflow_cycle_context_queue.py`
- Modify: `backend/app/services/production_workspace_service_workflow_common.py`
- Modify: `backend/app/api/v1/editor_production.py`
- Test: `backend/tests/unit/test_production_workspace_service.py`
- Test: `backend/tests/integration/test_production_workspace_api.py`
- Test: `backend/tests/integration/test_production_sop_flow.py`
- Test: `backend/tests/integration/test_production_publish_gate.py`

**Step 1: Write the failing tests**

补充 unit / integration 测试锁定：

- 缺少 production schema 时返回明确兼容错误或只读兼容响应
- 不允许在 schema 缺失时静默回退到 legacy 生产推进流
- `PGRST205` / “does not exist” 都会走统一 missing-schema 分支
- `publish gate`、`workspace queue`、`author feedback`、`proofreading-email preview` 都要走同一套归一逻辑

示例断言方向：

```python
assert response.status_code in {409, 503}
assert response.json()["detail"].startswith("Production SOP schema not migrated")
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' \
  tests/unit/test_production_workspace_service.py \
  tests/integration/test_production_workspace_api.py \
  tests/integration/test_production_sop_flow.py \
  tests/integration/test_production_publish_gate.py -q
```

Expected:

- FAIL，因为错误码、错误文案或 fallback 行为尚未完全统一。

**Step 3: Write minimal implementation**

- 统一 `is_table_missing_error` / schema-missing 判定
- 在 `editor_production.py` 与 service 层收敛兼容响应
- 明确：schema 缺失时不再 silently fallback 到 legacy queue / workspace / author feedback / manual proofreading email 分支
- publish gate 不再把已经标准化的 `503` 包回 `500`
- payment gate / final PDF gate / publish gate helper / audit log / cycle events / artifact metadata / correction items 的 schema 缺失也统一归一到 `503`

**Step 4: Run test to verify it passes**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' \
  tests/unit/test_production_workspace_service.py \
  tests/integration/test_production_workspace_api.py \
  tests/integration/test_production_sop_flow.py \
  tests/unit/test_production_service.py \
  tests/integration/test_production_gates.py \
  tests/integration/test_production_publish_gate.py \
  tests/integration/test_proofreading_author_flow.py -q
```

Observed:

- `42 passed, 17 skipped`

**Step 5: Commit**

```bash
git add backend/app/services/production_workspace_service.py \
        backend/app/services/production_workspace_service_publish_gate.py \
        backend/app/services/production_workspace_service_workflow_cycle_writes.py \
        backend/app/services/production_workspace_service_workflow_author.py \
        backend/app/services/production_workspace_service_workflow_cycle_context_queue.py \
        backend/app/services/production_workspace_service_workflow_common.py \
        backend/app/api/v1/editor_production.py \
        backend/tests/unit/test_production_workspace_service.py \
        backend/tests/integration/test_production_workspace_api.py \
        backend/tests/integration/test_production_sop_flow.py \
        backend/tests/integration/test_production_publish_gate.py \
        backend/tests/unit/test_production_service.py \
        backend/tests/integration/test_production_gates.py
git commit -m "fix: standardize production sop schema fallback"
```

### Task 4: 对齐 workspace 动作面板与作者反馈链路

> 进度：已完成 workspace 基础文案收口与对应 Vitest；作者反馈链路与动作可见性仍待继续收口。

**Files:**
- Modify: `frontend/src/app/(admin)/editor/production/page.tsx`
- Modify: `frontend/src/components/editor/production/ProductionWorkspacePanel.tsx`
- Modify: `frontend/src/components/editor/production/ProductionActionPanel.tsx`
- Modify: `backend/app/services/production_workspace_service_workflow_author.py`
- Test: `frontend/tests/unit/production-workspace-ui.test.tsx`
- Test: `frontend/tests/unit/production-workspace.test.tsx`
- Test: `backend/tests/integration/test_proofreading_author_flow.py`

**Step 1: Write the failing tests**

补充测试锁定：

- workspace 只渲染与当前 `stage` 相匹配的动作
- author feedback 提交后，timeline / current assignee / next stage 显示一致
- 不再同时渲染 legacy “next action” 与新 transition dropdown

示例断言方向：

```tsx
expect(screen.queryByText(/next action/i)).not.toBeInTheDocument()
expect(screen.getByRole("combobox", { name: /transition/i })).toBeInTheDocument()
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && bun x vitest run tests/unit/production-workspace.test.tsx tests/unit/production-workspace-ui.test.tsx
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/integration/test_proofreading_author_flow.py -q
```

Expected:

- FAIL，暴露 UI 动作面板与作者反馈返回状态的残留不一致。

**Step 3: Write minimal implementation**

- 在 `ProductionWorkspacePanel.tsx` 和 `ProductionActionPanel.tsx` 只按 `stage` 渲染动作
- 清理残留 legacy 文案与重复入口
- 在 `production_workspace_service_workflow_author.py` 保证 author feedback 返回的 stage / assignment / timeline 数据一致

**Step 4: Run test to verify it passes**

Run the same commands.

**Step 5: Commit**

```bash
git add frontend/src/app/(admin)/editor/production/page.tsx \
        frontend/src/components/editor/production/ProductionWorkspacePanel.tsx \
        frontend/src/components/editor/production/ProductionActionPanel.tsx \
        backend/app/services/production_workspace_service_workflow_author.py \
        frontend/tests/unit/production-workspace-ui.test.tsx \
        frontend/tests/unit/production-workspace.test.tsx \
        backend/tests/integration/test_proofreading_author_flow.py
git commit -m "fix: align production workspace actions with sop stages"
```

### Task 5: 执行最小回归并同步文档状态

**Files:**
- Modify: `docs/plans/2026-03-13-overnight-workstream-reconciliation.md`
- Modify: `docs/plans/2026-03-10-open-work-items.md`
- Modify: `docs/plans/2026-03-11-current-workflow-for-uat.md`

**Step 1: Run the targeted regression suite**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' \
  tests/unit/test_production_workspace_service.py \
  tests/integration/test_production_workspace_api.py \
  tests/integration/test_production_sop_flow.py \
  tests/integration/test_production_gates.py \
  tests/integration/test_proofreading_author_flow.py -q

cd frontend && bun x vitest run \
  tests/unit/production-workspace.test.tsx \
  tests/unit/production-workspace-ui.test.tsx

cd frontend && bun run test:e2e -- production_flow.spec.ts
```

Expected:

- 全部 PASS；若有 skip，必须确认是 migration 未应用导致的预期 skip，而不是新增回归。

**Step 2: Update the docs**

- 在 `2026-03-13-overnight-workstream-reconciliation.md` 标记 production workstream 的收口结果
- 在 `2026-03-10-open-work-items.md` 勾掉已完成的 production SOP 项
- 在 `2026-03-11-current-workflow-for-uat.md` 同步当前 production 入口口径

**Step 3: Verify working tree**

Run:

```bash
git status --short
```

Expected:

- 只包含本轮代码与文档改动。

**Step 4: Commit**

```bash
git add docs/plans/2026-03-13-overnight-workstream-reconciliation.md \
        docs/plans/2026-03-10-open-work-items.md \
        docs/plans/2026-03-11-current-workflow-for-uat.md
git commit -m "docs: sync production sop closure status"
```

### Task 6: 并行执行策略

**Files:**
- No code changes in this task

**Step 1: Split ownership**

- Backend worker 负责：
  - `backend/app/services/production_*`
  - `backend/app/api/v1/editor_production.py`
  - backend production tests
- Frontend worker 负责：
  - `frontend/src/app/(admin)/editor/production/page.tsx`
  - `frontend/src/components/editor/production/*`
  - `frontend/src/components/editor/ProductionStatusCard.tsx`
  - `frontend/tests/e2e/specs/production_flow.spec.ts`

**Step 2: Reserve shared hotspot**

- `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx` 由主线程独占
- 不允许 worker 擅自修改这个文件

**Step 3: Execute in order**

执行顺序：

1. 主线程完成 Task 1 的 shared hotspot 边界收口
2. Backend worker 与 Frontend worker 并行执行 Task 2-4 中各自负责部分
3. 主线程统一跑 Task 5 回归与文档同步

**Step 4: No commit**

- 该任务只定义执行边界，不单独提交
