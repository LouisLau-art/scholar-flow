# Tailwind 设计系统审查问题清单（tailwind-design-system）

审查时间：2026-02-26  
审查范围：`frontend/src/app`、`frontend/src/components`、`frontend/src/pages`、Tailwind/PostCSS 配置

## 结论
项目已完成 Tailwind v4 基础迁移（`@import "tailwindcss"`、`@theme`、`@custom-variant dark` 已到位），但仍未完全符合设计系统最佳实践。主要短板是“语义 token 渗透不完整”，业务层存在较多硬编码色板类名。

## 问题列表（按严重度）

1. 高：语义颜色 token 渗透不完整，业务层仍大量硬编码色板类名
- 现状：扫描到 `331` 处 `bg/text/border-(red|green|amber|violet|purple|gray|slate|yellow|emerald|rose)-*`。
- 风险：主题统一、品牌换肤、状态色一致性维护成本高；跨页面视觉口径容易漂移。
- 典型位置：
`frontend/src/components/EditorPipeline.tsx:308`
`frontend/src/components/DecisionPanel.tsx:501`
`frontend/src/components/AssignAEModal.tsx:158`
`frontend/src/lib/statusStyles.ts:58`
`frontend/src/components/finance/FinanceInvoicesTable.tsx:17`
`frontend/src/components/analytics/ManagementInsights.tsx:38`

2. 中高：状态色规则分散在多个业务模块，缺少统一语义映射层
- 现状：状态 badge/告警色在多个文件各自硬编码，不同模块对同一状态的色阶可能不同。
- 风险：同义状态出现不同颜色，影响可用性和认知一致性；后续改色需要全局搜索替换。
- 典型位置：
`frontend/src/lib/statusStyles.ts:53`
`frontend/src/components/editor/TaskStatusBadge.tsx:12`
`frontend/src/components/ErrorMessage.tsx:7`
`frontend/src/components/finance/FinanceInvoicesTable.tsx:17`

3. 中：PostCSS 配置未显式包含 `autoprefixer`
- 现状：当前仅启用 `@tailwindcss/postcss`。
- 风险：在部分浏览器特性和自定义 CSS 规则上可能缺少前缀兼容保障（尤其是非 Tailwind 生成规则）。
- 位置：
`frontend/postcss.config.mjs:3`

4. 中：当前 Tailwind 审计脚本对“硬编码色板”检测口径偏窄
- 现状：脚本仅统计 `slate|blue`，无法覆盖 `amber|rose|emerald|violet|gray` 等常见硬编码色。
- 风险：审计报告可能出现“0 问题”的假象，难以及时发现 token 外泄回归。
- 位置：
`frontend/scripts/tailwind-readiness-audit.sh:23`
`frontend/scripts/tailwind-readiness-audit.sh:46`

5. 中：CVA 组件化覆盖面仍偏小
- 现状：`cva` 仅用于 `Button` 与 `Badge`，大量业务组件仍以长 `className` 直接拼接。
- 风险：可维护性下降，变体扩展和样式复用成本高。
- 位置：
`frontend/src/components/ui/button.tsx:9`
`frontend/src/components/ui/badge.tsx:8`

## 本轮已确认的“非问题”项
- `w-[96vw]`：0
- `hex colors`：0
- `inline style={{...}}`：0
- `magic width tokens`：0
- `legacy animate-in/out`：0

## 建议修复顺序
1. 先收敛状态色：建立统一语义 token 映射（success/warning/danger/info 等），优先替换 `statusStyles`、`TaskStatusBadge`、`EditorPipeline`、`DecisionPanel`。
2. 扩展审计脚本：把硬编码色检测从 `slate|blue` 扩展到完整状态色集合，并纳入 CI gate。
3. 补齐 `autoprefixer`，避免兼容性隐患。
4. 分批把高复用业务组件提炼为 CVA 变体组件，减少页面级长 className。

---

# shadcn/ui 审查问题清单（追加，shadcn-ui）

审查时间：2026-02-26  
审查范围：`frontend/src`（组件实现与页面表单/弹窗）

## 结论
shadcn 基础底座是合格的（`components.json`、`ThemeProvider`、`Button asChild`、`Dialog` 基础组件都在），但业务层仍有较多“绕开 shadcn 组件体系”的实现，尚未达到最佳实践。

## 已符合项（本轮确认）
- 已有 shadcn 配置：`frontend/components.json`
- `Button` 已支持 `asChild`（Slot 模式）：`frontend/src/components/ui/button.tsx:38`
- 根布局已接入 `ThemeProvider` + `suppressHydrationWarning`：`frontend/src/app/layout.tsx:111`
- Dialog 基础封装完整（Overlay/Content/Close/Title/Description）：`frontend/src/components/ui/dialog.tsx:9`

## 问题列表（按严重度）

1. 高：仍存在手写弹窗，未使用 shadcn Dialog 语义与焦点管理
- 现状：`AcademicCheckModal` 仍使用 `fixed inset-0` 手写遮罩层 + 原生表单控件。
- 风险：可访问性与键盘交互一致性弱于 Radix Dialog（焦点陷阱、语义、Esc 关闭行为可维护性差）。
- 位置：
`frontend/src/components/AcademicCheckModal.tsx:35`
`frontend/src/components/AcademicCheckModal.tsx:41`
`frontend/src/components/AcademicCheckModal.tsx:76`

2. 中高：关键流程仍大量使用原生 `<input>/<textarea>/<button>`，绕开 shadcn Input/Textarea/Button
- 现状：静态扫描命中 `126` 处原生表单/按钮标签。
- 风险：样式和交互难统一，状态/禁用/focus 规则在各页重复实现，后续维护成本高。
- 典型位置：
`frontend/src/app/login/page.tsx:63`
`frontend/src/app/login/page.tsx:94`
`frontend/src/app/signup/page.tsx:64`
`frontend/src/app/signup/page.tsx:94`
`frontend/src/components/ReviewerAssignModal.tsx:591`
`frontend/src/components/ReviewerAssignModal.tsx:692`
`frontend/src/components/ReviewerDashboard.tsx:246`

3. 中：多个 Dialog 显式隐藏默认关闭按钮，偏离 shadcn 默认可访问模式
- 现状：使用 `[&>button]:hidden` 隐藏 `DialogPrimitive.Close`。
- 风险：关闭入口一致性下降；若业务按钮未覆盖所有场景，会影响键盘/读屏可用性。
- 位置：
`frontend/src/components/ReviewerDashboard.tsx:155`
`frontend/src/components/ReviewerDashboard.tsx:436`
`frontend/src/components/ReviewerAssignModal.tsx:532`

4. 中：表单标签关联不完整（Label 与控件的 `htmlFor/id` 绑定缺失）
- 现状：部分评分控件使用 `<Label>` 但未与 `input` 建立显式关联。
- 风险：读屏与无障碍语义不完整，表单可用性下降。
- 位置：
`frontend/src/components/ReviewerDashboard.tsx:201`
`frontend/src/components/ReviewerDashboard.tsx:204`
`frontend/src/components/ReviewerDashboard.tsx:216`
`frontend/src/components/ReviewerDashboard.tsx:219`

5. 中：业务表单未采用 shadcn 推荐的 `Form`（RHF + Zod）统一模式
- 现状：登录/注册及若干编辑表单采用本地 state + 手写验证；`ui/form` 体系未进入主链路。
- 风险：校验逻辑分散，错误展示/可访问性/提交态一致性难保证。
- 典型位置：
`frontend/src/app/login/page.tsx:58`
`frontend/src/app/signup/page.tsx:59`
`frontend/src/components/AcademicCheckModal.tsx:19`

## 建议优先级
1. 先把 `AcademicCheckModal` 改造为 shadcn `Dialog + RadioGroup + Textarea + Button`（最高优先级）。
2. 统一关键认证与审稿弹窗表单到 `Input/Textarea/Button`，减少原生控件直写。
3. 清理 `[&>button]:hidden`，改为保留默认关闭按钮或显式 `DialogClose asChild`。
4. 对高频表单分批引入 `Form`（RHF + Zod）以统一校验与错误反馈。

---

# Web Interface Guidelines 审查问题清单（追加，web-design-guidelines）

审查时间：2026-02-26  
规则来源：`https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`

## 结论
当前前端“基础可用”，但在可访问性（表单标签、键盘可达性、语义交互）和一致性（文案、省略号、日期本地化）上仍有明显偏差，尚未完全符合 web-design-guidelines 最佳实践。

## 发现（按严重度，`file:line`）

1. 高 | `frontend/src/components/AcademicCheckModal.tsx:35`
- 问题：手写遮罩弹窗（`fixed inset-0`）而非语义化 `dialog`，缺失标准焦点管理与键盘交互保障。
- 建议：改为统一 `Dialog` 组件（含 `DialogTitle`/`DialogDescription`/可达关闭行为）。

2. 高 | `frontend/src/components/home/HeroSection.tsx:65`
- 问题：搜索输入仅靠 placeholder，无显式 `<label>` 或 `aria-label`。
- 建议：增加可见或 `sr-only` label，确保读屏与表单语义完整。

3. 高 | `frontend/src/components/admin/UserFilters.tsx:20`
- 问题：管理员搜索框无关联 label（placeholder-only input）。
- 建议：补 `label` + `htmlFor/id`（或 `aria-label`）。

4. 高 | `frontend/src/components/layout/SiteHeader.tsx:210`
- 问题：站点搜索弹窗内输入框无 label，仅 placeholder。
- 建议：增加 `Label`（可 `sr-only`）并绑定 input id。

5. 中高 | `frontend/src/app/page.tsx:371`
- 问题：首页 Newsletter 三个输入框无 label（`Name/Last name/Email` 仅 placeholder）。
- 建议：补表单 label；必要时增加 `name` 与 `autoComplete`。

6. 中高 | `frontend/src/components/layout/SiteHeader.tsx:237`
- 问题：Mega Menu 主要依赖 `onMouseEnter/onMouseLeave` 打开，键盘用户缺少等价触发路径。
- 建议：改为可聚焦触发器（button）+ `aria-expanded` + 键盘事件支持。

7. 中高 | `frontend/src/components/layout/SiteHeader.tsx:247`
- 问题：菜单项用 `<li class="cursor-pointer">` 伪交互，不是 link/button，键盘不可达。
- 建议：改为 `<Link>` 或 `<button>`，保持语义和可访问性。

8. 中 | `frontend/src/components/portal/SiteFooter.tsx:48`
- 问题：Footer 资源项是 `<li class="cursor-pointer">`，没有实际交互元素。
- 建议：改为可导航 `<Link>`，或明确移除伪点击样式。

9. 中 | `frontend/src/components/layout/SiteHeader.tsx:271`
- 问题：存在占位链接 `href="#"`，会导致无意义导航（页面回顶）。
- 建议：改为真实路径；若未实现，使用禁用态按钮并给出说明。

10. 中 | `frontend/src/components/layout/SiteHeader.tsx:211`
- 问题：搜索框使用 `autoFocus`，会在打开时强制焦点跳转。
- 建议：仅在明确用户触发且不打断上下文时使用，或移除为手动聚焦策略。

11. 中 | `frontend/src/components/finance/FinanceInvoicesTable.tsx:35`
- 问题：加载文案使用 `...`（三点），不符合统一排版建议（应使用单字符省略号 `…`）。
- 建议：统一替换为 `…`；同类文案一并清理。

12. 中 | `frontend/src/app/(admin)/admin/feedback/_components/FeedbackTable.tsx:36`
- 问题：同样使用 `Loading...` 三点省略写法。
- 建议：统一为 `Loading…`。

13. 中 | `frontend/src/components/editor/ManuscriptTable.tsx:37`
- 问题：使用固定模板 `format(d, 'yyyy-MM-dd HH:mm')`，日期展示非 locale-aware。
- 建议：改用 `Intl.DateTimeFormat`（或统一封装 `date-display` 工具）。

14. 中 | `frontend/src/components/editor/InternalNotebook.tsx:222`
- 问题：使用固定模板 `format(..., 'MMM d, HH:mm')`，跨地区显示不一致。
- 建议：统一走 locale-aware 日期格式工具。

15. 中 | `frontend/src/components/editor/AuditLogTimeline.tsx:416`
- 问题：时间戳使用硬编码格式 `yyyy-MM-dd HH:mm`。
- 建议：统一改为 `Intl.DateTimeFormat`/共享日期格式函数。

16. 低 | `frontend/src/components/home/HeroSection.tsx:70`
- 问题：输入框 `focus:ring-0 focus:outline-none`，焦点可见性不足（键盘导航不友好）。
- 建议：保留明确 focus ring（至少 `focus-visible:ring-*`）。

---

# UI Guideline Remediation 状态更新（2026-02-26）

## 已完成

1. `AcademicCheckModal` 已改为 shadcn `Dialog` 语义实现（含可访问关闭路径）。
2. Header/Hero/Admin 筛选/Newsletter/审稿页关键输入已补齐显式 label 与 id 绑定。
3. Header Mega Menu / Footer / Home Discovery 已清理伪交互，全部改为语义化 Link/Button。
4. 全站已清理 `href="#"` 占位导航（本轮覆盖范围内）。
5. `ReviewerDashboard` 与 `ReviewerAssignModal` 已移除 `[&>button]:hidden` 关闭按钮 hack。
6. 文案省略号统一：`Loading… / Submitting… / Confirming… / Removing…`。
7. 目标组件时间展示统一为 `date-display`（locale-aware）：
   - `ManuscriptTable`
   - `InternalNotebook`
   - `AuditLogTimeline`
   - `FinanceInvoicesTable`
   - `FeedbackTable`
8. 已新增静态审计脚本：`frontend/scripts/ui-guidelines-audit.sh`，并接入 `bun run audit:ui-guidelines`。

## 验证结果

- `cd frontend && bun run lint` ✅
- `cd frontend && bun run audit:ui-guidelines` ✅
- `./scripts/test-fast.sh` ✅

## 剩余观察项（非阻断）

1. `test-fast` 中仍有历史 `act(...)` 警告（测试警告，不阻断通过）。

---

# problem.md 问题处理结果（2026-02-26 更新）

## 已完成（本轮已落地）

1. Tailwind 语义 token 收敛已推进：
- 硬编码色板（原清单口径）`185 -> 74`。
- 关键文件已改造：`statusStyles`、`EditorPipeline`、`DecisionPanel`、`SubmissionForm`、`ArticleClient`、`detail-sections`、`AssignAEModal`、`ResetPasswordDialog`、`ReviewerAssignModal`。

2. 状态色映射层已统一到语义类：
- `frontend/src/lib/statusStyles.ts`
- `frontend/src/components/editor/TaskStatusBadge.tsx`
- `frontend/src/components/finance/FinanceInvoicesTable.tsx`

3. PostCSS 已显式启用 `autoprefixer`：
- `frontend/postcss.config.mjs`

4. Tailwind 审计脚本检测口径已扩展：
- 覆盖目录：`src/app`、`src/components`、`src/lib`、`src/pages`
- 色板规则由窄口径扩展为完整集合（含 `amber/rose/emerald/violet/...`）
- 文件：`frontend/scripts/tailwind-readiness-audit.sh`

5. CVA 覆盖面已扩展：
- `cva(` 使用点：`2 -> 6`
- 新增并落地：`status-pill`、`inline-notice`

6. shadcn 表单体系收敛推进：
- 原生 `<input>/<textarea>/<button>` 计数：`111 -> 58`
- 关键链路完成替换：登录/注册、投稿表单、审稿弹窗、审稿仪表盘、DecisionEditor、SiteHeader、ProcessFilterBar、ArticleClient

## 已知未清零（保留项 + 后续口径）

1. 按“完整色板审计口径”统计，当前 hard palette 仍为 `155`（非阻断）：
- 这属于检测口径扩大后的新基线，不等同于旧口径回退。
- 主要集中在 `AuditLogTimeline`、`DashboardPageClient`、`UserTable`、`submit-revision`、`review assignment page` 等。
- 建议后续继续按文件批次清理。

2. 前端测试仍有 `act(...)` warnings（非阻断）：
- `./scripts/test-fast.sh` 全绿通过。
- warnings 主要来自测试代码对异步状态更新的包裹方式，可后续专项清理。
