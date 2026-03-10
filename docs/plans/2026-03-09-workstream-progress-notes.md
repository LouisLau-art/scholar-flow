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

## 已写计划与说明文档

- `docs/plans/2026-03-06-next16-stabilization-plan.md`
- `docs/plans/2026-03-06-next16-stabilization-notes.md`
- `docs/plans/2026-03-06-reviewer-invitation-workflow-plan.md`
- `docs/plans/2026-03-06-reviewer-invitation-state-machine-notes.md`
- `docs/plans/2026-03-09-reviewer-decision-cancel-design.md`
- `docs/plans/2026-03-09-reviewer-decision-cancel-plan.md`

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
