# 2026-03-13 Parallel Agent Lanes: Manual Email / Submission / Precheck / Decision

## Goal

在不继续污染热点文件的前提下，同时推进 5 条可并行工作流，并由主线程统一处理共享状态机边界、最终集成和验证。

## Hotspot Owner

以下文件只允许主线程修改：

- `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- `backend/app/api/v1/manuscripts_submission.py`
- `backend/app/services/revision_service.py`

原因：

- `manuscript detail` 同时承载 reviewer compose / author manual email / invoice email 入口
- `manuscripts_submission.py` 同时承载 submission source、schema cache 兼容、precheck/resubmission 路由恢复
- `revision_service.py` 是 decision / precheck / resubmission 的状态回流交叉点

## Lane A: Manual Email Backend Core

目标：

- 收紧 manual email / notification 的 API 契约和 envelope / recipient resolver 一致性
- 优先处理 reviewer compose、technical revision、revision request、proofreading、invoice 手动发送链路

允许修改：

- `backend/app/core/mail.py`
- `backend/app/services/email_recipient_resolver.py`
- `backend/app/services/notification_orchestrator.py`
- `backend/app/api/v1/reviews.py`
- `backend/app/api/v1/invoices.py`
- `backend/tests/unit/test_manual_email_api_contract.py`
- `backend/tests/unit/test_author_notification_target.py`
- `backend/tests/unit/test_notification_orchestrator.py`

禁止修改：

- `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- `backend/app/api/v1/manuscripts_submission.py`
- `backend/app/services/revision_service.py`

最小验证：

- `backend/tests/unit/test_manual_email_api_contract.py`
- `backend/tests/unit/test_author_notification_target.py`
- `backend/tests/unit/test_notification_orchestrator.py`

## Lane B: Manual Email Frontend Dialogs

目标：

- 收口 author / reviewer / invoice 相关 compose / preview dialog
- 保证字段命名、只读派生字段和 envelope 展示口径一致

允许修改：

- `frontend/src/components/editor/AuthorEmailPreviewDialog.tsx`
- `frontend/src/components/editor/ReviewerEmailPreviewDialog.tsx`
- `frontend/src/components/editor/InvoiceInfoModal.tsx`
- `frontend/src/components/editor/ReviewerEmailPreviewDialog.test.tsx`
- `frontend/src/components/editor/InvoiceInfoModal.test.tsx`

禁止修改：

- `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- `backend/app/api/v1/manuscripts_submission.py`
- `backend/app/services/revision_service.py`

最小验证：

- dialog / modal 相关定向单测

## Lane C: Precheck Workspace / Waiting-Author

目标：

- 收口 waiting-author 稿件在 workspace 的可见性、恢复目标与 AE assignment
- 补 precheck workspace 的动作后刷新与状态展示稳定性

允许修改：

- `backend/app/services/editor_service_precheck.py`
- `backend/app/services/editor_service_precheck_intake.py`
- `backend/app/services/editor_service_precheck_workspace.py`
- `backend/app/services/editor_service_precheck_workspace_views.py`
- `backend/app/services/editor_service_precheck_workspace_decisions.py`
- `frontend/src/components/editor/ManagingWorkspacePanel.tsx`
- `frontend/src/components/AssignAEModal.tsx`
- `backend/tests/unit/test_precheck_role_service.py`
- `backend/tests/integration/test_precheck_flow.py`
- `frontend/tests/e2e/specs/precheck_workflow.spec.ts`

禁止修改：

- `backend/app/api/v1/manuscripts_submission.py`
- `backend/app/services/revision_service.py`
- `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`

最小验证：

- `backend/tests/unit/test_precheck_role_service.py`
- `backend/tests/integration/test_precheck_flow.py`
- `frontend/tests/e2e/specs/precheck_workflow.spec.ts`

## Lane D: Submission Frontend UX / Source ZIP

目标：

- 收口 source selector、Word / ZIP 互斥体验、作者邮箱唯一性前端反馈
- 保持投稿页与当前 DOCX-first / PDF-required 口径一致

允许修改：

- `frontend/src/components/SubmissionForm.tsx`
- `frontend/src/components/submission/use-submission-form.ts`
- `frontend/src/components/submission/SubmissionSourceArchiveUploadCard.tsx`
- `frontend/src/components/submission/SubmissionWordUploadCard.tsx`
- `frontend/src/tests/SubmissionForm.test.tsx`
- `frontend/tests/e2e/specs/submission.spec.ts`

禁止修改：

- `backend/app/api/v1/manuscripts_submission.py`
- `backend/app/services/revision_service.py`
- `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`

最小验证：

- `frontend/src/tests/SubmissionForm.test.tsx`
- `frontend/tests/e2e/specs/submission.spec.ts`

## Lane E: Decision / Academic / Reviewer Smoke

目标：

- 补齐 `academic -> decision / under_review`、`review-stage-exit -> first decision request email`、`under_review -> direct revision` 的边界验证
- 优先处理已有逻辑的定向测试与 smoke，而不是扩新功能

允许修改：

- `backend/app/services/decision_service.py`
- `backend/app/services/decision_service_transitions.py`
- `backend/app/services/decision_service_letters.py`
- `backend/app/api/v1/editor_decision.py`
- `backend/app/api/v1/editor_heavy_decision.py`
- `frontend/src/components/editor/decision/DecisionEditor.tsx`
- `frontend/src/components/editor/decision/DecisionEditor.test.ts`
- `backend/tests/integration/test_decision_workspace.py`
- `backend/tests/integration/test_decision_visibility.py`
- `backend/tests/integration/test_decision_rbac.py`
- `frontend/tests/e2e/specs/decision_workspace.spec.ts`
- `frontend/tests/e2e/specs/reviewer_management_delivery.spec.ts`

禁止修改：

- `backend/app/services/revision_service.py`
- `backend/app/api/v1/manuscripts_submission.py`
- `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`

最小验证：

- `backend/tests/integration/test_decision_workspace.py`
- `frontend/tests/e2e/specs/decision_workspace.spec.ts`

## Agent Rules

- 每个 agent 都必须知道自己不是唯一在工作的 agent，不得回滚或覆盖他人改动
- 不允许越过 lane 边界“顺手修一下”热点文件
- 若发现 blocker 落在热点文件，停止修改并汇报给主线程
- 每个 agent 最终只汇报：
  - 改了哪些文件
  - 跑了哪些验证
  - 剩余 blocker 是什么

## Main Thread Responsibilities

- 处理 3 个热点文件
- 处理跨 lane 的共享 route / glue file：
  - `backend/app/api/v1/editor.py`
  - `backend/app/api/v1/editor_precheck.py`
  - `backend/app/api/v1/editor_decision.py`
  - `backend/app/api/v1/editor_heavy_decision.py`
  - `backend/app/api/v1/editor_heavy_revision.py`
- 审核 worker 结果并解决交叉冲突
- 跑最终定向回归
- 同步文档、commit、push

## Execution Snapshot

本轮实际执行结果：

- Lane A `Manual Email Backend Core`：完成
- Lane B `Manual Email Frontend Dialogs`：完成
- Lane C `Precheck Workspace / Waiting-Author`：完成
- Lane D `Submission Frontend UX / Source ZIP`：完成
- Lane E `Decision / Academic / Reviewer Smoke`：worker 因 usage limit 中断，由主线程接管并完成

主线程未修改热点文件；本轮收口主要集中在各 lane 允许范围内的组件、服务层与测试。

## Delivered Changes

### Lane A

- `backend/app/core/mail.py`
- `backend/tests/unit/test_manual_email_api_contract.py`

收口内容：

- 未配置邮件 provider 时，manual email / invoice email 仍然记录 failed audit log
- `communication_status` 根据最终发送结果归一为 `system_sent` / `system_failed`
- declined reviewer assignment 不允许再记录 external-sent reminder

### Lane B

- `frontend/src/components/editor/AuthorEmailPreviewDialog.tsx`
- `frontend/src/components/editor/ReviewerEmailPreviewDialog.tsx`
- `frontend/src/components/editor/InvoiceInfoModal.tsx`
- `frontend/src/components/editor/ReviewerEmailPreviewDialog.test.tsx`
- `frontend/src/components/editor/InvoiceInfoModal.test.tsx`

收口内容：

- sending / saving 期间锁定收件人输入与 invoice modal 关键动作
- invoice modal 忙碌态禁止关闭，避免半提交状态

### Lane C

- `backend/app/services/editor_service_precheck_workspace_views.py`
- `backend/tests/unit/test_precheck_role_service.py`

收口内容：

- `revision_before_review` 稿件重新带回 waiting-author 上下文
- workspace row 补齐 `waiting_resubmit`、`waiting_resubmit_reason`、`intake_return_reason`

### Lane D

- `frontend/src/components/SubmissionForm.tsx`
- `frontend/src/components/submission/use-submission-form.ts`
- `frontend/src/tests/SubmissionForm.test.tsx`

收口内容：

- 前端显式展示 duplicate author email warning
- 移除 Word 稿或切换 away 时，清理未被手动触碰的 DOCX 派生元数据

### Lane E

- `backend/tests/integration/test_decision_workspace.py`
- `backend/tests/integration/test_decision_visibility.py`
- `backend/tests/integration/test_utils.py`

收口内容：

- 决策集成测试改用唯一 email，避免云端共享库唯一键冲突
- 显式补齐 editor / author / reviewer profile seed
- `insert_manuscript` 支持 `submission_email`
- review-stage-exit 补齐 first decision request / direct minor revision 邮件回执断言

## Validation Summary

本轮主线程最终验证：

- `backend/tests/unit/test_manual_email_api_contract.py`
- `backend/tests/unit/test_notification_orchestrator.py`
- `backend/tests/unit/test_mail.py`
- `backend/tests/unit/test_precheck_role_service.py`
- `backend/tests/integration/test_precheck_flow.py`
  - 结果：`75 passed`
- `backend/tests/integration/test_decision_workspace.py`
- `backend/tests/integration/test_decision_visibility.py`
- `backend/tests/integration/test_decision_rbac.py`
  - 结果：`12 passed`
- `frontend/src/components/editor/ReviewerEmailPreviewDialog.test.tsx`
- `frontend/src/components/editor/InvoiceInfoModal.test.tsx`
- `frontend/src/tests/SubmissionForm.test.tsx`
  - 结果：`28 passed`
- `frontend/tests/e2e/specs/submission.spec.ts`
  - 结果：`6 passed`
- `frontend/tests/e2e/specs/precheck_workflow.spec.ts`
  - 结果：`3 passed`

备注：

- `precheck_workflow.spec.ts` 的失败来自旧 mock 路由与旧 heading 断言，已按当前 `Managing Editor Workspace` / `managing-workspace` 契约修正
- `SubmissionForm.test.tsx` 仍有既存 React `act(...)` warning，但本轮新增断言与相关用例均为绿色
