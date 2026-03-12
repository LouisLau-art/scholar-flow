# Submission Word/ZIP Routing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把作者投稿页改成 `PDF + Cover Letter + (Word xor ZIP)` 的上传模型，并让 ZIP 作为仅存储文件进入编辑部文件仓库。

**Architecture:** 前端把 Word 与 ZIP 改成互斥二选一上传组；后端 `ManuscriptCreate` 与创建接口同步改成 XOR 校验；ZIP 不进入 `/manuscripts/upload` 解析接口，只作为 `manuscript_files.file_type=source_archive` 持久化。编辑详情页沿用现有 `FileHubCard`，把 `source_archive` 归到 `Manuscript Versions`。

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5.x, FastAPI 0.115+, Pydantic v2, Supabase Storage, Vitest, pytest

---

## Execution Checklist

- [x] Task 1: 后端 XOR 校验与持久化
- [x] Task 2: 前端互斥上传 UI 与提交门禁
- [x] Task 3: 编辑详情页显示 ZIP
- [x] Task 4: 最小回归与文档同步

### Task 1: Backend XOR Validation And Persistence

**Files:**
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/app/api/v1/manuscripts_submission.py`
- Test: `backend/tests/test_manuscripts.py`

**Step 1: Write the failing tests**

- 新增/调整用例：
  - `pdf + cover + word` 可提交
  - `pdf + cover + zip` 可提交
  - `word + zip` 同时出现时返回 422
  - `word/zip` 都缺失时返回 422
  - `source_archive` 写入 `manuscript_files`

**Step 2: Run test to verify they fail**

Run:

```bash
cd backend && pytest tests/test_manuscripts.py -q --no-cov -k 'source_archive or cover_letter or manuscript_word'
```

**Step 3: Write minimal implementation**

- 给 `ManuscriptBase` 增加 `source_archive_*`
- 用 `model_validator(mode="after")` 校验 `manuscript_word_path XOR source_archive_path`
- 创建稿件接口取消 `manuscript_word_path` 的强制必填
- 增加 `source_archive_path` 的路径与后缀 `.zip` 校验
- 持久化 `file_type=source_archive`

**Step 4: Run tests to verify they pass**

Run:

```bash
cd backend && pytest tests/test_manuscripts.py -q --no-cov -k 'source_archive or cover_letter or manuscript_word'
```

### Task 2: Frontend Exclusive Upload UI

**Files:**
- Modify: `frontend/src/components/submission/use-submission-form.ts`
- Modify: `frontend/src/components/SubmissionForm.tsx`
- Modify: `frontend/src/components/submission/SubmissionWordUploadCard.tsx`
- Create: `frontend/src/components/submission/SubmissionSourceArchiveUploadCard.tsx`
- Modify: `frontend/src/components/submission/index.ts`
- Modify: `frontend/src/components/submission/submission-form-utils.ts`
- Test: `frontend/src/tests/SubmissionForm.test.tsx`

**Step 1: Write the failing tests**

- Word 与 ZIP 二选一
- ZIP 上传成功后不调用 `/api/v1/manuscripts/upload`
- 提交按钮在 `pdf + cover + (word xor zip)` 时可用
- 同时选择 Word 和 ZIP 时，前端会清空另一项或阻止第二项

**Step 2: Run test to verify they fail**

Run:

```bash
cd frontend && bun run vitest run src/tests/SubmissionForm.test.tsx
```

**Step 3: Write minimal implementation**

- 新增 ZIP 文件状态与上传 handler
- `isSupportedSourceArchive(file)` 只接受 `.zip`
- ZIP 直接上传到 Storage，不调用解析接口
- `submitDisabled` 与 `showValidationHint` 改成 `fileValid && coverLetterValid && (word xor zip)`
- 提交 payload 增加 `source_archive_*`
- 更新区块文案为 Optional / XOR

**Step 4: Run tests to verify they pass**

Run:

```bash
cd frontend && bun run vitest run src/tests/SubmissionForm.test.tsx
cd frontend && bunx tsc --noEmit
```

### Task 3: Editor Detail File Hub

**Files:**
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/helpers.ts`
- Optional modify: `frontend/src/components/editor/FileHubCard.tsx`
- Test: `frontend/src/app/(admin)/editor/manuscript/[id]/__tests__/helpers.workflow.test.ts`

**Step 1: Write the failing test**

- `source_archive` 会被归到 `manuscriptFiles`

**Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && bun run vitest run 'src/app/(admin)/editor/manuscript/[id]/__tests__/helpers.workflow.test.ts'
```

**Step 3: Write minimal implementation**

- `buildFileHubProps()` 把 `source_archive` 合并到 `manuscriptFiles`

**Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && bun run vitest run 'src/app/(admin)/editor/manuscript/[id]/__tests__/helpers.workflow.test.ts'
```

### Task 4: Minimal Verification And Docs Sync

**Files:**
- Modify: `docs/plans/2026-03-11-current-workflow-for-uat.md`
- Modify: `docs/plans/2026-03-10-open-work-items.md`

**Step 1: Run minimal verification**

```bash
cd backend && pytest tests/test_manuscripts.py -q --no-cov -k 'source_archive or cover_letter or manuscript_word'
cd frontend && bun run vitest run src/tests/SubmissionForm.test.tsx
cd frontend && bun run vitest run 'src/app/(admin)/editor/manuscript/[id]/__tests__/helpers.workflow.test.ts'
cd frontend && bunx tsc --noEmit
```

**Step 2: Sync docs**

- 更新当前真实上传规则
- 记录 ZIP 不参与 AI 解析

## Result

- 作者投稿链路已切到 `PDF + Cover Letter + (Word xor ZIP)`
- ZIP 只上传到 Storage，并持久化为 `manuscript_files.file_type=source_archive`
- ZIP 不调用 `/api/v1/manuscripts/upload`，不参与 AI 元数据解析
- 编辑详情页 `File Hub` 已展示 `source_archive`

---

Plan complete and saved to `docs/plans/2026-03-12-submission-word-zip-routing-implementation-plan.md`.
