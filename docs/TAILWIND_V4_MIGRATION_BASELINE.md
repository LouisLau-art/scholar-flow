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
- `hex colors (#xxxxxx)`: `5`
- `inline style={{...}}`: `4`
- `hard palette (bg/text/border)-(slate|blue)-`: `0`

> 说明：`hard palette` 已清零；后续重点转向 `hex colors` 与 `inline style` 的收敛。

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
