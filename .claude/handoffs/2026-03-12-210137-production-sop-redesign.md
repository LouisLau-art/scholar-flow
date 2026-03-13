# Handoff: Production SOP Redesign 实施中间态

## Session Metadata
- Created: 2026-03-12 21:01:37
- Project: /root/scholar-flow
- Branch: main
- HEAD: `ad10872`
- Session duration: ~70 分钟

### Recent Commits (for context)
  - `ad10872` feat: add invoice email send action to invoice modal
  - `ee6c567` feat: expose reviewer email envelope fields in compose dialog
  - `a673850` docs(plan): add me workspace unification implementation plan
  - `d938274` docs(plan): add me workspace unification design
  - `acec154` feat: add reviewer email envelope defaults

## Handoff Chain

- **Continues from**: None
- **Supersedes**: None

## Current State Summary

本次工作已经从“production SOP 设计”进入“按计划执行”的实现阶段，但只完成了前半段基础设施，尚未进入 API/前端 UI 切换。当前可视为：

- Task 1 完成：后端/前端 production contract 已补到代码层；
- Task 2 完成：新增 migration，定义 `stage + per-cycle assignees + artifacts + events + author attachment fields`；
- Task 3 仅完成第一段：服务层已开始识别 `coordinator_ae_id/current_assignee_id/stage`，并让 `create_cycle -> upload_galley -> author submit` 这三条主链开始写入新字段，同时保留对旧 schema 的回退。

还没有开始的部分：

- queue 逻辑尚未真正按 `current_assignee_id + stage` 切换；
- transition/action API 还没重构；
- author feedback 附件上传还只是 schema 层准备，没有接前后端上传能力；
- editor production workspace 前端仍是旧模型。

## Codebase Understanding

## Architecture Overview

Production 这次重构的核心约束已经确定，不要再回到“硬编码 4 个平台角色”的思路：

- 平台角色保持粗粒度：
  - `assistant_editor`
  - `production_editor`
  - `managing_editor`
  - `admin`
- 每个 `production_cycle` 负责挂具体责任人：
  - `coordinator_ae_id`
  - `typesetter_id`
  - `language_editor_id`
  - `pdf_editor_id`
  - `proofreader_author_id`
- `production_cycle.stage` 将成为 production 唯一 source of truth；
- `manuscripts.status` 继续保留，但只是兼容 bucket；
- 产物和交接靠：
  - `production_cycle_artifacts`
  - `production_cycle_events`

目前代码层的实际状态是“兼容过渡态”：

- `backend/app/services/production_workspace_service.py` 已经有：
  - `_LEGACY_STATUS_STAGE_MAP`
  - `_PRODUCTION_CYCLE_SELECT_SOP / _PRODUCTION_CYCLE_SELECT_LEGACY`
  - `_derive_cycle_stage()`
  - `_derive_current_assignee_id()`
  - `_format_cycle()` 输出新字段
- `_ensure_editor_access()` 已经允许：
  - `assistant_editor` 在 `coordinator_ae_id == user_id` 时读 production
  - `production_editor` 在 `current_assignee_id == user_id` 时写 production
  - 老 schema 下继续回退 `layout_editor_id / collaborator_editor_ids`
- `create_cycle / upload_galley / submit_proofreading` 已开始写 `stage/current_assignee`

## Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| `docs/plans/2026-03-12-production-sop-redesign-design.md` | 设计决策基线 | 明确了角色策略、状态机、产物、迁移和最佳实践出处 |
| `docs/plans/2026-03-12-production-sop-redesign-implementation-plan.md` | 实施任务拆分 | 当前实现就是按这份计划推进 |
| `supabase/migrations/20260312120000_production_sop_stage_artifacts_events.sql` | Production SOP 新 schema | 已新增但尚未推到云端/测试库 |
| `backend/app/models/production_workspace.py` | 后端 contract model | 已补 `stage`、责任人字段、`artifacts` |
| `backend/app/services/production_workspace_service.py` | 核心读模型/权限判定 | 已开始兼容新 SOP 字段，是下一步继续改的核心入口 |
| `backend/app/services/production_workspace_service_workflow_cycle_writes.py` | create/upload/update 写路径 | 已开始写 `stage/current_assignee`，后续要继续接 artifacts/events |
| `backend/app/services/production_workspace_service_workflow_author.py` | author proofreading 提交 | 已开始把 author submit 后的 cycle 设到 `ae_final_review` |
| `backend/app/services/production_workspace_service_workflow_cycle_context_queue.py` | workspace/queue 读模型 | 还没切到 `stage/current_assignee`，下一步重点 |
| `backend/app/api/v1/editor_production.py` | production API | 还没重构成 assignments/artifacts/transitions 风格 |
| `frontend/src/types/production.ts` | 前端 contract type | 已补新字段 |
| `frontend/src/lib/production-utils.ts` | active cycle 判断 | 已支持 `stage` 优先 |
| `frontend/src/components/editor/production/*` | editor production 前端 | 仍是旧 layout_editor/status 模型，后续要整体改 |

## Key Patterns Discovered

- 当前 service 已经处于“新 schema 优先、旧 schema 回退”的兼容写法：
  - 先 select SOP 列；
  - 如果报缺列，再回退 legacy select。
- 这次改造必须沿着这个兼容模式做，否则云端未迁移时 editor 页面会直接 500。
- `production_workspace_service.py` 已经具备作为统一聚合层的雏形，不要绕开它去各路由各自推导 `stage`。
- 前端目前只有 `production-utils.ts` 这一处开始真正使用 `stage`；大部分组件仍然看 `status/layout_editor_id/collaborators`。

## Work Completed

### Tasks Finished

- [x] 写出 production SOP 设计稿
- [x] 写出 production SOP 实施计划
- [x] 后端 contract model 增加：
  - `ProductionCycleStage`
  - `ProductionArtifactKind`
  - `ProductionArtifactPayload`
  - `ProductionCyclePayload.stage`
  - `coordinator_ae_id / typesetter_id / language_editor_id / pdf_editor_id / current_assignee_id`
  - `artifacts`
- [x] 前端 contract type 增加对应字段
- [x] `frontend/src/lib/production-utils.ts` 让 `hasActiveProductionCycle()` 支持 `stage` 优先
- [x] 新增 migration：
  - `stage`
  - production assignee 字段
  - `production_cycle_artifacts`
  - `production_cycle_events`
  - `production_proofreading_responses` 附件字段
- [x] integration schema check 测试已更新到新 schema 契约
- [x] `_ensure_editor_access()` 已支持 coordinator AE / current assignee
- [x] `create_cycle / upload_galley / submit_proofreading` 已开始写 `stage/current_assignee`

### Files Modified

| File | Changes | Rationale |
|------|---------|-----------|
| `docs/plans/2026-03-12-production-sop-redesign-design.md` | 新建设计稿 | 固化重构方向 |
| `docs/plans/2026-03-12-production-sop-redesign-implementation-plan.md` | 新建实施计划 | 按任务推进 |
| `supabase/migrations/20260312120000_production_sop_stage_artifacts_events.sql` | 新增 migration | 定义新 schema |
| `backend/app/models/production_workspace.py` | 增加新 contract 字段 | 锁定 domain contract |
| `backend/app/services/production_workspace_service.py` | 兼容 SOP select/stage/assignee/access | 读模型和权限过渡 |
| `backend/app/services/production_workspace_service_workflow_cycle_writes.py` | create/upload 开始写 stage/current_assignee | 主链兼容新 schema |
| `backend/app/services/production_workspace_service_workflow_author.py` | author submit 后写 `ae_final_review/current_assignee` | 主链兼容新 schema |
| `backend/tests/unit/test_production_workspace_service.py` | 新增 contract + access 测试 | 锁定行为 |
| `backend/tests/integration/test_production_workspace_api.py` | schema check 更新 | 确保 migration 契约 |
| `backend/tests/integration/test_proofreading_author_flow.py` | schema check + stage 断言更新 | 锁定 author flow 目标状态 |
| `frontend/src/types/production.ts` | 新增前端 SOP type | 前端 contract 对齐 |
| `frontend/src/lib/production-utils.ts` | `stage` 优先 | 活跃轮次判断开始脱离 legacy status |
| `frontend/tests/unit/production-workspace.test.tsx` | 新增 `stage/artifact_kind` 测试 | 锁定前端契约 |

## Decisions Made

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| 先保留稳定平台角色，不直接新增 4 个硬编码平台角色 | 4 个硬角色；单一 production_editor；per-cycle assignees | per-cycle assignees 更灵活，兼任和代理成本更低 |
| `production_cycle.stage` 做唯一 production source of truth | 继续依赖 `manuscripts.status`；双轨并存 | 双轨状态机是当前实现最大风险点 |
| 本轮先做兼容演进，不推倒重来 | 一次性大切换；增量迁移 | 云端还在跑旧 schema，必须双读/双写过渡 |
| Task 3 先从 access/control 和三条主链写路径切入 | 先做前端；先改 API；先改 queue | 先让 domain contract 真正进服务层，后续 API/UI 才有稳固基础 |

## Pending Work

## Immediate Next Steps

1. 完成 Task 3 剩余部分，优先改：
   - `backend/app/services/production_workspace_service_workflow_cycle_context_queue.py`
   - `backend/app/services/production_workspace_service_workflow_cycle.py`
   - `backend/app/services/production_workspace_service_publish_gate.py`
   目标：
   - queue 改按 `current_assignee_id + stage`
   - `display_cycle/active_cycle` 改按 `stage`
   - approve/publish gate 开始看 `ready_to_publish`

2. 补真正的 artifacts/events 写入，不要只停在 schema：
   - galley/typeset/language/final/publication 上传时写 `production_cycle_artifacts`
   - handoff/transition 时写 `production_cycle_events`

3. 再进入 Task 4：
   - 重构 `backend/app/api/v1/editor_production.py`
   - 新增 assignments/artifacts/transitions endpoint 族
   - 保留旧 endpoint 兼容代理

4. 之后再做 author feedback 附件上传和前端 workspace 切换。

## Blockers/Open Questions

- [ ] 云端/测试库尚未应用 `20260312120000_production_sop_stage_artifacts_events.sql`，所以 integration 目前只能 `skip`，没法做真正写入验证。
- [ ] 工作区里存在多个额外未跟踪 migration：
  - `supabase/migrations/20260312203000_production_sop_stage_artifacts_events.sql`
  - `supabase/migrations/20260312210000_production_sop_stage_artifacts_events.sql`
  - `supabase/migrations/20260312211000_production_sop_stage_artifacts_events.sql`
  这些不是本次创建的主 migration，下一位 agent 不要随手提交；先确认来源。
- [ ] 还有未跟踪文件：
  - `backend/tests/unit/test_manual_email_idempotency.py`
  - `backend/tests/unit/test_production_schema_migration.py`
  这两份不是本次主线工作产物，需要先辨别是不是用户或其他并行任务留下的。

## Deferred Items

- 还没动 `frontend/src/components/editor/production/ProductionWorkspacePanel.tsx` 等 UI 文件。
- 还没动 `frontend/src/app/proofreading/[id]/page.tsx` 的附件上传能力。
- 还没动 `backend/app/api/v1/manuscripts.py` 的 author-feedback 契约。
- 还没处理 `ProductionStatusCard` 从“可推进”变“只读摘要”。

## Context for Resuming Agent

## Important Context

1. 设计阶段已经结束，用户明确选择继续执行实现，不需要再回到 brainstorm。
2. 当前最危险的误操作是：
   - 把那几个额外未跟踪 migration 一起提交；
   - 直接按新 schema 写死，不做缺列回退；
   - 跳过 `production_workspace_service.py`，在别处重复推导 `stage/current_assignee`。
3. 现在 unit 层已经有一个稳定落脚点，下一位 agent 应该延续 TDD，小步推进 queue/transition/publish gate，而不是直接冲前端大改。
4. 设计稿和实施计划都已存在，优先读：
   - `docs/plans/2026-03-12-production-sop-redesign-design.md`
   - `docs/plans/2026-03-12-production-sop-redesign-implementation-plan.md`

## Assumptions Made

- 假设 `layout_editor_id` 目前仍作为 typesetter 的 legacy fallback。
- 假设 `coordinator_ae_id` 在未真正分配前允许为空。
- 假设 `current_assignee_id` 是读优化字段，可以从 stage + role fields 推导回退。
- 假设云端数据库短期内不会立即同步 migration，所以服务层必须继续容忍缺列。

## Potential Gotchas

- 本次 session 中尝试过 `session-handoff` skill 说明里的 `scripts/create_handoff.py` / `validate_handoff.py`，但仓库根目录并没有这些脚本；本 handoff 是手工创建的。
- `backend/tests/unit/test_production_workspace_service.py` 在本轮开始时有一条未提交的 `idempotency_key` 断言改动；现在整份文件已通过，不要误以为那还是独立红点。
- `git status` 里已经有其他未跟踪 handoff：`.claude/handoffs/2026-03-12-205929-notification-email-rollout.md`，与本任务无关。
- 当前仍在 `main` 分支直接工作，没有 commit；如果继续实现，最好先确认是否要继续在当前分支上推进。
- 全仓 `cd frontend && bun x tsc --noEmit --pretty false` 仍然会被 `tests/e2e/specs/submission.theme-accessibility.spec.ts:69` 的 Playwright 类型冲突卡住，这不是 production SOP 改动引入的。

## Environment State

### Tools/Services Used

- `exec_command`：读取代码、运行定向测试、查看 git 状态
- `apply_patch`：手工修改代码和文档
- `spawn_agent` / `wait`：尝试并行 explorer/reviewer，但后续已中断，未产出可用结果
- 未启动 `bun dev`、`uvicorn`、`./start.sh`

### Active Processes

- 无长期运行进程
- 所有先前子 agent 已中断

### Validation Run

已通过：

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' backend/tests/unit/test_production_workspace_service.py -q`
- `cd frontend && bun x vitest run tests/unit/production-workspace.test.tsx`

预期 `skip`：

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' backend/tests/integration/test_production_workspace_api.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' backend/tests/integration/test_proofreading_author_flow.py -q`

未通过但与本任务无关：

- `cd frontend && bun x tsc --noEmit --pretty false`
  - 卡在 `tests/e2e/specs/submission.theme-accessibility.spec.ts:69`

### Working Tree Snapshot

当前与本任务直接相关的未提交改动：

- `backend/app/models/production_workspace.py`
- `backend/app/services/production_workspace_service.py`
- `backend/app/services/production_workspace_service_workflow_author.py`
- `backend/app/services/production_workspace_service_workflow_cycle_writes.py`
- `backend/tests/integration/test_production_workspace_api.py`
- `backend/tests/integration/test_proofreading_author_flow.py`
- `backend/tests/unit/test_production_workspace_service.py`
- `frontend/src/lib/production-utils.ts`
- `frontend/src/types/production.ts`
- `frontend/tests/unit/production-workspace.test.tsx`
- `supabase/migrations/20260312120000_production_sop_stage_artifacts_events.sql`
- `docs/plans/2026-03-12-production-sop-redesign-design.md`
- `docs/plans/2026-03-12-production-sop-redesign-implementation-plan.md`

## Related Resources

- `docs/plans/2026-03-12-production-sop-redesign-design.md`
- `docs/plans/2026-03-12-production-sop-redesign-implementation-plan.md`
- `backend/app/models/production_workspace.py`
- `backend/app/services/production_workspace_service.py`
- `backend/app/services/production_workspace_service_workflow_cycle_writes.py`
- `backend/app/services/production_workspace_service_workflow_author.py`
- `backend/app/services/production_workspace_service_workflow_cycle_context_queue.py`
- `backend/app/services/production_workspace_service_workflow_cycle.py`
- `backend/app/api/v1/editor_production.py`
- `frontend/src/types/production.ts`
- `frontend/src/lib/production-utils.ts`
- `frontend/src/components/editor/production/ProductionWorkspacePanel.tsx`
- `frontend/src/components/editor/production/ProductionActionPanel.tsx`
- `frontend/src/components/editor/production/ProductionTimeline.tsx`

---

**Security Reminder**: 本 handoff 为手工创建，未运行自动 validator；已人工检查无密钥、认证串、密码等敏感信息。
