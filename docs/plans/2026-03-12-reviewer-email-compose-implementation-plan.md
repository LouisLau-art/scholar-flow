# Reviewer Email Compose Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让 AE / ME 在 reviewer email 发送前弹窗中直接编辑本次发送的 `Subject` 和 `HTML Body`，并让 `Plain Text` 自动跟随当前 HTML 派生，保证预览和真实发送一致。

**Architecture:** 保留现有 reviewer email preview/send API，但新增一次性 compose overrides：前端在弹窗内维护 `editableSubject` 和 `editableHtml`，后端 preview/send 支持接收 override 并始终从最终 HTML 派生 plain text。底层模板不回写，仍由高权限角色单独维护。

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5, Tiptap React, FastAPI 0.115, Pydantic v2, Vitest, Playwright, pytest

---

## Task 1: 锁定 reviewer email compose 行为

**Files:**
- Modify: `frontend/src/components/editor/ReviewerEmailPreviewDialog.test.tsx`
- Test: `backend/tests/unit/test_mail.py`
- Test: `backend/tests/unit/test_reviews_email_preview.py` (new)

**Step 1: Write the failing tests**

前端新增用例，锁定：

- `Subject` 可编辑
- `HTML Body` 可编辑
- `Plain Text` 只读且会根据当前 HTML 更新

后端新增用例，锁定：

- preview/send 接收到 `subject_override/body_html_override` 时，返回/发送的 plain text 来自最终 HTML

**Step 2: Run tests to verify they fail**

Run:

```bash
cd frontend && bun run vitest run src/components/editor/ReviewerEmailPreviewDialog.test.tsx
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/unit/test_mail.py tests/unit/test_reviews_email_preview.py -q
```

Expected:

- 前端失败在 reviewer preview 仍为只读
- 后端失败在 payload 不支持 override 或 text 仍不由 HTML 派生

**Step 3: Write minimal implementation**

- 扩展 reviewer email preview/send payload 支持：
  - `subject_override`
  - `body_html_override`
- reviewer email render/send path 增加 `force_plain_text_from_html`
- 前端 test data/types 同步新增 override compose 形态

**Step 4: Run tests to verify they pass**

Run the same commands.

**Step 5: Commit**

```bash
git add frontend/src/components/editor/ReviewerEmailPreviewDialog.test.tsx \
        backend/tests/unit/test_mail.py \
        backend/tests/unit/test_reviews_email_preview.py \
        backend/app/api/v1/reviews.py \
        backend/app/core/mail.py
git commit -m "feat: support reviewer email compose overrides"
```

## Task 2: 实现 reviewer email 专用富文本编辑器

**Files:**
- Create: `frontend/src/components/editor/ReviewerEmailComposeEditor.tsx`
- Modify: `frontend/src/components/editor/ReviewerEmailPreviewDialog.tsx`

**Step 1: Write the failing test**

新增或扩展前端测试，锁定：

- toolbar 至少包含 `Bold / Italic / Underline / Bullets / Numbered / Link`
- 弹窗打开后用 preview html 初始化 editor
- editor 改动会回调到父组件

**Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && bun run vitest run src/components/editor/ReviewerEmailPreviewDialog.test.tsx
```

Expected: FAIL because editor is still iframe/read-only.

**Step 3: Write minimal implementation**

- 新建 reviewer email 专用 Tiptap editor
- 使用 `StarterKit + Underline + Link`
- 不接入图片上传
- 保持最小 toolbar
- 用 editor HTML 作为唯一正文编辑源

**Step 4: Run test to verify it passes**

Run the same test command.

**Step 5: Commit**

```bash
git add frontend/src/components/editor/ReviewerEmailComposeEditor.tsx \
        frontend/src/components/editor/ReviewerEmailPreviewDialog.tsx \
        frontend/src/components/editor/ReviewerEmailPreviewDialog.test.tsx
git commit -m "feat: add reviewer email compose editor"
```

## Task 3: 接入 manuscript detail 页状态与发送动作

**Files:**
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/types.ts`
- Modify: `frontend/src/services/editor-api/manuscripts.ts`

**Step 1: Write the failing test**

锁定：

- 打开 reviewer email preview 时，初始化 `editableSubject/editableHtml`
- 点击发送时，把 `subject_override/body_html_override/recipient_email` 一起提交
- 改 recipient 为非 reviewer 邮箱时，仍显示 preview/test send 提示

**Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && bun run vitest run src/components/editor/ReviewerEmailPreviewDialog.test.tsx src/components/editor/ReviewerAssignmentSearch.test.tsx
```

Expected: FAIL because send payload 仍只带 `template_key/recipient_email`。

**Step 3: Write minimal implementation**

- 在 manuscript detail 页面增加 compose state：
  - `reviewerEmailPreviewSubject`
  - `reviewerEmailPreviewHtml`
- preview 成功后初始化这两个 state
- send 时提交 override 字段
- 更新前端 API payload type

**Step 4: Run test to verify it passes**

Run the same test command plus:

```bash
cd frontend && bunx tsc --noEmit
```

**Step 5: Commit**

```bash
git add frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx \
        frontend/src/app/(admin)/editor/manuscript/[id]/types.ts \
        frontend/src/services/editor-api/manuscripts.ts
git commit -m "feat: wire reviewer email compose state"
```

## Task 4: 补最小高层 smoke 与文档

**Files:**
- Modify: `frontend/tests/e2e/specs/reviewer_management_delivery.spec.ts`
- Modify: `docs/plans/2026-03-10-open-work-items.md`
- Modify: `docs/plans/2026-03-11-current-workflow-for-uat.md`

**Step 1: Write the failing smoke**

锁定：

- reviewer email preview 里可以修改 subject/html
- 右侧 plain text 会更新
- send 请求带 override

**Step 2: Run smoke to verify it fails**

Run:

```bash
cd frontend && PLAYWRIGHT_WEB_SERVER=1 bunx playwright test tests/e2e/specs/reviewer_management_delivery.spec.ts -g 'reviewer email compose uses editable subject and html overrides' --project=chromium
```

Expected: FAIL because dialog is still preview-only or request payload缺 override.

**Step 3: Write minimal implementation**

- 调整 mocked e2e route
- 补 smoke 断言
- 同步文档口径

**Step 4: Run smoke to verify it passes**

Run the same Playwright command.

**Step 5: Commit**

```bash
git add frontend/tests/e2e/specs/reviewer_management_delivery.spec.ts \
        docs/plans/2026-03-10-open-work-items.md \
        docs/plans/2026-03-11-current-workflow-for-uat.md
git commit -m "test: cover reviewer email compose flow"
```

## Minimal Validation Set

```bash
cd frontend && bun run vitest run src/components/editor/ReviewerEmailPreviewDialog.test.tsx
cd frontend && bunx tsc --noEmit
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/unit/test_mail.py tests/unit/test_reviews_email_preview.py -q
cd frontend && PLAYWRIGHT_WEB_SERVER=1 bunx playwright test tests/e2e/specs/reviewer_management_delivery.spec.ts -g 'reviewer email compose uses editable subject and html overrides' --project=chromium
```
