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

## 已完成的 v3 设计系统化（第四批增量）
- 第四批高频文件完成语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/components/DecisionPanel.tsx`
  - `frontend/src/app/about/page.tsx`
  - `frontend/src/pages/editor/managing-workspace/page.tsx`
  - `frontend/src/components/cms/CmsPagesPanel.tsx`
  - `frontend/src/app/journals/[slug]/page.tsx`
- 第四批 5 个文件合计减少硬编码色板引用约 `126` 处。

## 已完成的 v3 设计系统化（第五批增量）
- 第五批高频文件完成语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/pages/editor/workspace/page.tsx`
  - `frontend/src/components/editor/production/ProductionWorkspacePanel.tsx`
  - `frontend/src/components/editor/InternalTasksPanel.tsx`
  - `frontend/src/components/AdminDashboard.tsx`
  - `frontend/src/app/contact/page.tsx`
- 第五批 5 个文件合计减少硬编码色板引用约 `115` 处。

## 已完成的 v3 设计系统化（第六批增量）
- 第六批高频文件完成语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/app/admin/journals/page.tsx`
  - `frontend/src/app/(public)/review/invite/page.tsx`
  - `frontend/src/components/editor/ReviewerLibraryList.tsx`
  - `frontend/src/components/editor/FileHubCard.tsx`
  - `frontend/src/app/dashboard/notifications/page.tsx`
- 第六批 5 个文件合计减少硬编码色板引用约 `107` 处。

## 已完成的 v3 设计系统化（第七批增量）
- 第七批高频文件完成语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/app/signup/page.tsx`
  - `frontend/src/app/(reviewer)/reviewer/workspace/[id]/page.tsx`
  - `frontend/src/components/editor/decision/ReviewReportComparison.tsx`
  - `frontend/src/components/editor/decision/DecisionEditor.tsx`
  - `frontend/src/components/editor/ManuscriptTable.tsx`
- 第七批 5 个文件合计减少硬编码色板引用约 `87` 处。

## 已完成的 v3 设计系统化（第八批增量）
- 第八批高频文件完成语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/app/login/page.tsx`
  - `frontend/src/components/editor/production/ProductionTimeline.tsx`
  - `frontend/src/components/editor/ProcessFilterBar.tsx`
  - `frontend/src/app/dashboard/author/manuscripts/[id]/page.tsx`
  - `frontend/src/components/editor/ManuscriptDetailsHeader.tsx`
- 第八批 5 个文件合计减少硬编码色板引用约 `89` 处。

## 已完成的 v3 设计系统化（第九批增量）
- 第九批高频文件完成语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/components/VersionHistory.tsx`
  - `frontend/src/app/proofreading/[id]/page.tsx`
  - `frontend/src/components/home/JournalCarousel.tsx`
  - `frontend/src/components/author/proofreading/ProofreadingForm.tsx`
  - `frontend/src/app/admin/manuscripts/page.tsx`
- 第九批 5 个文件合计减少硬编码色板引用约 `81` 处。

## 已完成的 v3 设计系统化（第十批增量）
- 第十批高频文件完成语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/app/admin/eic-approval/page.tsx`
  - `frontend/src/components/home/HeroSection.tsx`
  - `frontend/src/components/editor/production/ProductionActionPanel.tsx`
  - `frontend/src/components/EditorDashboard.tsx`
  - `frontend/src/app/finance/page.tsx`
- 第十批 5 个文件合计减少硬编码色板引用约 `73` 处。

## 已完成的 v3 设计系统化（第十一批增量）
- 第十一批高频文件完成语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/app/(reviewer)/reviewer/workspace/[id]/action-panel.tsx`
  - `frontend/src/app/(admin)/editor/production/page.tsx`
  - `frontend/src/app/(admin)/editor/production/[id]/page.tsx`
  - `frontend/src/app/(admin)/editor/manuscript/[id]/loading.tsx`
  - `frontend/src/components/notifications/NotificationList.tsx`
- 第十一批 5 个文件合计减少硬编码色板引用约 `61` 处。

## 已完成的 v3 设计系统化（第十二批增量，加速批）
- 第十二批一次性完成 10 个高频文件语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/components/home/LatestArticles.tsx`
  - `frontend/src/components/home/HomeDiscoveryBlocks.tsx`
  - `frontend/src/components/finance/FinanceInvoicesTable.tsx`
  - `frontend/src/components/editor/ProductionStatusCard.tsx`
  - `frontend/src/components/cms/CmsMenuPanel.tsx`
  - `frontend/src/components/editor/QuickPrecheckModal.tsx`
  - `frontend/src/components/editor/AuditLogTimeline.tsx`
  - `frontend/src/components/CoverageDashboard.tsx`
  - `frontend/src/app/topics/page.tsx`
  - `frontend/src/app/submit-revision/[id]/page.tsx`
- 第十二批 10 个文件合计减少硬编码色板引用约 `114` 处。

## 已完成的 v3 设计系统化（第十三批增量，激进批）
- 第十三批一次性完成 15 个高频文件语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/components/editor/InvoiceInfoSection.tsx`
  - `frontend/src/components/RecommendationList.tsx`
  - `frontend/src/app/auth/callback/page.tsx`
  - `frontend/src/app/admin/users/page.tsx`
  - `frontend/src/components/editor/FileSectionGroup.tsx`
  - `frontend/src/components/editor/FileSectionCard.tsx`
  - `frontend/src/components/editor/decision/DecisionWorkspaceLayout.tsx`
  - `frontend/src/app/not-found.tsx`
  - `frontend/src/app/(reviewer)/reviewer/workspace/[id]/pdf-viewer.tsx`
  - `frontend/src/app/(public)/review/invite/decline-form.tsx`
  - `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
  - `frontend/src/app/(admin)/editor/decision/[id]/page.tsx`
  - `frontend/src/components/portal/ArticleList.tsx`
  - `frontend/src/components/notifications/NotificationBell.tsx`
  - `frontend/src/components/editor/ManuscriptHeader.tsx`
- 第十三批 15 个文件合计减少硬编码色板引用约 `108` 处。

## 已完成的 v3 设计系统化（第十四批增量，冲刺批）
- 第十四批一次性完成 12 个高频文件语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/components/editor/BindingOwnerDropdown.tsx`
  - `frontend/src/components/editor/BindingAssistantEditorDropdown.tsx`
  - `frontend/src/components/analytics/ManagementInsights.tsx`
  - `frontend/src/app/submit/page.tsx`
  - `frontend/src/app/(public)/review/invite/accept-form.tsx`
  - `frontend/src/app/(public)/review/error/page.tsx`
  - `frontend/src/app/(admin)/editor/process/page.tsx`
  - `frontend/src/components/ui/sonner.tsx`
  - `frontend/src/components/layout/SiteFooter.tsx`
  - `frontend/src/components/editor/InvoiceInfoPanel.tsx`
  - `frontend/src/components/QualityCheckDialog.tsx`
  - `frontend/src/components/FileUpload.tsx`
- 第十四批 12 个文件合计减少硬编码色板引用约 `68` 处。

## 已完成的 v3 设计系统化（第十五批增量，清尾批）
- 第十五批一次性完成 10 个剩余高频文件语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/components/ErrorBoundary.tsx`
  - `frontend/src/app/journal/[slug]/page.tsx`
  - `frontend/src/app/(reviewer)/layout.tsx`
  - `frontend/src/components/portal/SiteFooter.tsx`
  - `frontend/src/components/portal/HomeBanner.tsx`
  - `frontend/src/components/cms/CmsManagementPanel.tsx`
  - `frontend/src/app/(admin)/editor/doi-tasks/page.tsx`
  - `frontend/src/app/(admin)/editor/analytics/page.tsx`
  - `frontend/src/components/ui/date-time-picker.tsx`
  - `frontend/src/components/settings/AvatarUpload.tsx`
- 第十五批 10 个文件合计减少硬编码色板引用约 `38` 处。

## 已完成的 v3 设计系统化（第十六批增量，清零批）
- 第十六批一次性完成 16 个剩余命中文件语义 token 化（`(bg|text|border)-(slate|blue)-` 全部清零）：
  - `frontend/src/app/(admin)/admin/feedback/page.tsx`
  - `frontend/src/app/(admin)/editor/reviewers/page.tsx`
  - `frontend/src/app/admin/sentry-test/page.tsx`
  - `frontend/src/app/globals.css`
  - `frontend/src/components/AcademicCheckModal.tsx`
  - `frontend/src/components/AssignAEModal.tsx`
  - `frontend/src/components/ErrorMessage.tsx`
  - `frontend/src/components/PDFViewer.tsx`
  - `frontend/src/components/PlagiarismActions.tsx`
  - `frontend/src/components/admin/UserFilters.tsx`
  - `frontend/src/components/cms/TiptapEditor.tsx`
  - `frontend/src/components/editor/ManuscriptsProcessPanel.tsx`
  - `frontend/src/components/editor/TaskStatusBadge.tsx`
  - `frontend/src/components/home/HeroSection.tsx`
  - `frontend/src/components/notifications/NotificationItem.tsx`
  - `frontend/src/components/ui/avatar.tsx`
- 第十六批 16 个文件合计减少硬编码色板引用约 `32` 处，并将 `hard palette` 清零。

## 当前基线（代码扫描）
- `w-[96vw]`: `0`
- `hex colors (#xxxxxx)`: `0`
- `inline style={{...}}`: `0`
- `hard palette (bg/text/border)-(slate|blue)-`: `0`

> 说明：四项核心计数已全部清零，后续以 CI 门禁防止回退。

## 审计脚本
- 新增：`frontend/scripts/tailwind-readiness-audit.sh`
- 运行：`cd frontend && bun run audit:tailwind-readiness`
- 输出：
  - 核心计数（魔法值、hex、inline style、硬编码色板）
  - Top 文件分布（便于分批治理）
- 门禁模式：
  - 通过 `TAILWIND_AUDIT_ENFORCE=1` 启用阈值校验（默认阈值均为 `0`，可用 `TAILWIND_MAX_*` 覆盖）
  - 已接入 `frontend-ci`，默认阻断 `w-[96vw] / hex / inline style / hard palette` 回退

## v4 迁移进度（2026-02-25）
### Phase 1（已完成，兼容模式）
- 依赖升级：
  - `tailwindcss` -> `^4.2.0`
  - 新增 `@tailwindcss/postcss` -> `^4.2.0`
- 构建链升级：
  - `postcss.config.mjs` 改为 `@tailwindcss/postcss` 插件
- 样式入口升级：
  - `src/app/globals.css` 改为 `@import "tailwindcss"`
  - 使用 `@config "../../tailwind.config.mjs"` 保留 v3 配置兼容
  - 新增 `@custom-variant dark (&:where(.dark, .dark *))`
- 配置文件升级：
  - `tailwind.config.ts` -> `tailwind.config.mjs`（移除 TS 类型声明）
  - `components.json` 同步引用 `tailwind.config.mjs`

### Phase 2（已完成，CSS-first）
1. token 下沉到 CSS-first：
  - 将原 `tailwind.config` 的语义颜色、字体、圆角与 accordion 动画迁移到 `globals.css` 的 `@theme`。
2. 动画插件替换：
  - 移除 `tailwindcss-animate` 依赖。
  - 在 `globals.css` 使用 `@utility` + `@keyframes` 提供兼容的 `animate-in/out`、`fade/zoom/slide` 动画原子类。
3. 兼容层移除：
  - 删除 `@config "../../tailwind.config.mjs"`。
  - 删除 `tailwind.config.mjs`，`components.json` 的 `tailwind.config` 置空（v4 CSS-first）。
4. 验证结果：
  - `bun run lint`、`bun run test:run`、`bun run build`、`TAILWIND_AUDIT_ENFORCE=1 bun run audit:tailwind-readiness` 全通过。

### Phase 3（下一步）
1. 清理并标准化遗留 magic width token（当前 `w-[...] = 42`）。
2. 把现有自定义动画 utility 拆分为更小的语义层，减少组件层直接拼接复杂动画类。
3. 根据真实页面性能数据评估是否继续做动画降载（减少首屏动画数量/时长）。
