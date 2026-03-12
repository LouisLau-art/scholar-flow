# Notification Email Orchestration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为外部通知链路补齐统一邮件编排能力，支持 `To / CC / BCC / Reply-To / Attachments`、作者收件人重算、Invoice PDF 附件发送，以及“外部已发送”补登记，同时保证邮件不阻塞业务流程。

**Architecture:** 在现有站内信和散落邮件逻辑之上新增一层 `NotificationOrchestrator + RecipientResolver`。自动事件继续由后端内部触发，人工 / 半人工事件暴露 `preview / send / resend / mark-external-sent`，并统一写入扩展后的 `email_logs`。

**Tech Stack:** FastAPI 0.115, Pydantic v2, Supabase PostgreSQL, Resend/SMTP, Next.js 16 App Router, React 19, TypeScript 5, pytest, Vitest, Playwright

---

## Task 1: 先锁定数据模型与日志契约

**Files:**
- Create: `supabase/migrations/20260312xxxx_add_journal_public_editorial_email.sql`
- Create: `supabase/migrations/20260312xxxx_expand_email_logs_for_delivery_envelope.sql`
- Modify: `backend/app/models/email_log.py`
- Test: `backend/tests/unit/test_mail.py`

**Step 1: Write the failing tests**

补充后端单测，锁定：

- `email_logs` 模型允许记录 `to / cc / bcc / reply_to`
- 日志能记录 `delivery_mode / communication_status / attachment_count`

**Step 2: Run tests to verify they fail**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/unit/test_mail.py -q
```

Expected:

- FAIL，因为当前日志结构还没有这些字段。

**Step 3: Write minimal implementation**

- 新增 `journals.public_editorial_email`
- 扩展 `email_logs`
- 同步更新 ORM / Pydantic 兼容结构

**Step 4: Run tests to verify they pass**

Run the same command.

**Step 5: Commit**

```bash
git add supabase/migrations/20260312xxxx_add_journal_public_editorial_email.sql \
        supabase/migrations/20260312xxxx_expand_email_logs_for_delivery_envelope.sql \
        backend/app/models/email_log.py \
        backend/tests/unit/test_mail.py
git commit -m "feat: extend journal and email log delivery schema"
```

## Task 2: 升级邮件核心发送能力

**Files:**
- Modify: `backend/app/core/mail.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/unit/test_mail.py`
- Test: `backend/tests/unit/test_reviews_email_idempotency.py`

**Step 1: Write the failing tests**

锁定：

- 单封邮件支持 `to / cc / bcc / reply_to / attachments`
- idempotency key 仍按单封发送工作
- 附件只走单封接口，不走 batch

**Step 2: Run tests to verify they fail**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/unit/test_mail.py tests/unit/test_reviews_email_idempotency.py -q
```

Expected:

- FAIL，因为当前发送 envelope 不完整或附件能力缺失。

**Step 3: Write minimal implementation**

- 在 `mail.py` 中引入统一 `EmailEnvelope`
- 扩展 Resend/SMTP 发送逻辑
- 发送成功后按新字段写入 `email_logs`

**Step 4: Run tests to verify they pass**

Run the same command.

**Step 5: Commit**

```bash
git add backend/app/core/mail.py \
        backend/app/core/config.py \
        backend/tests/unit/test_mail.py \
        backend/tests/unit/test_reviews_email_idempotency.py
git commit -m "feat: add email envelope recipients and attachments support"
```

## Task 3: 建立统一收件人解析与通知编排服务

**Files:**
- Create: `backend/app/services/email_recipient_resolver.py`
- Create: `backend/app/services/notification_orchestrator.py`
- Modify: `backend/app/api/v1/editor_common.py`
- Modify: `backend/app/services/notification_service.py`
- Test: `backend/tests/unit/test_notification_orchestrator.py`

**Step 1: Write the failing tests**

锁定：

- 作者类默认 `To = all corresponding authors`
- 其他作者与 `journal.public_editorial_email` 进入 `CC`
- `submission_email` 仅兜底
- 相同邮箱会被去重

**Step 2: Run tests to verify they fail**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/unit/test_notification_orchestrator.py -q
```

Expected:

- FAIL，因为当前没有统一 resolver / orchestrator，作者收件人仍优先 `submission_email`。

**Step 3: Write minimal implementation**

- 新建 `email_recipient_resolver.py`
- 新建 `notification_orchestrator.py`
- 把现有作者收件人解析改为新策略
- 先保留旧业务入口，但底层改调新服务

**Step 4: Run tests to verify they pass**

Run the same command.

**Step 5: Commit**

```bash
git add backend/app/services/email_recipient_resolver.py \
        backend/app/services/notification_orchestrator.py \
        backend/app/api/v1/editor_common.py \
        backend/app/services/notification_service.py \
        backend/tests/unit/test_notification_orchestrator.py
git commit -m "feat: add notification orchestrator and recipient resolver"
```

## Task 4: 打通人工邮件的统一 API 契约

**Files:**
- Modify: `backend/app/api/v1/reviews.py`
- Modify: `backend/app/api/v1/editor_precheck.py`
- Modify: `backend/app/api/v1/editor_heavy_revision.py`
- Modify: `backend/app/api/v1/invoices.py`
- Test: `backend/tests/integration/test_notifications.py`
- Test: `backend/tests/unit/test_manual_email_api_contract.py`

**Step 1: Write the failing tests**

锁定：

- 人工 / 半人工场景支持 `preview / send / mark-external-sent`
- `preview` 返回 `resolved_recipients / subject / html / text / attachments / idempotency_key`
- `send` 支持 recipient overrides
- `mark-external-sent` 能落库为 `external_sent`

**Step 2: Run tests to verify they fail**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/unit/test_manual_email_api_contract.py tests/integration/test_notifications.py -q
```

Expected:

- FAIL，因为现有 API 不支持统一 envelope 和外部补登记。

**Step 3: Write minimal implementation**

- reviewer invitation/reminder 升级为统一 envelope
- technical revision / revision request / invoice preview-send API 建立统一契约
- 新增 `mark-external-sent`

**Step 4: Run tests to verify they pass**

Run the same command.

**Step 5: Commit**

```bash
git add backend/app/api/v1/reviews.py \
        backend/app/api/v1/editor_precheck.py \
        backend/app/api/v1/editor_heavy_revision.py \
        backend/app/api/v1/invoices.py \
        backend/tests/unit/test_manual_email_api_contract.py \
        backend/tests/integration/test_notifications.py
git commit -m "feat: unify manual email preview send and external sent APIs"
```

## Task 5: 重做 invoice 邮件为 PDF 附件发送

**Files:**
- Modify: `backend/app/api/v1/editor_heavy_decision.py`
- Modify: `backend/app/api/v1/editor_decision.py`
- Modify: `backend/app/services/invoice_pdf_service.py`
- Modify: `backend/app/api/v1/invoices.py`
- Test: `backend/tests/integration/test_invoice_pdf_generation.py`
- Test: `backend/tests/integration/test_invoice_pdf_download.py`
- Test: `backend/tests/integration/test_finance_invoices_sync.py`

**Step 1: Write the failing tests**

锁定：

- accept 后只生成 / 更新 invoice PDF，不自动给作者发 invoice link 邮件
- invoice email 发送时使用单封附件邮件
- `mark-external-sent` 不阻塞 invoice 生命周期

**Step 2: Run tests to verify they fail**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/integration/test_invoice_pdf_generation.py tests/integration/test_invoice_pdf_download.py tests/integration/test_finance_invoices_sync.py -q
```

Expected:

- FAIL，因为当前 accept path 仍有自动 link 邮件逻辑，且附件发信链路未接入。

**Step 3: Write minimal implementation**

- 去掉 accept 时自动发 invoice link 邮件
- 保留 invoice PDF 生成
- `POST /api/v1/invoices/{id}/email/send` 改为后端读取 PDF bytes 后作为附件发送

**Step 4: Run tests to verify they pass**

Run the same command.

**Step 5: Commit**

```bash
git add backend/app/api/v1/editor_heavy_decision.py \
        backend/app/api/v1/editor_decision.py \
        backend/app/services/invoice_pdf_service.py \
        backend/app/api/v1/invoices.py \
        backend/tests/integration/test_invoice_pdf_generation.py \
        backend/tests/integration/test_invoice_pdf_download.py \
        backend/tests/integration/test_finance_invoices_sync.py
git commit -m "feat: send invoice emails with pdf attachments"
```

## Task 6: 接入自动事件与 proof / decision 场景

**Files:**
- Modify: `backend/app/api/v1/manuscripts_submission.py`
- Modify: `backend/app/services/first_decision_request_email.py`
- Modify: `backend/app/services/reviewer_assignment_cancellation_email.py`
- Modify: `backend/app/services/decision_service.py`
- Modify: `backend/app/services/decision_service_transitions.py`
- Modify: `backend/app/services/production_workspace_service_workflow_cycle.py`
- Modify: `backend/app/services/production_workspace_service_workflow_cycle_writes.py`
- Modify: `backend/app/services/production_workspace_service_workflow_author.py`
- Test: `backend/tests/integration/test_decision_workspace.py`
- Test: `backend/tests/integration/test_production_workspace_api.py`

**Step 1: Write the failing tests**

锁定：

- 投稿成功自动发作者邮件
- first decision request 自动发 AE / EIC
- reviewer cancellation 自动发 reviewer
- proofreading 首次通知自动发作者
- proofreading 再次通知改走半自动 / 手动链路
- `production approved` 不再单独外发

**Step 2: Run tests to verify they fail**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/integration/test_decision_workspace.py tests/integration/test_production_workspace_api.py -q
```

Expected:

- FAIL，因为当前这些场景尚未统一接入 orchestrator。

**Step 3: Write minimal implementation**

- 自动事件改由 orchestrator 派发
- proofreading 首轮与二次通知拆分策略
- 去掉 `production approved` 的作者外发逻辑

**Step 4: Run tests to verify they pass**

Run the same command.

**Step 5: Commit**

```bash
git add backend/app/api/v1/manuscripts_submission.py \
        backend/app/services/first_decision_request_email.py \
        backend/app/services/reviewer_assignment_cancellation_email.py \
        backend/app/services/decision_service.py \
        backend/app/services/decision_service_transitions.py \
        backend/app/services/production_workspace_service_workflow_cycle.py \
        backend/app/services/production_workspace_service_workflow_cycle_writes.py \
        backend/app/services/production_workspace_service_workflow_author.py \
        backend/tests/integration/test_decision_workspace.py \
        backend/tests/integration/test_production_workspace_api.py
git commit -m "feat: route automatic decision and proofreading emails through orchestrator"
```

## Task 7: 实现前端统一邮件发送弹窗与 reviewer compose 扩展

**Files:**
- Create: `frontend/src/components/editor/EmailComposeDialog.tsx`
- Modify: `frontend/src/components/editor/ReviewerEmailPreviewDialog.tsx`
- Modify: `frontend/src/components/editor/ReviewerEmailPreviewDialog.test.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- Modify: `frontend/src/services/editor-api/manuscripts.ts`
- Test: `frontend/tests/e2e/specs/reviewer_management_delivery.spec.ts`

**Step 1: Write the failing tests**

锁定：

- reviewer invitation/reminder 弹窗支持 `To / CC / BCC / Reply-To`
- 发送弹窗提供：
  - `Send via ScholarFlow`
  - `Copy Email Content`
  - `Mark as Sent Externally`
- invoice / author 类邮件可复用同一 compose 结构

**Step 2: Run tests to verify they fail**

Run:

```bash
cd frontend && bun run vitest run src/components/editor/ReviewerEmailPreviewDialog.test.tsx
cd frontend && PLAYWRIGHT_WEB_SERVER=1 bunx playwright test tests/e2e/specs/reviewer_management_delivery.spec.ts --project=chromium
```

Expected:

- FAIL，因为当前 reviewer 弹窗尚未支持完整 envelope 和外部已发送操作。

**Step 3: Write minimal implementation**

- 抽出通用 compose dialog
- reviewer 现有弹窗基于通用 dialog 适配
- manuscript detail 页接入作者 / invoice / proofreading 发送弹窗

**Step 4: Run tests to verify they pass**

Run the same command plus:

```bash
cd frontend && bunx tsc --noEmit
```

**Step 5: Commit**

```bash
git add frontend/src/components/editor/EmailComposeDialog.tsx \
        frontend/src/components/editor/ReviewerEmailPreviewDialog.tsx \
        frontend/src/components/editor/ReviewerEmailPreviewDialog.test.tsx \
        frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx \
        frontend/src/services/editor-api/manuscripts.ts \
        frontend/tests/e2e/specs/reviewer_management_delivery.spec.ts
git commit -m "feat: add unified email compose dialog for editor flows"
```

## Task 8: 增加 provider webhook 回写与最小文档同步

**Files:**
- Modify: `backend/app/api/v1/internal.py`
- Create: `backend/tests/unit/test_email_webhook_events.py`
- Modify: `docs/plans/2026-03-11-current-workflow-for-uat.md`
- Modify: `docs/plans/2026-03-10-open-work-items.md`

**Step 1: Write the failing tests**

锁定：

- provider webhook 至少能把 `delivered / bounced / opened` 映射回 `email_logs`
- 无法匹配 provider message id 时不应 500

**Step 2: Run tests to verify they fail**

Run:

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/unit/test_email_webhook_events.py -q
```

Expected:

- FAIL，因为当前 webhook 还没有状态回写。

**Step 3: Write minimal implementation**

- 增加 webhook 事件映射和日志更新
- 同步补充 UAT / open work items 文档

**Step 4: Run tests to verify they pass**

Run the same command.

**Step 5: Commit**

```bash
git add backend/app/api/v1/internal.py \
        backend/tests/unit/test_email_webhook_events.py \
        docs/plans/2026-03-11-current-workflow-for-uat.md \
        docs/plans/2026-03-10-open-work-items.md
git commit -m "feat: sync email delivery webhook events"
```

## Minimal Validation Set

```bash
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' \
  tests/unit/test_mail.py \
  tests/unit/test_reviews_email_idempotency.py \
  tests/unit/test_notification_orchestrator.py \
  tests/unit/test_manual_email_api_contract.py \
  tests/unit/test_email_webhook_events.py \
  tests/integration/test_notifications.py \
  tests/integration/test_invoice_pdf_generation.py \
  tests/integration/test_invoice_pdf_download.py \
  tests/integration/test_finance_invoices_sync.py \
  tests/integration/test_decision_workspace.py \
  tests/integration/test_production_workspace_api.py -q

cd frontend && bun run vitest run src/components/editor/ReviewerEmailPreviewDialog.test.tsx
cd frontend && bunx tsc --noEmit
cd frontend && PLAYWRIGHT_WEB_SERVER=1 bunx playwright test tests/e2e/specs/reviewer_management_delivery.spec.ts --project=chromium
```

## Notes for Execution

- 先落后端 envelope、recipient resolver 和日志扩展，再接前端。
- 任何需要写邮件正文的人工场景，都必须同时支持 `Mark as Sent Externally`。
- 如果执行过程中发现某条历史链路过度耦合，优先把底层发送逻辑收敛到 orchestrator，再回填旧 endpoint。
