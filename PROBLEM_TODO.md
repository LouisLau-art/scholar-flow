# `problem.md` 整改待办清单（持续打钩版）

更新时间：2026-02-26
负责人：Codex + 你

## 使用规则

- 每完成一批，先跑对应验证命令，再打勾。
- 只有“代码改动 + 验证通过”才允许打勾。
- 本文件作为唯一执行清单，直到全部清零。

## 当前基线（2026-02-26）

- 硬编码色板类名计数：`185`
- `cva(` 使用点：`2`
- 原生 `<input>/<textarea>/<button>` 计数：`111`
- Dialog 关闭按钮隐藏 hack（`[&>button]:hidden`）：`1`
- `SiteHeader` `autoFocus`：`1`
- `postcss.config.mjs` 中 `autoprefixer`：`未启用`

---

## Batch 0：已完成项（已打钩）

- [x] 清理 `href="#"` 占位导航（本轮范围内）
- [x] 清理伪交互 `cursor-pointer`（本轮范围内）
- [x] 关键路径 label/id 绑定补齐（登录/注册/搜索/审稿）
- [x] 目标组件时间展示统一到 `date-display`
- [x] 省略号统一为 `…`（本轮抽样范围）
- [x] `bun run lint` / `bun run audit:ui-guidelines` / `./scripts/test-fast.sh` 通过

---

## Batch 1：快速阻断项（先清零）

- [x] B1-1 去掉 `ReviewerDashboard` 的 `[&>button]:hidden`
  - 文件：`frontend/src/components/ReviewerDashboard.tsx`
- [x] B1-2 去掉 `SiteHeader` 搜索框 `autoFocus`（改为可控聚焦策略）
  - 文件：`frontend/src/components/layout/SiteHeader.tsx`
- [x] B1-3 在 PostCSS 显式启用 `autoprefixer`
  - 文件：`frontend/postcss.config.mjs`
- [x] B1-4 验证通过并记录
  - 命令：`cd frontend && bun run lint && bun run audit:ui-guidelines`

退出标准：
- hack=0，`autoFocus`=0，`autoprefixer` 已启用。

Batch 1 结果快照：
- Dialog 关闭按钮隐藏 hack：`0`
- `SiteHeader` `autoFocus`：`0`
- `autoprefixer`：`已启用`

---

## Batch 2：Tailwind token 化收敛

- [x] B2-1 统一状态色映射层（success/warning/danger/info）并在高频组件落地
  - 目标文件：
    - `frontend/src/lib/statusStyles.ts`
    - `frontend/src/components/finance/FinanceInvoicesTable.tsx`
    - `frontend/src/components/editor/TaskStatusBadge.tsx`
    - `frontend/src/components/EditorPipeline.tsx`
    - `frontend/src/components/DecisionPanel.tsx`
- [x] B2-2 第一轮将硬编码色板从 `185` 降到 `<=120`
- [x] B2-3 第二轮将硬编码色板从 `<=120` 降到 `<=80`
- [x] B2-4 审计脚本保持可检测回归
  - 文件：`frontend/scripts/tailwind-readiness-audit.sh`

退出标准：
- 硬编码色板计数 `<=80`。

Batch 2 结果快照：
- 硬编码色板计数（当前基线命令口径）：`74`
- Tailwind 审计脚本：已扩展为完整色板检测，并纳入 `src/lib`
- `cd frontend && bun run lint`：通过
- `cd frontend && bun run audit:ui-guidelines`：通过
- `cd frontend && bun run audit:tailwind-readiness`：通过（审计信息可见）

---

## Batch 3：CVA 组件化扩展

- [x] B3-1 新增至少 2 个高复用 CVA 组件（如 `TaskStatusBadge`、`Alert/Message`）
- [x] B3-2 页面改用新 CVA 组件，减少长 `className` 拼接
- [x] B3-3 `cva(` 使用点从 `2` 提升到 `>=6`

退出标准：
- `rg -n "\\bcva\\(" frontend/src | wc -l` 结果 `>=6`。

Batch 3 结果快照：
- 新增组件：`frontend/src/components/ui/status-pill.tsx`、`frontend/src/components/ui/inline-notice.tsx`
- 业务接入：`frontend/src/components/EditorPipeline.tsx`、`frontend/src/components/SubmissionForm.tsx`
- 现有组件 CVA 化：`frontend/src/components/editor/TaskStatusBadge.tsx`、`frontend/src/components/finance/FinanceInvoicesTable.tsx`
- `cva(` 使用点：`6`

---

## Batch 4：shadcn 表单体系收敛

- [x] B4-1 关键链路继续替换原生控件为 `Input/Textarea/Button`（或 `Form + RHF + Zod`）
  - 首批目标：
    - `frontend/src/app/login/page.tsx`
    - `frontend/src/app/signup/page.tsx`
    - `frontend/src/components/ReviewerDashboard.tsx`
    - `frontend/src/components/ReviewerAssignModal.tsx`
- [x] B4-2 原生表单控件计数从 `111` 降到 `<=80`
- [x] B4-3 原生表单控件计数从 `<=80` 降到 `<=60`

退出标准：
- 原生 `<input>/<textarea>/<button>` 计数 `<=60`。

Batch 4 结果快照：
- 原生表单控件计数：`58`
- 重点改造文件：
  - `frontend/src/app/login/page.tsx`
  - `frontend/src/app/signup/page.tsx`
  - `frontend/src/components/SubmissionForm.tsx`
  - `frontend/src/components/ReviewerAssignModal.tsx`
  - `frontend/src/components/ReviewerDashboard.tsx`
  - `frontend/src/components/editor/decision/DecisionEditor.tsx`
  - `frontend/src/components/layout/SiteHeader.tsx`
  - `frontend/src/components/editor/ProcessFilterBar.tsx`
  - `frontend/src/app/articles/[id]/ArticleClient.tsx`

---

## Batch 5：收口与关闭

- [x] B5-1 全量执行并通过：
  - `cd frontend && bun run lint`
  - `cd frontend && bun run audit:ui-guidelines`
  - `cd /root/scholar-flow && ./scripts/test-fast.sh`
- [x] B5-2 更新 `problem.md`：未完成项转“已完成/遗留原因”
- [x] B5-3 本清单全部勾满

Batch 5 结果快照：
- `bun run lint`：通过
- `bun run audit:ui-guidelines`：通过
- `./scripts/test-fast.sh`：通过（存在历史 `act(...)` warnings，不阻断）
- `problem.md`：已补充“问题处理结果（2026-02-26 更新）”章节

---

## 基线命令（每批次完成后重跑）

```bash
# 硬编码色板计数
cd /root/scholar-flow
rg -n "bg-(red|green|amber|violet|purple|gray|slate|yellow|emerald|rose)-|text-(red|green|amber|violet|purple|gray|slate|yellow|emerald|rose)-|border-(red|green|amber|violet|purple|gray|slate|yellow|emerald|rose)-" frontend/src/app frontend/src/components frontend/src/lib frontend/src/pages | wc -l

# CVA 使用点
rg -n "\bcva\(" frontend/src | wc -l

# 原生表单控件计数
rg -n "<input|<textarea|<button" frontend/src/app frontend/src/components | wc -l
```
