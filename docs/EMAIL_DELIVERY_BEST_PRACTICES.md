# Email Delivery Best Practices (ScholarFlow)

## 当前实现（2026-03-06）

- Provider: `Resend`（后备支持 SMTP）
- 发送入口：
  - `backend/app/core/mail.py`
  - `POST /api/v1/reviews/assignments/{assignment_id}/send-email`
- 模板管理：
  - DB 表 `public.email_templates`
  - Admin 页面 `/admin/email-templates`

## 已落地最佳实践

1. 幂等发送（Idempotency）
- 审稿邮件发送会携带 `idempotency_key`。
- invitation 使用固定 key（防重复点击）。
- reminder 使用“按小时”key（短时防抖，可跨小时重发）。

2. 仅对可恢复错误重试
- 仅重试 `429` / `5xx` / 网络抖动。
- `400/422` 等参数错误不重试，避免重复打 API。

3. Tags 与 Headers
- 每封审稿邮件附带 `scene/event/template/assignment_id/manuscript_id/journal` tags。
- 附带 `X-SF-*` headers，便于链路追踪。

4. HTML + Text 双通道
- 模板未提供 text 时，后端自动从 HTML 生成 plain text fallback。

5. Webhook 验签
- 新增 `POST /api/v1/internal/webhooks/resend`。
- 使用 `RESEND_WEBHOOK_SECRET` + `svix-*` headers 验签。

## React Email 工程化

- React 模板源码：`frontend/emails/reviewer-assignment.tsx`
- 构建命令：`cd frontend && bun run email:build-templates`
- 产物：`frontend/emails/generated/reviewer-assignment.templates.json`

说明：
- 该 JSON 可作为 Admin 模板导入/同步来源；
- 变量占位符与后端上下文一致（如 `{{ reviewer_name }}`）。
