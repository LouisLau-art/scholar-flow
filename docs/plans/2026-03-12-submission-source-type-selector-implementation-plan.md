# Submission Source Type Selector Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把作者投稿页的 `Word` / `ZIP` 上传交互改成“先选 source type，再显示单一上传入口”，并保留后端 XOR 兜底。

**Architecture:** 前端新增 `Manuscript source type` 单选状态，按选择只渲染一种上传卡片；切换 source type 且已有文件时，先弹确认再清空旧文件。后端继续沿用现有 `manuscript_word_path XOR source_archive_path` 校验，不改变投稿 API 契约。

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5.x, FastAPI 0.115+, Pydantic v2, Supabase Storage, Vitest

---

## Execution Checklist

- [x] Task 1: 前端 source type 选择器与单一上传入口
- [x] Task 2: 切换 source type 的确认弹窗与清空逻辑
- [x] Task 3: 文案与提交门禁同步
- [x] Task 4: 最小测试与文档同步

### Task 1: Source Type Selector

**Files:**
- Modify: `frontend/src/components/SubmissionForm.tsx`
- Modify: `frontend/src/components/submission/use-submission-form.ts`
- Modify: `frontend/src/components/submission/index.ts`
- Modify: `frontend/src/tests/SubmissionForm.test.tsx`

**Step 1: Write the failing tests**

- 未选择 source type 时，不显示 Word/ZIP 上传卡片
- 选择 `Word` 后，只显示 Word 上传卡片
- 选择 `ZIP` 后，只显示 ZIP 上传卡片

**Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && bun run vitest run src/tests/SubmissionForm.test.tsx -t 'source type'
```

**Step 3: Write minimal implementation**

- 新增 `selectedSourceType: 'word' | 'zip' | null`
- `SubmissionForm` 基于 `selectedSourceType` 只渲染一种上传卡片
- 移除“两个上传框同时出现”的默认展示

**Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && bun run vitest run src/tests/SubmissionForm.test.tsx -t 'source type'
```

### Task 2: Switch Confirmation

**Files:**
- Modify: `frontend/src/components/SubmissionForm.tsx`
- Modify: `frontend/src/components/submission/use-submission-form.ts`
- Optional Create: `frontend/src/components/submission/SubmissionSourceTypeSwitchDialog.tsx`
- Modify: `frontend/src/tests/SubmissionForm.test.tsx`

**Step 1: Write the failing tests**

- 已上传 Word 时切换到 ZIP，会弹确认
- 已上传 ZIP 时切换到 Word，会弹确认
- 确认后清空旧 source 文件
- 取消后保留原 source 文件

**Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && bun run vitest run src/tests/SubmissionForm.test.tsx -t 'switch manuscript source'
```

**Step 3: Write minimal implementation**

- 切换 source type 时，如果当前 source 已有文件：
  - 打开确认弹窗
  - 确认后执行 clear
  - 取消则保持原状态
- 清空时重置：
  - 对应 file state
  - 对应 uploaded path
  - 对应 error state
  - file input key

**Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && bun run vitest run src/tests/SubmissionForm.test.tsx -t 'switch manuscript source'
```

### Task 3: Copy And Submission Gating

**Files:**
- Modify: `frontend/src/components/submission/SubmissionWordUploadCard.tsx`
- Modify: `frontend/src/components/submission/SubmissionSourceArchiveUploadCard.tsx`
- Modify: `frontend/src/components/submission/use-submission-form.ts`
- Modify: `frontend/src/tests/SubmissionForm.test.tsx`

**Step 1: Write the failing tests**

- Finalize 在未选 source type 或未上传 source 文件前保持不可用
- 选定 source type 后，相关提示文案正确
- 不再出现“自动替换另一路文件”的交互

**Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && bun run vitest run src/tests/SubmissionForm.test.tsx -t 'finalize|latex zip route|word manuscript'
```

**Step 3: Write minimal implementation**

- 文案改成 `Choose one manuscript source`
- submit gating 绑定到：
  - `selectedSourceType`
  - 当前 source 文件是否已成功上传
- 删除“上传第二个文件会自动替换第一个”的说明

**Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && bun run vitest run src/tests/SubmissionForm.test.tsx -t 'finalize|latex zip route|word manuscript'
```

### Task 4: Minimal Verification And Docs Sync

**Files:**
- Modify: `docs/plans/2026-03-11-current-workflow-for-uat.md`
- Modify: `docs/plans/2026-03-10-open-work-items.md`

**Step 1: Run minimal verification**

```bash
cd frontend && bun run vitest run src/tests/SubmissionForm.test.tsx
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/test_manuscripts.py -q -k 'source_archive or cover_letter or manuscript_word'
```

Note:

- `bunx tsc --noEmit` 当前仓库有一条与本任务无关的既有 e2e 类型错误，若仍存在，不在本任务顺手扩大修复。

**Step 2: Sync docs**

- 更新作者投稿真实交互规则
- 记录“先选 source type，再显示单一上传区”

## Result

- 作者投稿页不再同时暴露 `Word` 与 `ZIP` 两个上传入口
- `Word` / `ZIP` 的互斥关系由 UI 直接表达，而不是靠用户试错
- 后端仍保留 XOR 校验，保证错误请求无法落库
- 已完成最小验证：
  - `cd frontend && bun run vitest run src/tests/SubmissionForm.test.tsx`
  - `cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_asyncio.plugin -o addopts='' tests/test_manuscripts.py -q -k 'source_archive or cover_letter or manuscript_word'`

---

Plan complete and saved to `docs/plans/2026-03-12-submission-source-type-selector-implementation-plan.md`.

Two execution options:

**1. Subagent-Driven (this session)** - 我在当前会话按计划逐步实施、逐步验证  
**2. Parallel Session (separate)** - 新开一个会话，按 executing-plans 批量执行

当前更适合 `1`，因为这次范围集中在作者投稿表单。
