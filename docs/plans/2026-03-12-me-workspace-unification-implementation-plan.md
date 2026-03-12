# Managing Workspace 单页收口与首屏稳定性修复 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 Managing Workspace 收口为 ME 唯一主工作面，并在同一轮修复首屏受保护请求不稳定、错误态缺失、缓存失效不完整的问题。

**Architecture:** 保留后端现有 `workspace_bucket` 语义，把 `Managing Workspace` 作为前端唯一主读模型，`intake` 仅作为默认分组存在；旧 `/editor/intake` 路由降级为兼容入口并导向统一页面。同时在前端增加 session-ready gate、显式错误态与完整的 `managingWorkspaceCache` 失效。

**Tech Stack:** Next.js 16 App Router、React 19、Vitest、FastAPI（只做兼容验证，不作为主改动面）、Supabase Auth、现有 `editorService` / `EditorApi` 缓存层。

---

## 执行原则

- 使用 `@superpowers:test-driven-development`
- 每个行为变化先写失败测试，再写最小实现
- 每个任务单独 commit
- 不触碰当前 worktree 中与本任务无关的未提交后端邮件相关改动

## Task 1: 收口主页面语义，明确 Managing Workspace 是唯一主入口

**Files:**
- Modify: `frontend/src/components/editor/ManagingWorkspacePanel.tsx`
- Modify: `frontend/src/app/(admin)/editor/managing-workspace/page.tsx`
- Modify: `frontend/src/app/(admin)/editor/intake/page.tsx`
- Modify: `frontend/src/components/editor/__tests__/managing-workspace-panel.awaiting-author.test.tsx`
- Modify: `frontend/src/app/(admin)/editor/intake/page.test.tsx`

**Step 1: Write the failing tests**

- 在 `frontend/src/app/(admin)/editor/intake/page.test.tsx` 增加用例，定义旧 Intake 路由不再渲染独立列表，而是明确引导或复用统一工作面。
- 在 `frontend/src/components/editor/__tests__/managing-workspace-panel.awaiting-author.test.tsx` 增加/调整断言，确认：
  - `Managing Workspace` 可以展示 `intake` 分组作为默认工作分组
  - 页面标题/描述表达“统一工作面”而不是“跟踪辅助页”

**Step 2: Run tests to verify they fail**

Run:

```bash
cd frontend && bun run test:run src/app/'(admin)'/editor/intake/page.test.tsx src/components/editor/__tests__/managing-workspace-panel.awaiting-author.test.tsx
```

Expected:

- 至少一条断言失败，显示当前 Intake 页面仍在渲染独立队列表达，或 Managing Workspace 文案仍未体现“唯一主入口”。

**Step 3: Write minimal implementation**

- 让 `ManagingWorkspacePanel` 的标题、副标题、分组顺序明确表达“这是 ME 的统一工作面，`intake` 为默认分组”。
- 调整 `frontend/src/app/(admin)/editor/intake/page.tsx`：
  - 不再维护独立 intake 列表逻辑
  - 改为兼容入口，可直接复用统一工作面并默认聚焦 `intake`，或提供显式跳转/提示
- 尽量把旧页面收成壳，不再让两套列表逻辑继续分叉。

**Step 4: Run tests to verify they pass**

Run:

```bash
cd frontend && bun run test:run src/app/'(admin)'/editor/intake/page.test.tsx src/components/editor/__tests__/managing-workspace-panel.awaiting-author.test.tsx
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add frontend/src/components/editor/ManagingWorkspacePanel.tsx frontend/src/app/'(admin)'/editor/managing-workspace/page.tsx frontend/src/app/'(admin)'/editor/intake/page.tsx frontend/src/components/editor/__tests__/managing-workspace-panel.awaiting-author.test.tsx frontend/src/app/'(admin)'/editor/intake/page.test.tsx
git commit -m "feat(editor): unify me workspace entrypoint"
```

## Task 2: 为统一工作面加 session-ready gate 与显式错误态

**Files:**
- Modify: `frontend/src/components/editor/ManagingWorkspacePanel.tsx`
- Modify: `frontend/src/services/auth.ts`
- Optionally Modify: `frontend/src/components/layout/SiteHeader.tsx`
- Create: `frontend/src/components/editor/__tests__/managing-workspace-panel.error-state.test.tsx`

**Step 1: Write the failing tests**

- 新增 `frontend/src/components/editor/__tests__/managing-workspace-panel.error-state.test.tsx`，至少覆盖：
  - 请求失败时显示错误提示和重试入口，而不是空态
  - 在 session 未准备好前，不发 `editorService.getManagingWorkspace()`
- 如需要，可在 `auth.ts` 层 mock `getSession()` 未完成状态，确保当前实现会失败。

**Step 2: Run tests to verify they fail**

Run:

```bash
cd frontend && bun run test:run src/components/editor/__tests__/managing-workspace-panel.error-state.test.tsx
```

Expected:

- FAIL，原因是当前组件在 `catch` 后仅 `console.error`
- 或 FAIL，原因是组件 mount 即发请求，没有 session gate

**Step 3: Write minimal implementation**

- 在 `ManagingWorkspacePanel` 中引入显式状态：
  - `authReady`
  - `error`
- session 未准备好前只显示“正在验证登录态”或等价格式的 loading，而不是直接请求列表。
- 请求失败时：
  - 若无历史数据：显示错误态 + 重试按钮
  - 若已有历史数据：保留旧数据，并显示轻量错误提示
- 若 `SiteHeader` 的并行 `getSession()` 明显造成重复恢复，可做最小协调，但不要顺手大改整个站点认证架构。

**Step 4: Run tests to verify they pass**

Run:

```bash
cd frontend && bun run test:run src/components/editor/__tests__/managing-workspace-panel.error-state.test.tsx src/components/editor/__tests__/managing-workspace-panel.awaiting-author.test.tsx
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add frontend/src/components/editor/ManagingWorkspacePanel.tsx frontend/src/services/auth.ts frontend/src/components/layout/SiteHeader.tsx frontend/src/components/editor/__tests__/managing-workspace-panel.error-state.test.tsx
git commit -m "fix(editor): harden workspace auth gate and error state"
```

Note:

- 如果最终没有修改 `SiteHeader.tsx`，从 `git add` 中去掉该文件。

## Task 3: 补齐 managing workspace 相关缓存失效

**Files:**
- Modify: `frontend/src/services/editor-api/manuscripts.ts`
- Modify: `frontend/src/tests/services/editor/precheck.api.test.ts`
- Modify: `frontend/src/services/__tests__/editorApi.force-refresh-header.test.ts`

**Step 1: Write the failing tests**

- 在 `frontend/src/tests/services/editor/precheck.api.test.ts` 或相近服务测试中补断言：
  - `assignAE()` 成功后会清空 `managingWorkspaceCache`
  - `submitIntakeRevision()` 成功后会清空 `managingWorkspaceCache`
  - `submitTechnicalCheck()` / `revertTechnicalCheck()` / `submitAcademicCheck()` 成功后也会影响统一工作面时，必须失效该缓存
- 在 `frontend/src/services/__tests__/editorApi.force-refresh-header.test.ts` 保持已有强刷行为不回归。

**Step 2: Run tests to verify they fail**

Run:

```bash
cd frontend && bun run test:run src/tests/services/editor/precheck.api.test.ts src/services/__tests__/editorApi.force-refresh-header.test.ts
```

Expected:

- FAIL，提示相关 mutation 后 `managingWorkspaceCache` 仍未清空

**Step 3: Write minimal implementation**

- 在 `frontend/src/services/editor-api/manuscripts.ts` 中统一调用现有 `invalidateManagingWorkspaceCache()` 或等效清理逻辑。
- 不要重复发明第二套缓存失效函数。
- 确保所有会改变 ME 分组视图的 mutation 都能触发统一工作面刷新。

**Step 4: Run tests to verify they pass**

Run:

```bash
cd frontend && bun run test:run src/tests/services/editor/precheck.api.test.ts src/services/__tests__/editorApi.force-refresh-header.test.ts
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add frontend/src/services/editor-api/manuscripts.ts frontend/src/tests/services/editor/precheck.api.test.ts frontend/src/services/__tests__/editorApi.force-refresh-header.test.ts
git commit -m "fix(editor): invalidate managing workspace cache on mutations"
```

## Task 4: 补统一工作面的交互回归测试

**Files:**
- Modify: `frontend/src/app/(admin)/editor/intake/page.test.tsx`
- Modify: `frontend/src/components/editor/__tests__/managing-workspace-panel.awaiting-author.test.tsx`
- Modify: `frontend/src/components/editor/__tests__/managing-workspace-panel.error-state.test.tsx`
- Optionally Create: `frontend/src/components/editor/__tests__/managing-workspace-panel.intake-entry.test.tsx`

**Step 1: Write the failing tests**

- 增加端到端风格的组件级断言，至少覆盖：
  - 旧 intake 入口可以进入统一工作面
  - `intake` 是默认工作分组
  - 错误态与空态严格区分
  - 搜索/刷新不会破坏现有 `awaiting_author` 分组表现

**Step 2: Run tests to verify they fail**

Run:

```bash
cd frontend && bun run test:run src/app/'(admin)'/editor/intake/page.test.tsx src/components/editor/__tests__/managing-workspace-panel.awaiting-author.test.tsx src/components/editor/__tests__/managing-workspace-panel.error-state.test.tsx
```

Expected:

- 至少一条断言失败，证明新增的统一工作面交互还未完全覆盖

**Step 3: Write minimal implementation**

- 只补实现中为了满足这些回归场景所缺的最小代码
- 避免顺手做视觉重构或额外 IA 调整

**Step 4: Run tests to verify they pass**

Run:

```bash
cd frontend && bun run test:run src/app/'(admin)'/editor/intake/page.test.tsx src/components/editor/__tests__/managing-workspace-panel.awaiting-author.test.tsx src/components/editor/__tests__/managing-workspace-panel.error-state.test.tsx
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add frontend/src/app/'(admin)'/editor/intake/page.test.tsx frontend/src/components/editor/__tests__/managing-workspace-panel.awaiting-author.test.tsx frontend/src/components/editor/__tests__/managing-workspace-panel.error-state.test.tsx frontend/src/components/editor/__tests__/managing-workspace-panel.intake-entry.test.tsx
git commit -m "test(editor): cover unified me workspace flows"
```

Note:

- 如果未创建 `managing-workspace-panel.intake-entry.test.tsx`，从 `git add` 中移除该文件。

## Task 5: 最终整体验证与文案收口

**Files:**
- Modify: `frontend/src/components/editor/ManagingWorkspacePanel.tsx`
- Modify: `frontend/src/app/(admin)/editor/intake/page.tsx`
- Optionally Modify: `docs/plans/2026-03-12-me-workspace-unification-design.md`

**Step 1: Run focused verification before touching wording**

Run:

```bash
cd frontend && bun run test:run src/app/'(admin)'/editor/intake/page.test.tsx src/components/editor/__tests__/managing-workspace-panel.awaiting-author.test.tsx src/components/editor/__tests__/managing-workspace-panel.error-state.test.tsx src/tests/services/editor/precheck.api.test.ts src/services/__tests__/editorApi.force-refresh-header.test.ts
```

Expected:

- 全绿

**Step 2: Apply final copy cleanup**

- 统一把页面文案收成“Managing Workspace 是唯一主工作面”
- 删掉任何暗示双主页面并存的描述

**Step 3: Re-run the same focused verification**

Run:

```bash
cd frontend && bun run test:run src/app/'(admin)'/editor/intake/page.test.tsx src/components/editor/__tests__/managing-workspace-panel.awaiting-author.test.tsx src/components/editor/__tests__/managing-workspace-panel.error-state.test.tsx src/tests/services/editor/precheck.api.test.ts src/services/__tests__/editorApi.force-refresh-header.test.ts
```

Expected:

- 全绿

**Step 4: Commit**

```bash
git add frontend/src/components/editor/ManagingWorkspacePanel.tsx frontend/src/app/'(admin)'/editor/intake/page.tsx
git commit -m "docs(editor): align me workspace single-page copy"
```

## Final Verification

Run:

```bash
cd frontend && bun run test:run src/app/'(admin)'/editor/intake/page.test.tsx src/components/editor/__tests__/managing-workspace-panel.awaiting-author.test.tsx src/components/editor/__tests__/managing-workspace-panel.error-state.test.tsx src/tests/services/editor/precheck.api.test.ts src/services/__tests__/editorApi.force-refresh-header.test.ts
```

Then:

```bash
git status -sb
```

Expected:

- 目标测试全绿
- worktree 仅剩与本任务无关的用户本地改动，不能被误提交

## Notes for Execution

- 当前仓库已有与邮件流程相关的未提交改动；实现本计划时不要改动这些文件，除非用户明确要求。
- 若在执行中发现 `ManagingWorkspacePanel` 与 `Intake Page` 耦合过高，可以新建一个轻量容器组件承接“统一工作面入口”职责，但要先写失败测试再动手。
- 如果 session gate 在单页实现里需要抽成公共 hook，优先做最小抽象，不要顺手全站推广。

## Suggested Commit Sequence

1. `feat(editor): unify me workspace entrypoint`
2. `fix(editor): harden workspace auth gate and error state`
3. `fix(editor): invalidate managing workspace cache on mutations`
4. `test(editor): cover unified me workspace flows`
5. `docs(editor): align me workspace single-page copy`
