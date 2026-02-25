# Tailwind v4 Migration Baseline (2026-02-25)

## 目标
- 为 Tailwind v4 迁移建立可量化基线，避免一次性大改导致回归难定位。
- 先持续推进 v3 设计系统化，再在独立阶段切换 v4。

## 已完成的 v3 设计系统化（本轮）
- 移除所有 `w-[96vw]`，统一为 `sf-page-container` 容器类。
- 新增全局页面基类：
  - `sf-page-shell`
  - `sf-page-container`
- 首页 `src/app/page.tsx` 收敛：
  - 十六进制颜色替换为语义色阶（blue/slate）。
  - 多处 `style={{ fontFamily: ... }}` 改为 `next/font` class。
  - 背景图保留 `backgroundImage`，将 `cover/center` 下沉到 class。

## 已完成的 v3 设计系统化（本次增量）
- Top 5 高频文件完成语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/app/(admin)/editor/manuscript/[id]/detail-sections.tsx`
  - `frontend/src/components/EditorPipeline.tsx`
  - `frontend/src/app/articles/[id]/ArticleClient.tsx`
  - `frontend/src/components/ReviewerAssignModal.tsx`
  - `frontend/src/components/layout/SiteHeader.tsx`
- 以上 5 个文件合计减少硬编码色板引用约 `232` 处。

## 已完成的 v3 设计系统化（第二批增量）
- 第二批高频文件完成语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/pages/editor/academic/page.tsx`
  - `frontend/src/app/dashboard/page.tsx`
  - `frontend/src/pages/editor/intake/page.tsx`
  - `frontend/src/components/ReviewerDashboard.tsx`
  - `frontend/src/app/search/page.tsx`
- 第二批 5 个文件合计减少硬编码色板引用约 `193` 处。

## 已完成的 v3 设计系统化（第三批增量）
- 第三批高频文件完成语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/app/review/[token]/page.tsx`
  - `frontend/src/app/(public)/review/assignment/[assignmentId]/page.tsx`
  - `frontend/src/components/SubmissionForm.tsx`
  - `frontend/src/components/editor/InternalNotebook.tsx`
  - `frontend/src/app/page.tsx`
- 第三批 5 个文件合计减少硬编码色板引用约 `189` 处。

## 当前基线（代码扫描）
- `w-[96vw]`: `0`
- `hex colors (#xxxxxx)`: `5`
- `inline style={{...}}`: `4`
- `hard palette (bg/text/border)-(slate|blue)-`: `1099`

> 说明：`hard palette` 仍高，后续按页面域逐步替换为语义 token（`bg-background`/`text-foreground`/`border-border` 等）。

## 审计脚本
- 新增：`frontend/scripts/tailwind-readiness-audit.sh`
- 运行：`cd frontend && bun run audit:tailwind-readiness`
- 输出：
  - 核心计数（魔法值、hex、inline style、硬编码色板）
  - Top 文件分布（便于分批治理）

## v4 迁移策略（独立阶段）
1. 先做 v3 token 渗透（按页面域拆批次，不跨域混改）。
2. 为每批变更保留可比对基线（脚本 + CI build）。
3. 单独开 v4 迁移批次：
   - CSS-first 配置落地（`@theme`）
   - 清理/替换 v3 旧配置
   - 全量回归与性能对比
4. v4 上线后保留 1 个迭代窗口观察回归，再移除兼容层。
