# Production SOP Closure Design

**Date:** 2026-03-13

**Status:** approved for planning

**Related Skills:** `brainstorming`, `writing-plans`, `dispatching-parallel-agents`

## Problem

`Production SOP Redesign` 的主体代码已经落地，但当前仓库状态更像“完成了重构主干，尚未完成统一收口”。

具体表现为：

- 后端 `stage / artifacts / transitions / publish gate` 已进入主链路，但需要确认没有 legacy direct-advance 旁路残留。
- 前端 `/editor/production` 已重做，但稿件详情页与 production workspace 的职责边界需要再次锁死。
- 生产链路相关 migration 已写入仓库，但需要明确云端应用前后的兼容策略。
- 昨晚多 agent 并行后，production 相关代码虽集中，但仍与 `manual email`、`manuscript detail`、`author proofreading` 等区域发生交叉。

因此，当前阶段最合理的目标不是再扩展 production 功能，而是把已经实现的 SOP 方案收成“单入口、单契约、可回归、可交接”的稳定状态。

## Goals

- 确认 production 详细流程的唯一 source of truth 是 `production_cycle.stage`。
- 确认 editor 侧 production 只有一个主操作入口，即 `/editor/production`。
- 确认稿件详情页不再承担 legacy 生产推进职责，只保留只读摘要或跳转能力。
- 确认 `assignments / artifacts / transitions / author feedback / publish gate` 的前后端契约一致。
- 明确 migration 前后兼容行为，并把“未迁移云端”的降级策略写清楚。
- 用最小回归测试集合覆盖 production 闭环。

## Non-Goals

- 本轮不新增新的 production 角色类型。
- 本轮不扩展 proofreading 以外的复杂作者协作能力。
- 本轮不重构 notification/manual email 体系。
- 本轮不回头重做 precheck / decision 主流程。

## Current State

根据现有提交、handoff 和代码状态，当前 production SOP 已具备以下能力：

- `production_cycles` 已承载新的 `stage` 语义。
- 后端已支持 `assignments`、`artifacts`、`transitions`、`author feedback`。
- `ProductionWorkspacePanel` / `ProductionActionPanel` 已按 SOP 阶段重做。
- `ProductionStatusCard` 与 `production_service` 已开始移除 legacy direct transitions。
- `publish gate` 已开始依赖 `ready_to_publish` 与产物状态。

未完成的不是“有没有功能”，而是“有没有彻底收口”。

## Options Considered

### Option A: 继续在现有基础上加功能

优点：

- 短期看起来推进更快。

缺点：

- 会把当前尚未统一的入口、状态和测试继续摊薄。
- 很容易再次把 `manuscript detail` 变成隐性第二入口。

### Option B: 先做 production 收口，再恢复并行开发（推荐）

优点：

- 最适合当前多 agent 并行后需要恢复秩序的仓库状态。
- 可以在不大改架构的前提下，快速提升可维护性和可验证性。
- 有利于后续把 `manual email`、`proofreading`、`publish gate` 接到同一稳定底座上。

缺点：

- 短期需要投入时间做回归与边界清理，而不是继续扩功能。

### Option C: 回退到旧 production 流程，SOP 仅部分启用

优点：

- 看起来风险最低。

缺点：

- 已有实现成本白费。
- 新旧双轨并存时间更长，风险更高。

## Decision

采用 **Option B**：把本轮 production 主线定义为 **closure / stabilization**，而不是继续扩大功能面。

## Closure Scope

本轮收口只覆盖 4 个层面：

1. 领域契约
2. 页面入口边界
3. 兼容 / migration 行为
4. 最小回归验证

## Design

### 1. 领域契约

后端与前端共同承认下列 production 概念是唯一真相：

- `stage`
- `current_assignee`
- `assignments`
- `artifacts`
- `author_feedback`
- `ready_to_publish`
- `published`

约束：

- 任何中间生产步骤都不能再由 `manuscripts.status` 的旧线性推进直接驱动。
- `manuscripts.status` 只保留 coarse-grained 兼容意义。
- `publish gate` 必须由 production cycle 的状态与产物共同决定。

### 2. 页面入口边界

Editor 侧的生产操作入口约束如下：

- `/editor/production`：唯一主操作入口
- `/editor/manuscript/[id]`：只读摘要、状态展示、跳转到 workspace

禁止项：

- 在稿件详情页保留任何会跨 `layout / language / proofreading` 的 legacy direct-advance 按钮
- 在两个页面上重复维护同一种 transition 动作

### 3. 兼容与降级策略

考虑到云端 migration 可能尚未完整应用，需要明确以下策略：

- 若 production artifact / event / stage schema 不存在，后端必须返回明确的兼容响应，而不是隐式 500。
- 降级路径只允许“不可执行新动作但可读兼容摘要”，不允许偷偷回退到旧生产推进流。
- 所有 schema-missing 分支都要集中在 production service / API 层，不把兼容逻辑散落到前端组件。

### 4. 测试策略

本轮不跑整仓回归，只跑 production 相关最小集合：

- backend unit：production workflow / gate
- backend integration：production workspace API / proofreading author flow / production sop flow
- frontend unit：production workspace 组件与类型
- frontend e2e：production flow

测试目标不是证明“所有功能都没问题”，而是证明 production 收口后的主闭环成立。

## Files In Scope

### Backend

- `backend/app/services/production_workspace_service.py`
- `backend/app/services/production_workspace_service_publish_gate.py`
- `backend/app/services/production_workspace_service_workflow_common.py`
- `backend/app/services/production_workspace_service_workflow_author.py`
- `backend/app/services/production_workspace_service_workflow_cycle_writes.py`
- `backend/app/api/v1/editor_production.py`
- `backend/app/services/production_service.py`

### Frontend

- `frontend/src/app/(admin)/editor/production/page.tsx`
- `frontend/src/components/editor/production/ProductionWorkspacePanel.tsx`
- `frontend/src/components/editor/production/ProductionActionPanel.tsx`
- `frontend/src/components/editor/ProductionStatusCard.tsx`
- `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`

### Tests

- `backend/tests/unit/test_production_workspace_service.py`
- `backend/tests/integration/test_production_workspace_api.py`
- `backend/tests/integration/test_production_sop_flow.py`
- `backend/tests/integration/test_production_gates.py`
- `backend/tests/integration/test_proofreading_author_flow.py`
- `frontend/tests/unit/production-workspace.test.tsx`
- `frontend/tests/unit/production-workspace-ui.test.tsx`
- `frontend/tests/e2e/specs/production_flow.spec.ts`

### Docs

- `docs/plans/2026-03-12-production-sop-redesign-design.md`
- `docs/plans/2026-03-12-production-sop-redesign-implementation-plan.md`
- `docs/plans/2026-03-13-overnight-workstream-reconciliation.md`

## Parallelization Boundary

在执行阶段，只允许两条并行线：

- Backend agent：只负责 production service / API / tests
- Frontend agent：只负责 production workspace / detail page / tests

共享热点文件的规则：

- `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx` 必须由单一 owner 修改
- 若需要同时影响该文件与 workspace 组件，先由主线程定边界再分派

## Success Criteria

- `production_cycle.stage` 成为 production 详细进度的唯一真相
- `/editor/production` 成为唯一主操作入口
- 稿件详情页不再保留中间生产阶段的 direct transition
- `publish gate` 与 artifacts / transitions 语义一致
- migration 未应用时的降级行为明确且可预期
- production 相关最小回归测试通过

## Recommended Execution Order

1. 锁定契约与边界
2. 清理 legacy direct-advance 残留
3. 收口 migration / schema-missing 行为
4. 跑定向回归
5. 更新对账文档与 open work items

