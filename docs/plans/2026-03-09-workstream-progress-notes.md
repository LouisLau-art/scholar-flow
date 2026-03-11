# Workstream Progress Notes

日期：2026-03-09
当前代码锚点：`8411912`
分支：`main`
状态：工作区干净（记录创建时）

## 已完成主线

### Next 16 稳定化

- 已完成 `Next 16.1.6 + React 19 + eslint-config-next 16` 工具链对齐。
- 已完成 `middleware -> proxy` 迁移。
- 已完成 async request APIs 第一轮收敛。
- 已补齐 `README.md`、`AGENTS.md`、`docs/DEPLOYMENT.md` 的版本口径。
- 已设置回退锚点：`pre-next16-full-align`。

### Reviewer Invitation / Workspace

- reviewer 必须显式 `Accept` 邀请后才能进入 workspace。
- `session` / `workspace` / `submit` 已移除 implicit accept。
- invite 页已支持稿件基础信息与 PDF 预览。
- decline reasons 已接入 invite 页决策面。
- reviewer 首次激活不再走明文密码，已改为 activation / set-password 流程。
- reviewer 第一阶段体验收敛已完成：
  - reviewer workspace 的 `Comment to Authors` 已扩展为更适合长篇评审的输入区（更高默认高度 + `resize-y`）
  - reviewer 的公开 token 页与 magic assignment 页已同步放大两个评论框
  - reviewer 当前主链路（workspace / token / magic assignment）已去掉 `score` 输入
  - reviewer workspace 提交后不再写入占位 `score = 5`
  - token/magic 提交链也不再要求或写入 `score`

### Manuscript Detail / Reviewer Summary

- 稿件详情页左侧主区已新增 `Reviewer Management`。
- 右侧 `Review Summary` 已收敛为轻量摘要卡。
- 多轮 reviewer 的 `submitted_at` 错绑问题已修复。
- reviewer history modal 已补充 `round / due / decline reason / decline note` 等字段。
- reviewer invitation 已新增 assignment 级邮件证据链：
  - `email_logs` 扩展为支持 `assignment_id / manuscript_id / idempotency_key / scene / event_type`
  - reviewer 邮件发送先落应用级 `queued` 审计，再由后台发送链补 `sent / failed`
  - 稿件详情页 `Reviewer Management` 与 reviewer history modal 已展示最新 delivery 状态与邮件事件时间线
- reviewer 主链路 E2E 已新增两条跨浏览器回归：
  - 未接受邀请时，`/reviewer/workspace/[id]` 必须挡回 `/review/invite`
  - 编辑侧稿件详情页必须展示 reviewer delivery 状态，并可在 history modal 中看到 `sent / queued` 事件
- decline 后重新邀请语义已完成第二阶段收敛：
  - 对 `declined` assignment 再发 `invitation` 时，不再复用旧记录
  - 后端会新建 fresh assignment attempt，并继承 `manuscript_id / reviewer_id / due_at / round_number`
  - 新 attempt 会写入：
    - `selected_by=当前编辑`
    - `selected_via=system_reinvite`
    - `invited_by=当前编辑`
    - `invited_via=template_invitation`
  - 新邀请邮件、magic link、`email_logs.assignment_id` 全部绑定 fresh assignment
  - 旧 declined 记录保持终态，仅用于审计与 history 展示
  - 对 `declined` assignment 发送 `reminder` 现在会被 409 阻断，避免把提醒发到终态记录
- reviewer invitation history 展示已做一轮 UX 收敛：
  - `added_via / invited_via` 不再直接显示底层 token，统一转成业务文案
  - `Email Actions` 不再拼接原始字符串，改为按 `Invitation sent / Reminder failed` 这类可读事件展示
  - declined reason 也已做人类可读映射，避免直接暴露内部枚举值
- 编辑侧 reviewer 反馈展示已完成第一阶段去分数化：
  - 稿件详情页 `Reviewer Feedback Summary` 不再显示 `Score`
  - reviewer history modal 不再把 `report_score` 作为主展示文案
  - `DecisionPanel` 与 `ReviewReportComparison` 已移除 reviewer score 展示，改为仅基于提交状态与评论内容汇总
- reviewer cancel 生命周期第二阶段第一批已落地：
  - 已新增 migration：`supabase/migrations/20260309183000_review_assignment_cancel_audit.sql`
  - `review_assignments` 新增/预留：
    - `cancelled_at`
    - `cancelled_by`
    - `cancel_reason`
    - `cancel_via`
  - 已新增显式接口：
    - `POST /api/v1/reviews/assignments/{assignment_id}/cancel`
  - 行为收敛：
    - `invited/opened/accepted` 现在走 `cancel`，不再复用 `delete-unassign`
    - `DELETE /api/v1/reviews/assign/{assignment_id}` 仅允许 `selected` 早期移除
    - 稿件详情页 `Reviewer Management` 已返回 cancel 审计字段
    - reviewer history 已返回 cancel 审计字段
    - `cancelled` assignment 会立即失去 reviewer 会话访问资格
- reviewer decision / cancel 第二阶段第二批已落地：
  - 已新增显式动作接口：
    - `POST /api/v1/editor/manuscripts/{id}/review-stage-exit`
  - 行为收敛：
    - `under_review / resubmitted` 离开外审前必须至少存在一份 submitted review
    - `selected / invited / opened` reviewer 会在 exit 时自动 `cancel`
    - `accepted but not submitted` reviewer 需要 AE 显式选择后才能继续退出外审
    - `target_stage=first` 会把稿件推进到 `decision`
    - `target_stage=final` 会串行推进到 `decision_done`
  - 决策工作台规则同步收紧：
    - first decision 不再允许 `accept`
    - `Decision Workspace` 在详情页仅对 `decision / decision_done` 开放
    - 旧的 `under_review -> save first decision draft` 绕路口子已封住
  - reviewer 状态展示补全：
    - 前端 reviewer summary / management 已正式识别 `cancelled`
  - `cancelled` 不再被误显示成 `selected`

## 2026-03-10 继续推进：first decision 真动作化

- `decision` 阶段不再只是“保存建议草稿”：
  - `major_revision`
  - `minor_revision`
  - `reject`
  - `add_reviewer`
  现在都可作为第一阶段的真实提交动作
- `add_reviewer` 已实现为真实 workflow action：
  - 仅允许在 `decision` 阶段提交
  - 提交后 manuscript 退回 `under_review`
  - 不生成 author-facing `decision_letters`
  - 不触发作者通知
- `major_revision / minor_revision / reject` 在 `decision` 阶段提交时：
  - 继续保存决策信
  - 执行真实状态流转
  - 触发作者通知
- `decision_done` 阶段仍为 final decision：
  - `accept`
  - `major_revision`
  - `minor_revision`
  - `reject`
- `Decision Workspace` 前端已同步：
  - `decision` 阶段显示 `add_reviewer`
  - `decision_done` 阶段不显示 `add_reviewer`
  - `decision` 阶段按钮文案改为 `Submit First Decision`
  - 选中 `add_reviewer` 时按钮文案改为 `Return To Under Review`
  - 提交后若稿件离开 `decision / decision_done`，页面直接跳回稿件详情

## 已写计划与说明文档

- `docs/plans/2026-03-06-next16-stabilization-plan.md`
- `docs/plans/2026-03-06-next16-stabilization-notes.md`
- `docs/plans/2026-03-06-reviewer-invitation-workflow-plan.md`
- `docs/plans/2026-03-06-reviewer-invitation-state-machine-notes.md`
- `docs/plans/2026-03-09-reviewer-decision-cancel-design.md`
- `docs/plans/2026-03-09-reviewer-decision-cancel-plan.md`
- `docs/plans/2026-03-10-open-work-items.md`

## 2026-03-10 继续推进：投稿作者/通讯作者结构化

- 投稿表单已支持：
  - `submission_email`
  - `author_contacts[]`
  - 多作者
  - 唯一通讯作者
- 作者不要求预先存在 ScholarFlow 账号。
- 后端 `ManuscriptBase / ManuscriptCreate` 已接入：
  - `submission_email`
  - `author_contacts`
  - `special_issue`
- 云端 Supabase 已新增并推送：
  - `public.manuscripts.authors`
  - `public.manuscripts.submission_email`
  - `public.manuscripts.author_contacts`
  - `public.manuscripts.special_issue`
- 编辑稿件详情页已开始展示：
  - Authors
  - Corresponding Author
  - Submission Email
  - Special Issue
- 仍待继续：
  - 把其它作者通知链路统一切到 `submission_email / 对应通讯作者邮箱`
  - 决定作者侧稿件详情是否同步展示结构化作者信息

## 2026-03-10 修复：邮箱唯一性与历史重复 profile 清理

- 新增统一 email 归一化 helper：`backend/app/core/email_normalization.py`
- 以下写路径已统一改为 `strip().lower()`：
  - `UserManagementService.create_internal_user()`
  - `UserManagementService.invite_reviewer()`
  - `ReviewerService.add_to_library()`
  - `UserService.update_profile()` 的 fallback insert
  - `get_current_profile()` 自动建 profile
- Admin 创建用户 / 邀请 reviewer / reviewer library 现在都会先按归一化邮箱查重，再写入。
- 新增 migration：
  - `supabase/migrations/20260310203000_user_profiles_email_uniqueness.sql`
- migration 已完成：
  - 归一化 `public.user_profiles.email`
  - 为 `user_profiles` 新增 email normalize trigger
  - 收紧 `auth.users -> user_profiles` 的邮箱同步 trigger
  - 建立唯一索引 `user_profiles_email_unique_idx`
- 为避免 FK 链路上的历史 orphan profile 直接删除失败，migration 对重复 orphan profile 改写为唯一占位邮箱：
  - `dedup+<id>@example.invalid`
- 云端执行结果：
  - `duplicate_email_count = 0`
  - `placeholder_rewritten_count = 844`
- 仍待继续：
  - 若业务确认不再需要这些占位 orphan profile，可再补安全清理脚本

## 2026-03-11 继续推进：Academic Editor 正式模型第一阶段

- 已新增正式角色：`academic_editor`
- `journal_role_scopes` 已支持 `academic_editor`
- 云端 Supabase 已执行：
  - `supabase/migrations/20260310214500_academic_editor_binding.sql`
- `public.manuscripts` 已新增并接入：
  - `academic_editor_id`
  - `academic_submitted_at`
  - `academic_completed_at`
- AE 技术检查在选择 `送 Academic 预审（可选）` 时，现已必须指定具体学术编辑
- 新增后端候选接口：
  - `GET /api/v1/editor/academic-editors?manuscript_id=...&search=...`
- 候选来源规则：
  - 优先取当前期刊下具备 `academic_editor / editor_in_chief` scope 的用户
  - 若稿件已绑定学术编辑，则无论是否仍在 scope 查询结果里，都会保证回显
- Academic queue / 稿件详情 / decision access 已开始基于真实 `academic_editor_id` 工作：
  - 学术编辑默认只看分配给自己的 academic 稿件
  - `admin / editor_in_chief` 仍保留全局视图
  - 决策上下文已允许“已绑定的 academic editor”访问
- 前端已接入：
  - AE workspace `Submit Technical Check` 弹窗新增 `Academic Editor（必选）`
  - `/editor/academic` 标题已明确为 `Academic Editor Workspace`
- 相关验证已通过：
  - backend：`83 passed`
  - frontend：
    - Vitest 定向测试通过
    - `tests/e2e/specs/precheck_workflow.spec.ts` 通过
    - `bunx tsc --noEmit`
    - `bun run lint`

## 2026-03-11 继续推进：review-stage-exit First Decision 收件人语义

- `review-stage-exit` 在 `target_stage=first` 时，现已支持正式持久化 `recipient_emails`
- 收件人输入规则：
  - 前端弹窗默认预填当前稿件所属期刊的 `academic_editor / editor_in_chief` 邮箱
  - AE 可直接改成自己的邮箱或其他明确收件人
  - 后端统一做 `strip/lower/dedup`
- `recipient_emails` 已写入 `status_transition_logs.payload`
- Decision Workspace 右侧 `AE recommendation` 卡片现会显示：
  - recommendation
  - recipient emails
  - AE note
- 作者侧时间线可见性已补集成测试锁定：
  - 即使稿件已经离开 `under_review`
  - 后续新到达的 reviewer 公开意见仍应继续出现在 `/api/v1/manuscripts/{id}/author-context` 的 `timeline` 中
- 相关验证已通过：
  - backend：`tests/unit/test_decision_service_access.py`、`tests/integration/test_manuscript_reviews_access.py`
  - frontend：`tests/e2e/specs/decision_workspace.spec.ts`、`tests/e2e/specs/reviewer_management_delivery.spec.ts`
  - `ruff / tsc / lint` 全通过

## 当前尚未完成的 reviewer 相关工作

### P1

1. reviewer invitation history 进一步对齐参考图
   - 已完成第一阶段：
     - `review_assignments` 新增审计字段设计并已落代码：`selected_by / selected_via / invited_by / invited_via`
     - 选入拟邀请名单时记录 `selected_by=当前编辑`、`selected_via=editor_selection`
     - 首次发送 invitation 时记录 `invited_by=当前编辑`、`invited_via=template_invitation`
     - 稿件详情页左侧 `Reviewer Management` 已展示：
       - `Selected by X via ...`
       - `Invited by Y via ...`
     - reviewer history modal 已展示：
       - `Added By`
       - `Added Via`
       - `Email Actions` 中保留 delivery 事件，并可补充邀请执行人语义
   - 云端前置：需执行 `supabase/migrations/20260309120000_review_assignments_audit_fields.sql`

### P2

2. manuscript detail 中 reviewer history 展示继续增强
3. reviewer invitation history 继续向参考图靠拢：
   - `invited by / reminder by` 更细粒度展示
   - 如需要，再补独立事件表而不是继续堆字段

## 本轮突发问题

### Dashboard 角色误判

现象：任何账号登录后点击 `/dashboard`，都会提示：

> 当前账号未分配可访问的 Dashboard 角色，请联系管理员在 User Management 中补齐角色。

当前排查结论：

- 根因范围已锁定在前端 dashboard 的角色归一化逻辑。
- `frontend/src/components/dashboard/DashboardPageClient.tsx` 中的 `normalizeRoleTokens(input)` 当前只接受数组；一旦 `/api/v1/user/profile` 返回字符串或其他非数组结构，就会被错误归一化为空数组。
- `/dashboard` 的 SSR 初始数据也会把非数组 `roles` 直接丢弃，并把 `initialRolesLoaded` 标记为成功，导致页面不再补拉 profile，直接稳定误报。
- 已按 TDD 修复：
  - 新增 `frontend/src/components/dashboard/__tests__/DashboardPageClient.test.tsx`
  - 覆盖 SSR + 客户端 profile fetch 两条回归路径
  - dashboard 现已兼容字符串、JSON 风格字符串和异常拼接格式的角色载荷

## 下一步顺序

1. 继续 reviewer invitation history / email evidence 展示细化
2. 视需要把相同的 roles 归一化防御收敛到其他依赖 `/api/v1/user/profile` 的页面
3. reviewer 功能收尾后，再评估是否需要独立 reviewer assignment events 表

## 2026-03-10 继续推进：reviewer cancel 邮件模板与发送

- 已新增 reviewer cancellation 专用模板能力：
  - 新 migration：`supabase/migrations/20260310103000_email_templates_cancellation.sql`
  - 已通过本地 `supabase db push --linked` 推到云端
  - `email_templates.event_type` 现支持 `cancellation`
  - 已默认 upsert：`reviewer_cancellation_standard`

- 已新增后端 helper：
  - `backend/app/services/reviewer_assignment_cancellation_email.py`
  - 负责：
    - reviewer cancellation 模板加载（DB/fallback）
    - reviewer 邮箱与期刊标题解析
    - cancellation email tags / audit_context / idempotency key
    - 实际发送取消通知

- 手动 cancel 已接通发送逻辑：
  - `POST /api/v1/reviews/assignments/{assignment_id}/cancel`
  - 当 `send_email=true` 时，会真正发送 reviewer cancellation email
  - API 返回 `email_status / email_error`

- `review-stage-exit` 已接通取消通知：
  - `selected / invited / opened` 自动 cancel 后会发取消信
  - `accepted but not submitted` 被 AE 显式取消后也会发取消信
  - 响应增加：
    - `cancellation_email_sent_assignment_ids`
    - `cancellation_email_failed_assignment_ids`
  - 前端在失败时会 toast warning，但不会阻塞状态推进
  - 语义修正：
- `selected` 仅代表内部 shortlist，auto-cancel 时不会给 reviewer 发取消信
    - 只有 reviewer 已被真正联系过（`invited/opened/accepted/...`）才会收到 cancellation email
    - 已 `cancelled` assignment 若首次通知失败，可再次调用同一 `cancel` 接口并带 `send_email=true` 补发取消信

- Admin 模板管理已放开 cancellation 类型：
  - `backend/app/api/v1/admin/users.py`
  - `frontend/src/types/email-template.ts`
  - `frontend/src/app/admin/email-templates/page.tsx`

## 2026-03-10 继续推进：投稿作者元数据结构化

- 投稿表单已扩展为结构化作者信息输入：
  - `submission_email`
  - `author_contacts[]`
  - 每位作者包含：
    - `name`
    - `email`
    - `affiliation`
    - `is_corresponding`
- 业务规则：
  - 至少 1 位作者
  - 恰好 1 位通讯作者
  - 作者无需预先拥有 ScholarFlow 账号

- 后端 schema / API 已收口：
  - `ManuscriptCreate` 已支持：
    - `submission_email`
    - `author_contacts`
    - `special_issue`
  - `POST /api/v1/manuscripts` 已持久化：
    - `authors`
    - `submission_email`
    - `author_contacts`
    - `special_issue`

- 远端 Supabase migration 已通过本地 CLI 执行：
  - `supabase/migrations/20260310160000_submission_author_contacts.sql`

- 稿件详情页 metadata 卡片已开始展示：
  - Authors
  - Corresponding Author
  - Submission Email
  - Special Issue

- 当前这条线的剩余收尾：
  - 作者侧其他通知邮件改为优先使用 `submission_email / corresponding author`
  - 检查作者详情、导出、决策信是否仍在默认使用账号邮箱

- reviewer invitation / reminder 发送入口仍然只暴露 invitation/reminder：
  - `GET /api/v1/reviews/email-templates` 已排除 cancellation 模板
  - `POST /api/v1/reviews/assignments/{assignment_id}/send-email` 若传 cancellation 模板会直接 422

- React Email 模板工程同步更新：
  - `frontend/emails/reviewer-assignment.tsx`
  - `frontend/scripts/build-email-templates.ts`
  - `frontend/emails/generated/reviewer-assignment.templates.json`

- 本轮定向验证：
  - `cd frontend && bun run email:build-templates`
  - `cd backend && pytest -q -o addopts= tests/integration/test_editor_invite.py tests/unit/test_decision_service_access.py -k 'cancel or exit_review_stage'`
  - `cd frontend && bunx tsc --noEmit`
  - `cd frontend && bun run lint`

## 2026-03-10 继续推进：decision 边界收紧与 review-stage-exit E2E

- decision 边界已按第二阶段设计继续收紧：
  - `backend/app/services/decision_service.py`
  - `backend/app/services/decision_service_transitions.py`
  - `backend/app/services/editor_service_precheck_workspace_decisions.py`
- 新口径：
  - `Decision Workspace` 仅在 `decision / decision_done` 阶段开放
  - `under_review / resubmitted` 不再允许直接打开决策工作台
  - `final decision` 提交不再接受 `under_review / resubmitted`
  - `accept` 仅允许在 `decision_done`
  - `Final Decision Queue` 不再因为“已有 first decision draft”而把 `under_review / resubmitted` 稿件提前捞入终审队列
- 前端已同步：
  - `frontend/src/components/editor/decision/DecisionEditor.tsx`
  - `frontend/src/app/(admin)/editor/academic/page.tsx`
  - `resubmitted` 不再展示 `accept`
  - `decision` 阶段仍允许 `major_revision / minor_revision / reject`

- 已补 decision 边界红绿回归：
  - `backend/tests/unit/test_decision_service_access.py`
  - `backend/tests/unit/test_editor_service.py`
  - `backend/tests/integration/test_decision_workspace.py`
  - `frontend/src/components/editor/decision/DecisionEditor.test.ts`

- 已新增 AE `review-stage-exit` 浏览器级回归：
  - `frontend/tests/e2e/specs/reviewer_management_delivery.spec.ts`
  - 覆盖：
    - 外审阶段详情页先显示 `Exit Review Stage`
    - 未处理 accepted reviewer 时，`Continue` 会被前端拦截
    - 将 accepted reviewer 标记为 `Keep waiting` 时仍禁止退出
    - 显式改成 `Cancel reviewer` 后允许提交
    - 成功后详情页刷新到 `decision`
    - `Open Decision Workspace` 随之开放

- 本轮定向验证：
  - `cd backend && pytest -q -o addopts= tests/unit/test_decision_service_access.py tests/unit/test_editor_service.py tests/integration/test_decision_workspace.py`
  - `cd backend && uvx ruff check app/services/decision_service.py app/services/decision_service_transitions.py app/services/editor_service_precheck_workspace_decisions.py tests/unit/test_decision_service_access.py tests/unit/test_editor_service.py tests/integration/test_decision_workspace.py --select=E9,F63,F7,F82`
  - `cd frontend && bun run test:run src/components/editor/decision/DecisionEditor.test.ts 'src/app/(admin)/editor/manuscript/[id]/__tests__/helpers.reviewer-history.test.ts'`
  - `cd frontend && bun run test:e2e tests/e2e/specs/reviewer_management_delivery.spec.ts`
  - `cd frontend && bun run lint`
  - `cd frontend && bunx tsc --noEmit`

## 2026-03-10 继续推进：部署后 smoke / 平台门禁 / 最小 UAT 清单

- 新增内部平台 readiness 接口：
  - `GET /api/v1/internal/platform-readiness`
  - 仅内部调用（`X-Admin-Key`）
  - 用于检查：
    - `ADMIN_API_KEY`
    - magic link secret
    - `FRONTEND_BASE_URL`
    - `FRONTEND_ORIGIN`
    - 邮件 provider（Resend / SMTP）
    - 正式发件人地址

- 2026-03-10 晚些时候补了一轮门禁收紧：
  - `MAGIC_LINK_JWT_SECRET` 必须显式存在；仅 `SECRET_KEY` 兜底不再视为通过
  - Resend sender readiness 现在会探测 provider 域名状态，不再只看字符串存在
  - SMTP sender readiness 现在要求显式 `SMTP_FROM_EMAIL`，避免 `SMTP_USER=mailer` 这种伪通过
  - 新增内部版本接口：`GET /api/v1/internal/runtime-version`
  - `deploy-hf.yml` 会把 `DEPLOY_SHA` 写入 HF Space variable
  - `uat-smoke.yml` 会校验运行中后端 `DEPLOY_SHA` 与本次触发 SHA 一致
  - workflow 命名与 summary 也已改成 `UAT Canonical Smoke`，明确前端部分验证的是稳定 UAT URL，不宣称 Vercel commit 级绑定
    - Supabase 核心配置
  - 设计目标：
    - 不返回任何真实 secret
    - 只返回 readiness 状态、域名、布尔配置结果

- 新增 CI 脚本：
  - `scripts/ci/check-platform-readiness.sh`
  - `scripts/ci/check-supabase-linked-parity.sh`
- 平台门禁新增：
  - linked Supabase migration parity（`migration list --linked` + `db push --linked --dry-run`）
  - backend 平台 readiness internal gate

- 新增部署后 smoke workflow：
  - `.github/workflows/uat-smoke.yml`
  - 触发方式：
    - `Sync to Hugging Face Hub` 成功后自动运行
    - `workflow_dispatch`
  - 覆盖：
    - 平台门禁
    - 真实部署 Playwright smoke（Chromium）
    - artifact 上传（Playwright report）

- 新增真实部署 smoke spec：
  - `frontend/tests/e2e/specs/deployed_smoke.spec.ts`
  - 当前覆盖：
    - 首页
    - 登录
    - dashboard
    - settings
    - `/editor/process`
    - `/admin/users`
    - （可选）已发表文章页
  - 原则：
    - 只跑线上只读链路
    - 不在 smoke 里污染 UAT 业务数据

- 新增文档：
  - `docs/UAT_MINIMAL_CHECKLIST.md`
  - `docs/WORKFLOW_ASSERTIONS.md`
- 定位：
  - `UAT_MINIMAL_CHECKLIST.md`：发版后 10-15 分钟最小人工验证
  - `WORKFLOW_ASSERTIONS.md`：当前 reviewer / review-stage-exit / decision 边界的明确断言

- 本轮定向验证：
  - `cd backend && pytest -q -o addopts= tests/integration/test_internal_platform_readiness.py tests/contract/test_api_paths.py`
  - `cd backend && uvx ruff check app/api/v1/internal.py app/models/platform_readiness.py tests/integration/test_internal_platform_readiness.py tests/contract/test_api_paths.py --select=E9,F63,F7,F82`
  - `bash -n scripts/ci/check-platform-readiness.sh`
  - `bash -n scripts/ci/check-supabase-linked-parity.sh`
  - `cd frontend && bun run lint`
  - `cd frontend && bunx tsc --noEmit`
  - `cd frontend && bunx playwright test tests/e2e/specs/deployed_smoke.spec.ts --list`

## 2026-03-10 继续推进：review-stage-exit First Decision recommendation

- `review-stage-exit` 继续收敛成正式业务契约：
  - 当 `target_stage=first` 时，AE 现在必须显式选择 `requested_outcome`
  - 允许值：
    - `major_revision`
    - `minor_revision`
    - `reject`
    - `add_reviewer`
  - 当 `target_stage != first` 时，禁止携带 `requested_outcome`

- 后端改动：
  - `backend/app/models/decision.py`
    - 新增 `ReviewStageExitRequestedOutcome`
    - `ReviewStageExitRequest` 增加 `requested_outcome`
    - 使用 Pydantic `model_validator(mode='after')` 做条件校验
    - `DecisionContextResponse` 增加 `review_stage_exit_request`
  - `backend/app/services/decision_service.py`
    - `exit_review_stage()` 会把 `requested_outcome` 写入 `status_transition_logs.payload`
    - `get_decision_context()` 会回读最近一次 `review_stage_exit` 审计，供 Decision Workspace 展示

- 前端改动：
  - `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
    - `Exit Review Stage` 弹窗新增 `AE recommendation for First Decision`
  - `frontend/src/app/(admin)/editor/decision/[id]/page.tsx`
    - Decision Workspace 右侧新增 `AE recommendation` 提示卡
  - `frontend/src/services/editor-api/types.ts`
  - `frontend/src/types/decision.ts`

- 本轮定向验证：
  - `cd backend && pytest -q -o addopts= tests/unit/test_decision_service_access.py`
  - `cd backend && pytest -q -o addopts= tests/integration/test_decision_workspace.py -k 'review_stage_exit_moves_to_decision_and_cancels_pending_reviewers or review_stage_exit_allows_zero_submitted_reports'`
  - `cd backend && uvx ruff check app/models/decision.py app/services/decision_service.py app/api/v1/editor.py tests/unit/test_decision_service_access.py tests/integration/test_decision_workspace.py --select=E9,F63,F7,F82`
  - `cd frontend && bunx tsc --noEmit`
  - `cd frontend && bun run lint`

## 2026-03-10 继续推进：First Decision add_reviewer 真动作与 decision letter 语义收敛

- `Decision Workspace` 现在支持真正的 `first decision + add_reviewer` 提交动作：
  - `decision` 阶段可选：
    - `minor_revision`
    - `major_revision`
    - `reject`
    - `add_reviewer`
  - `decision_done` 阶段可选：
    - `accept`
    - `minor_revision`
    - `major_revision`
    - `reject`

- 后端状态机调整：
  - `backend/app/models/manuscript.py`
    - `decision -> under_review` 现在是合法流转
  - `backend/app/services/decision_service_transitions.py`
    - `first decision + add_reviewer` 会把 manuscript 返回 `under_review`

- decision letter 持久化语义收敛：
  - `backend/app/services/decision_service.py`
  - `backend/app/services/decision_service_letters.py`
  - 规则改成：
    - 草稿：继续只维护当前 editor 的最新 `draft`
    - first decision 提交：只允许复用当前 `draft`，不再更新“最近任意 letter”
    - final decision 提交：始终新建一条 committed `final` letter，保留 first decision 历史
    - `add_reviewer`：不生成 author-facing decision letter，并清理当前 draft，避免后续 decision 轮次把旧草稿重新带出来

- 作者侧决策文案收敛：
  - `backend/app/api/v1/manuscripts_detail_author.py`
  - 原先统一显示“最终决定”，现在改为更中性的“编辑决定”，避免 first/final decision 共存时误导作者

- 前端与文档同步：
  - `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
  - `docs/UAT_MINIMAL_CHECKLIST.md`
  - `docs/plans/2026-03-09-reviewer-decision-cancel-design.md`
  - 已统一为：
    - `first decision` 不允许 `accept`
    - `first decision` 允许 `add_reviewer`
    - `add_reviewer` 会把稿件退回 `under_review`

- 本轮定向验证：
  - `cd backend && pytest -q -o addopts= tests/unit/test_decision_service_access.py tests/unit/test_manuscript_status_model.py tests/integration/test_decision_workspace.py`
  - `cd frontend && bun run test:run src/components/editor/decision/DecisionEditor.test.ts`
  - `cd frontend && bun run test:e2e tests/e2e/specs/decision_workspace.spec.ts`
  - `cd frontend && bunx tsc --noEmit`
  - `cd frontend && bun run lint`

## 2026-03-11 继续推进：Academic Editor 第二阶段（真实绑定 + 改派）

- 后端权限与绑定模型继续收紧：
  - 新增动作 `manuscript:bind_academic_editor`
  - `POST /api/v1/editor/manuscripts/{id}/bind-academic-editor`
  - 仅 `managing_editor / editor_in_chief / admin` 可改派
  - 绑定目标必须具备 `academic_editor / editor_in_chief` 且匹配当前期刊 scope

- 安全修正：
  - 纯 `assistant_editor` 不再能查看非本人稿件的 academic editor 候选列表
  - 候选列表已去掉“无 scope 时回退到全局 profiles 模糊匹配”的 fail-open 逻辑
  - 非当前绑定学术编辑不能代替真正 assignee 提交 academic check
  - 稿件详情访问已显式允许绑定的 `academic_editor_id`

- 前端：
  - 稿件详情页 `Metadata & Staff` 新增 `Academic Editor`
  - 支持在详情页直接改派 academic editor
  - RBAC capability 已补齐 `canBindAcademicEditor`

- 测试：
  - `tests/unit/test_precheck_role_service.py`
  - `tests/integration/test_precheck_flow.py`
  - `tests/unit/test_editor_detail_runtime.py`
  - `frontend/src/lib/rbac.test.ts`
  - `cd frontend && bunx tsc --noEmit`
  - `cd frontend && bun run lint`

## 2026-03-11 继续推进：投稿作者通知链路统一

- 新增统一 helper：`backend/app/api/v1/editor_common.py -> resolve_author_notification_target(...)`
  - 作者邮件收件人优先级统一为：
    - `submission_email`
    - `corresponding author email`
    - `author profile email`
  - `recipient_name` 统一优先取通讯作者姓名，再回退到首位作者 / profile / 邮箱 local-part

- 已切换的作者侧发信入口：
  - `backend/app/api/v1/editor_precheck.py`
  - `backend/app/api/v1/editor_heavy_revision.py`
  - `backend/app/api/v1/editor_decision.py`
  - `backend/app/api/v1/editor_heavy_decision.py`
  - `backend/app/api/v1/editor_heavy_publish.py`

- 结果：
  - 技术退回
  - 修回请求
  - 最终决定
  - 发票邮件
  - 发表通知
  均不再默认只发作者账号邮箱，而是优先走投稿联系邮箱 / 通讯作者邮箱

- 新增回归测试：
  - `backend/tests/unit/test_author_notification_target.py`
  - 覆盖作者收件人优先级与技术退回 / 修回请求 / 最终决定 / 发表通知四条关键发信路径

- 本轮验证：
  - `cd backend && pytest -q -o addopts= tests/unit/test_author_notification_target.py`
  - `cd backend && pytest -q -o addopts= tests/integration/test_editor_http_methods.py`
  - `cd backend && python -m py_compile app/api/v1/editor_common.py app/api/v1/editor_precheck.py app/api/v1/editor_heavy_revision.py app/api/v1/editor_decision.py app/api/v1/editor_heavy_decision.py app/api/v1/editor_heavy_publish.py`
  - `cd backend && uvx ruff check app/api/v1/editor_common.py app/api/v1/editor_precheck.py app/api/v1/editor_heavy_revision.py app/api/v1/editor_decision.py app/api/v1/editor_heavy_decision.py app/api/v1/editor_heavy_publish.py tests/unit/test_author_notification_target.py --select=E9,F63,F7,F82`

## 2026-03-11 继续推进：Academic Editor 管理面收口

- 前端 User Management 已补齐 `academic_editor` 全链路入口：
  - `frontend/src/types/user.ts`
  - `frontend/src/components/admin/CreateUserDialog.tsx`
  - `frontend/src/components/admin/UserFilters.tsx`
  - `frontend/src/components/admin/UserRoleDialog.tsx`
  - `frontend/src/components/admin/UserTable.tsx`

- 现在已支持：
  - 创建内部账号时直接选择 `Academic Editor`
  - User Management 角色筛选里按 `Academic Editor` 过滤
  - Edit Role 弹窗里勾选 `Academic Editor`
  - `academic_editor` 与 `managing_editor/editor_in_chief` 一样要求绑定 journal scope
  - 用户列表角色 badge 正常展示 `academic_editor`

- 新增前端回归测试：
  - `frontend/src/components/admin/CreateUserDialog.test.tsx`
  - `frontend/src/components/admin/UserFilters.test.tsx`
  - `frontend/src/components/admin/UserRoleDialog.test.tsx`
  - `frontend/src/components/admin/UserTable.test.tsx`

## 2026-03-11 继续推进：Reviewer Dashboard 历史归档 + 投稿作者顺序

- Reviewer Dashboard 新增 reviewer 自己的历史归档接口与前端展示：
  - 后端：`GET /api/v1/reviews/my-history`
  - 前端：活跃任务下方增加 `My Review History`
  - 仅返回 reviewer 自己可见的数据，不暴露编辑内部信息

- 历史详情弹窗现在可查看：
  - 稿件标题/摘要
  - `Comments for Authors`
  - `Confidential Comments to Editor`
  - assignment 级 communication timeline

- 已提交历史项支持经现有 reviewer session bridge 重新进入只读 workspace

- 投稿表单新增作者顺序调整：
  - `Move Up / Move Down`
  - 按稳定 author `id` 调整，不使用数组 index 作为身份标识
  - 提交 payload 中 `author_contacts[]` 顺序与前端调整结果保持一致

- 投稿联系邮箱帮助文案已明确：
  - 可由学生/助理代投
  - 不要求与任一作者邮箱一致

- 回归测试：
  - `frontend/src/components/ReviewerDashboard.test.tsx`
  - `frontend/src/tests/SubmissionForm.test.tsx`

- 本轮验证：
  - `cd frontend && bun run test:run src/components/admin/CreateUserDialog.test.tsx src/components/admin/UserTable.test.tsx src/components/admin/UserRoleDialog.test.tsx src/components/admin/UserFilters.test.tsx`
  - `cd frontend && bun run lint`
  - `cd frontend && bunx tsc --noEmit`
