# 2026-03-13 Overnight Workstream Reconciliation

## Snapshot

- 检查时间：2026-03-13
- 当前分支：`main`
- 工作区状态：干净，`git status` 无未提交改动、无未跟踪文件
- 提交规模：
  - 自 `2026-03-12 00:00` 起共有 `62` 个 commit
  - 自 `2026-03-12 18:00` 起共有 `49` 个 commit
- 目录触点分布（按昨晚提交粗略统计）：
  - `backend/`：88 次
  - `frontend/`：61 次
  - `.claude/`：9 次
  - `docs/`：8 次
  - `supabase/`：3 次

## Executive Summary

昨晚的并行变更不是一条单线，而是至少 5 条工作流同时推进：

1. Production SOP 重构
2. 通知 / 邮件编排与手动发送能力补齐
3. Precheck / Intake / Managing Workspace 收口
4. Submission 源文件与 ZIP 路径增强
5. Decision / Academic workflow 对齐

从提交密度看，最拥挤的区域是：

- `precheck / intake / workspace`
- `email / notification / reviewer compose / invoice email`
- `production SOP / proofreading`

这意味着当前最需要人工收口的不是单个 bug，而是边界一致性：同一稿件详情页、同一 manual email 契约、同一 waiting-author / revision routing，被多个 agent 同时覆盖过。

## Workstream 1: Production SOP Redesign

### 目标

把 production 从旧的“直接推进”模式，改成围绕 `assignments / artifacts / transitions / author feedback` 的 SOP 工作流，并统一 editor 的 production workspace 入口。

### 关键提交

- `bc232f0` `feat: complete production sop transition logic, queues, and artifact logging`
- `a654cea` `feat: implement production sop assignments, artifacts, transitions and author feedback APIs`
- `22cdc2d` `feat: redesign production workspace for sop workflow`
- `ce55133` `refactor: remove legacy production direct advance flow`
- `bd24870` `docs: add session handoff for production sop part 2`

### 主要文件触点

- `backend/app/models/production_workspace.py`
- `backend/app/api/v1/editor_production.py`
- `backend/app/services/production_workspace_service.py`
- `backend/app/services/production_workspace_service_publish_gate.py`
- `backend/app/services/production_workspace_service_workflow_author.py`
- `backend/app/services/production_workspace_service_workflow_cycle_writes.py`
- `frontend/src/app/(admin)/editor/production/page.tsx`
- `frontend/src/components/editor/production/ProductionWorkspacePanel.tsx`
- `frontend/src/components/editor/production/ProductionActionPanel.tsx`
- `frontend/src/services/editor-api/decision-production.ts`
- `supabase/migrations/20260312120000_production_sop_stage_artifacts_events.sql`

### 对应文档 / handoff

- `docs/plans/2026-03-12-production-sop-redesign-design.md`
- `docs/plans/2026-03-12-production-sop-redesign-implementation-plan.md`
- `.claude/handoffs/2026-03-12-210137-production-sop-redesign.md`
- `.claude/handoffs/2026-03-13-090339-production-sop-part-2.md`

### 当前落地状态

- 后端领域模型、transition、artifact logging 和 author feedback API 已经落地
- 前端 production workspace 已重做为 SOP 导向界面
- 稿件详情页上的 legacy 直接推进流已被移除或降级为兼容摘要
- 相关单测 / 集成测试 / E2E 已跟进一轮

### 2026-03-13 Follow-up Execution Update

- 当前会话已继续收口 `production SOP`，把 frontend production workspace 的残留 legacy 文案替换成中性 SOP 口径。
- detail 页上的 `Publish Manuscript` 已移出，改由 `/editor/production/[id]` 的 workspace action panel 承担最终发布动作，避免 detail 页继续承载 production 旁路。
- backend 已把 `ProductionService` 的发布契约测试对齐到 `approved_for_publish -> published`，不再允许测试从 `proofreading` 起跳。
- `/api/v1/editor/manuscripts/{id}/production/revert` 已补 API 层集成契约测试，明确该入口必须显式返回 400 并提示改走 `Production Workspace`。
- 定向 backend 回归已通过：`tests/unit/test_production_service.py`、`tests/integration/test_production_gates.py`、`tests/integration/test_production_publish_gate.py`，结果为 `10 passed, 4 skipped`。
- mocked frontend E2E 已通过：`tests/e2e/specs/production_flow.spec.ts`、`tests/e2e/specs/publish_flow.spec.ts`。
- production schema-missing 分支已统一为 `503 + Production SOP schema not migrated: ...`；旧的 `DB not migrated: ...` 和 raw `PGRST205/PGRST204` 会在 production API 入口被归一化。
- `create_cycle / update_assignments / transition_stage / upload_galley / submit_proofreading` 等关键写路径不再在缺列时 silently fallback 到 legacy schema，也不再吞掉 artifact / attachment 元数据写入失败。
- `publish gate` 现在会把 `production_cycles.stage` / `production_cycles` 缺失统一抛成 `503`，不再把已归一的 schema 错误二次包成 `500`。
- `publish gate` 额外补齐了 `invoices` 读失败、`manuscripts.final_pdf_path` 缺列、`approved_at / galley_path` 缺列这些旧 schema 漏口；审计链路里的 `status_transition_logs.payload` 与 `production_cycle_events` 缺失也不再 silently no-op。
- `workspace context / queue / proofreading-email preview` 等读路径与手工邮件预览入口也已接入统一 schema-missing 归一逻辑。
- `Task 3` 当前 backend 全量定向回归已通过：`tests/unit/test_production_workspace_service.py`、`tests/integration/test_production_workspace_api.py`、`tests/integration/test_production_sop_flow.py`、`tests/unit/test_production_service.py`、`tests/integration/test_production_gates.py`、`tests/integration/test_production_publish_gate.py`、`tests/integration/test_proofreading_author_flow.py`，结果为 `42 passed, 17 skipped`。

### 收口风险

- `production` 相关 API 和 editor 页面同时动过，前后端契约虽然大概率已同步，但最容易残留旧字段假设
- `publish gate` 与新 `artifact / stage` 语义交织，若云端 migration 未推，最容易出现“本地逻辑对，线上 schema 不齐”
- 生产态入口被从多个页面收口后，旧的按钮、旧的状态文案、旧的测试 fixture 可能还残留在边缘页面

## Workstream 2: Notification / Email Rollout

### 目标

把邮件发送从零散分支逻辑，收敛成统一 envelope / recipient resolver / manual send 能力，同时补齐 reviewer compose、invoice、proofreading、technical revision、revision request 等 UI/接口。

### 关键提交

- `5061102` `feat: add email envelope logging and author recipient resolver`
- `b5ff1f0` `feat: add manual invoice email workflow`
- `4a3279f` `feat: record reviewer emails sent outside scholarflow`
- `2ce99df` `feat: add technical revision manual email endpoints`
- `5c0f910` `feat: add revision request manual email endpoints`
- `d54e26f` `feat: add manual proofreading reminder email endpoints`
- `4782d74` `feat: add journal mailbox envelopes for workflow emails`
- `acec154` `feat: add reviewer email envelope defaults`
- `ee6c567` `feat: expose reviewer email envelope fields in compose dialog`
- `ad10872` `feat: add invoice email send action to invoice modal`
- `d6dab11` `docs: create session handoff for author manual email UI`

### 主要文件触点

- `backend/app/core/mail.py`
- `backend/app/services/email_recipient_resolver.py`
- `backend/app/services/notification_orchestrator.py`
- `backend/app/api/v1/reviews.py`
- `backend/app/api/v1/editor_precheck.py`
- `backend/app/api/v1/editor_decision.py`
- `backend/app/api/v1/editor_heavy_decision.py`
- `backend/app/api/v1/invoices.py`
- `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- `frontend/src/components/editor/AuthorEmailPreviewDialog.tsx`
- `frontend/src/components/editor/ReviewerEmailPreviewDialog.tsx`
- `frontend/src/components/editor/InvoiceInfoModal.tsx`
- `backend/tests/unit/test_manual_email_api_contract.py`
- `backend/tests/unit/test_author_notification_target.py`
- `supabase/migrations/20260312193000_add_journal_public_editorial_email.sql`
- `supabase/migrations/20260312194000_expand_email_logs_delivery_envelope.sql`

### 对应文档 / handoff

- `docs/plans/2026-03-12-notification-email-orchestration-design.md`
- `docs/plans/2026-03-12-notification-email-orchestration-implementation-plan.md`
- `docs/plans/2026-03-12-reviewer-email-compose-design.md`
- `docs/plans/2026-03-12-reviewer-email-compose-implementation-plan.md`
- `.claude/handoffs/2026-03-12-205929-notification-email-rollout.md`
- `.claude/handoffs/2026-03-13-082914-author-manual-email-ui.md`

### 当前落地状态

- 邮件 envelope、日志记录、收件人解析器已进入后端主链路
- reviewer compose preview 和 envelope 字段已经暴露到前端
- invoice、technical revision、revision request、proofreading 的手动邮件入口已补齐
- 自动邮件与手动邮件的边界已经开始被区分，至少 revision request 流程已停止自动发信

### 收口风险

- `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx` 被多条线重复触达，是最需要人工抽查的热点页面
- manual email API 契约虽然有测试，但多个 endpoint 同时扩展，字段命名最容易轻微漂移
- `AGENTS.md / CLAUDE.md / GEMINI.md` 在 `b5ff1f0` 里出现过“混入无关改动”，随后 `5f8dd66` 再修正，说明昨晚确实发生过并行变更串扰

## Workstream 3: Precheck / Intake / Managing Workspace Unification

### 目标

把 waiting-author / revision 中间态从“卡在 intake 外面”改为“留在 workspace 内部可见、可恢复、可继续分派”，并收口到 Managing Workspace 单页视图。

### 关键提交

- `a57acb4` `docs(precheck): add ae assignment decoupling design`
- `8d202b9` `Allow AE assignment during waiting-author precheck`
- `973fe54` `Persist precheck return targets on revision requests`
- `7fff154` `fix(precheck): persist waiting-author resume target`
- `c4e9152` `Prefer persisted precheck routing on author resubmission`
- `caac4e7` `feat(precheck): surface waiting-author manuscripts in me workspace`
- `a2fb17e` `feat(editor-ui): add waiting-author section to me workspace`
- `846e789` `feat(intake): allow ae assignment during author revision`
- `9133213` `feat(editor): group waiting-author manuscripts in workspace`
- `c0874a9` `refactor(intake): keep waiting-author manuscripts in workspace`
- `8aa5de6` `refactor(editor): reuse managing workspace from intake route`
- `8b8175a` `fix(editor): harden workspace auth gate and error state`
- `a7e9110` `fix(editor): invalidate managing workspace cache on mutations`

### 主要文件触点

- `backend/app/services/editor_service_precheck_intake.py`
- `backend/app/services/editor_service_precheck_workspace_decisions.py`
- `backend/app/services/revision_service.py`
- `backend/app/api/v1/manuscripts_submission.py`
- `frontend/src/components/editor/ManagingWorkspacePanel.tsx`
- `frontend/src/app/(admin)/editor/intake/page.tsx`
- `frontend/src/components/AssignAEModal.tsx`
- `backend/tests/unit/test_precheck_role_service.py`

### 对应文档 / handoff

- `docs/plans/2026-03-12-precheck-ae-assignment-decoupling-design.md`
- `docs/plans/2026-03-12-precheck-ae-assignment-decoupling-implementation-plan.md`
- `docs/plans/2026-03-12-me-workspace-unification-design.md`
- `docs/plans/2026-03-12-me-workspace-unification-implementation-plan.md`
- `.claude/handoffs/2026-03-12-202503-me-workspace-intake-design-review.md`

### 当前落地状态

- waiting-author 稿件已开始在 workspace 中直接可见
- author revision 期间的 AE assignment 与 return target 持久化已补上
- intake 与 managing workspace 的 UI/数据入口已经开始复用
- 相关单测与页面测试都有补齐

### 收口风险

- `editor_service_precheck_intake.py`、`revision_service.py`、`manuscripts_submission.py` 同时动过，作者修回后路由恢复逻辑是潜在高风险点
- 前端 intake 页和 managing workspace 共用组件后，如果缓存失效策略不完整，容易出现“动作成功但列表不刷新”
- 这条线和 submission/decision 都有状态机交叉，容易出现同一 status 在不同页面解释不一致

## Workstream 4: Submission Source / ZIP Support

### 目标

增强投稿源文件提交流程，支持 source selector、ZIP 路径、source archive 元数据，并补足作者邮箱唯一性校验。

### 关键提交

- `7bf6b10` `feat(submission): add manuscript source selector`
- `8488f81` `feat: support zip-based manuscript submissions`
- `c0460eb` `fix(submission): allow source archive metadata`
- `123466c` `fix(submission): tolerate stale schema cache`
- `99ff6cc` `fix(submission): enforce unique author emails`

### 主要文件触点

- `backend/app/api/v1/manuscripts_submission.py`
- `backend/app/models/schemas.py`
- `backend/tests/test_manuscripts.py`
- `frontend/src/components/SubmissionForm.tsx`
- `frontend/src/components/submission/use-submission-form.ts`
- `frontend/src/components/submission/SubmissionSourceArchiveUploadCard.tsx`
- `frontend/src/components/submission/SubmissionWordUploadCard.tsx`
- `frontend/src/tests/SubmissionForm.test.tsx`
- `supabase/migrations/20260312183000_allow_source_archive_in_manuscript_files.sql`
- `supabase/migrations/20260312170000_reload_postgrest_schema_after_revision_fields.sql`

### 对应文档 / handoff

- `docs/plans/2026-03-12-submission-source-type-selector-design.md`
- `docs/plans/2026-03-12-submission-source-type-selector-implementation-plan.md`
- `docs/plans/2026-03-12-submission-word-zip-routing-design.md`
- `docs/plans/2026-03-12-submission-word-zip-routing-implementation-plan.md`
- `.claude/handoffs/2026-03-12-164746-submission-source-selector.md`

### 当前落地状态

- 前端投稿表单已支持 source selector 与 ZIP 上传分支
- 后端 schema/验证已跟进 source archive 元数据
- 作者联系邮箱唯一性约束已加上
- schema cache 相关容错做过一次补丁

### 收口风险

- 这条线和 precheck/resubmission 共享 `manuscripts_submission.py`，边界已经出现多次交叉修改
- 若线上 PostgREST schema cache 或 migration 不完整，这条链最容易暴露“本地通过、线上字段缺失”

## Workstream 5: Decision / Academic Workflow Alignment

### 目标

把 academic decision、revision before review、decision workspace 口径重新对齐，为后续 precheck / reviewer / production 串联打底。

### 关键提交

- `f31b600` `feat: align academic decision workflow`
- `abd4b92` `feat: make reviewer reselection explicit`
- `1c918bf` `feat: add reviewer email compose preview`
- `3402f86` `test: expand decision workspace smoke coverage`

### 主要文件触点

- `backend/app/services/decision_service.py`
- `backend/app/services/decision_service_transitions.py`
- `backend/app/services/editor_service.py`
- `backend/app/services/revision_service.py`
- `frontend/src/app/(admin)/editor/decision/[id]/page.tsx`
- `frontend/src/components/editor/decision/DecisionEditor.tsx`
- `frontend/src/components/ReviewerAssignModal.tsx`
- `supabase/migrations/20260312153000_add_revision_before_review_status.sql`

### 对应文档

- `docs/plans/2026-03-12-decision-academic-workflow-implementation-plan.md`
- `docs/plans/2026-03-11-current-workflow-for-uat.md`
- `docs/plans/2026-03-10-open-work-items.md`

### 当前落地状态

- decision / academic 的状态机与页面展示已经过一轮统一
- reviewer reselection 和 reviewer compose 开始显式化
- decision workspace smoke coverage 有补充

### 收口风险

- 这条线为其他工作流提供状态基础，任何 status 命名或 transition 变化都会向外扩散
- `revision_service.py` 在 decision 和 precheck 两边都被修改，是状态回流的交叉点

## Hotspots

下列文件在昨晚被重复改动，属于高风险热点：

- `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- `backend/app/api/v1/manuscripts_submission.py`
- `backend/tests/test_manuscripts.py`
- `backend/app/services/editor_service_precheck_intake.py`
- `frontend/src/components/editor/ManagingWorkspacePanel.tsx`
- `backend/tests/unit/test_manual_email_api_contract.py`
- `backend/tests/unit/test_author_notification_target.py`
- `backend/app/services/revision_service.py`
- `docs/plans/2026-03-10-open-work-items.md`
- `docs/plans/2026-03-11-current-workflow-for-uat.md`

## Documentation Inventory

### 昨晚新增或更新的正式计划文档

- `docs/plans/2026-03-12-production-sop-redesign-design.md`
- `docs/plans/2026-03-12-production-sop-redesign-implementation-plan.md`
- `docs/plans/2026-03-12-me-workspace-unification-design.md`
- `docs/plans/2026-03-12-me-workspace-unification-implementation-plan.md`
- `docs/plans/2026-03-12-precheck-ae-assignment-decoupling-design.md`
- `docs/plans/2026-03-12-precheck-ae-assignment-decoupling-implementation-plan.md`
- `docs/plans/2026-03-12-notification-email-orchestration-design.md`
- `docs/plans/2026-03-12-notification-email-orchestration-implementation-plan.md`
- `docs/plans/2026-03-12-reviewer-email-compose-design.md`
- `docs/plans/2026-03-12-reviewer-email-compose-implementation-plan.md`
- `docs/plans/2026-03-12-submission-source-type-selector-design.md`
- `docs/plans/2026-03-12-submission-source-type-selector-implementation-plan.md`
- `docs/plans/2026-03-12-submission-word-zip-routing-design.md`
- `docs/plans/2026-03-12-submission-word-zip-routing-implementation-plan.md`

### 昨晚新增的 handoff 文档

- `.claude/handoffs/2026-03-12-202503-me-workspace-intake-design-review.md`
- `.claude/handoffs/2026-03-12-205929-notification-email-rollout.md`
- `.claude/handoffs/2026-03-12-210137-production-sop-redesign.md`
- `.claude/handoffs/2026-03-12-213300-opencode-antigravity-config.md`
- `.claude/handoffs/2026-03-13-082914-author-manual-email-ui.md`
- `.claude/handoffs/2026-03-13-090339-production-sop-part-2.md`
- `.claude/handoffs/2026-03-12-164746-submission-source-selector.md`

## Possible Collision Points

### 1. 稿件详情页

`frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx` 同时被 production、manual email、reviewer compose 多条线触达，最适合做一次人工走查。

### 2. 投稿与修回入口

`backend/app/api/v1/manuscripts_submission.py` 同时承担 submission source、schema cache 兼容、precheck/resubmission 路由恢复，属于状态交叉高风险文件。

### 3. Revision 回流逻辑

`backend/app/services/revision_service.py` 同时被 decision 和 precheck 两条线改动，建议和状态机文档一起复核。

### 4. Managing Workspace 复用

`frontend/src/components/editor/ManagingWorkspacePanel.tsx` 被 waiting-author、quick actions、intake reuse、error state、cache invalidation 连续修改，功能面已明显扩大。

### 5. 协作规范文件

`AGENTS.md / CLAUDE.md / GEMINI.md` 在 invoice workflow 提交中曾混入无关变更，虽然随后被补救，但说明昨晚并行 agent 的改动边界并不总是干净。

## Suggested Human Review Order

1. 先过一遍 `production SOP` 当前 UI 与后端 API 是否一致
2. 再检查 `manuscript detail` 页里 reviewer compose / author manual email / invoice email 是否互相覆盖
3. 然后检查 `submission -> precheck -> waiting-author -> resubmission` 的状态回流
4. 最后核对 migration 是否都已推到云端，尤其是 production / email logs / source archive 这几条

## Recommended Next Actions

### 如果目标是“先恢复秩序”

- 以本文件作为总索引，给每条工作流指定 1 个 owner
- 明确哪些 handoff 只是中间态，哪些已经完全落地
- 把 `open-work-items` 里已经完成的事项勾掉，避免继续重复施工

### 如果目标是“先找风险”

- 手工走 `editor manuscript detail` 页面
- 手工走 `submission + resubmission` 页面
- 手工走 `editor production workspace`
- 对云端 Supabase 核对昨晚新增 migration 是否全部已应用

### 如果目标是“准备继续开发”

- 先决定后续主线是继续 production SOP，还是先收尾 notification/manual email
- 暂停继续并行修改 `manuscript detail` 与 `manuscripts_submission.py`，先把热点区收口
