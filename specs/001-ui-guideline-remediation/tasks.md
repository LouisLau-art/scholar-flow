# Tasks: UI Guideline Remediation

**Input**: Design documents from `/specs/001-ui-guideline-remediation/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-regression-api.openapi.yaml, quickstart.md

**Tests**: 本特性包含自动化补偿测试（auth pages a11y）+ 现有 lint/回归脚本 + 关键路径人工验收。  
**Organization**: 任务按用户故事分组，确保每个故事可独立实施与验收。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: 归属用户故事（US1/US2/US3）
- 每条任务均包含明确文件路径

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 建立整改追踪与自动审计基础

- [X] T001 新建整改映射文档并登记 `problem.md` 问题到故事映射 `specs/001-ui-guideline-remediation/artifacts/finding-mapping.md`
- [X] T002 [P] 新建 UI 规范静态审计脚本 `frontend/scripts/ui-guidelines-audit.sh`
- [X] T003 [P] 在 `frontend/package.json` 增加 `audit:ui-guidelines` 脚本并在 `specs/001-ui-guideline-remediation/quickstart.md` 记录用法

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 建立全故事共享的文案、时间与配置基座

**⚠️ CRITICAL**: 本阶段完成前不进入用户故事实现

- [X] T004 新建统一文案常量工具 `frontend/src/lib/ui-copy.ts`（含省略号规范）
- [X] T005 [P] 补齐并标准化时间展示工具导出 `frontend/src/lib/date-display.ts`
- [X] T006 [P] 扩展站点链接配置（资源与主题入口）`frontend/src/config/site-config.ts`
- [X] T007 [P] 规范 `Dialog` 关闭能力用法并避免样式 hack 依赖 `frontend/src/components/ui/dialog.tsx`
- [X] T008 新建回归核对清单 `specs/001-ui-guideline-remediation/artifacts/regression-checklist.md`

**Checkpoint**: 共享基础完成，可进入用户故事阶段

---

## Phase 3: User Story 1 - 可访问表单与弹窗闭环 (Priority: P1) 🎯 MVP

**Goal**: 关键表单具备明确可访问标签，关键弹窗具备可预测关闭与焦点闭环。  
**Independent Test**: 键盘-only + 读屏器完成登录、注册、搜索、审稿提交、管理员筛选流程。

### Implementation for User Story 1

- [X] T009 [US1] 将手写弹窗重构为统一可访问 Dialog 结构 `frontend/src/components/AcademicCheckModal.tsx`
- [X] T010 [P] [US1] 为 Hero 搜索输入补齐可访问标签与 id 绑定 `frontend/src/components/home/HeroSection.tsx`
- [X] T011 [P] [US1] 将管理员筛选输入改为带标签输入并统一 Input 组件 `frontend/src/components/admin/UserFilters.tsx`
- [X] T012 [US1] 为站点搜索弹窗输入补齐标签与焦点可见行为 `frontend/src/components/layout/SiteHeader.tsx`
- [X] T013 [US1] 为首页 Newsletter 三个字段补齐 label/name/autocomplete `frontend/src/app/page.tsx`
- [X] T014 [P] [US1] 将审稿页提交表单控件统一为可访问输入组件 `frontend/src/app/review/[token]/page.tsx`
- [X] T015 [P] [US1] 将 Magic 审稿页提交表单控件统一为可访问输入组件 `frontend/src/app/(public)/review/assignment/[assignmentId]/page.tsx`
- [X] T016 [US1] 清理弹窗关闭按钮隐藏 hack 并保留可访问关闭路径 `frontend/src/components/ReviewerDashboard.tsx`
- [X] T017 [US1] 清理弹窗关闭按钮隐藏 hack 并保留可访问关闭路径 `frontend/src/components/ReviewerAssignModal.tsx`
- [X] T018 [US1] 补齐图标型按钮可访问名称并核对 focus-visible `frontend/src/components/layout/SiteHeader.tsx`
- [X] T019 [US1] 在验收文档补充 US1 键盘/读屏器闭环步骤 `specs/001-ui-guideline-remediation/quickstart.md`

**Checkpoint**: US1 可独立交付（MVP）

---

## Phase 4: User Story 2 - 语义化交互与键盘可达导航 (Priority: P2)

**Goal**: 清理伪交互项，确保导航/入口全部语义化且键盘可达。  
**Independent Test**: 全站关键导航区域（Header/Mega Menu/Footer/主题卡片）可通过 Tab 完成遍历与触发。

### Implementation for User Story 2

- [X] T020 [US2] 将 Mega Menu 触发机制升级为键盘可达语义触发器 `frontend/src/components/layout/SiteHeader.tsx`
- [X] T021 [US2] 将 Mega Menu 中 `cursor-pointer` 列表项改为语义化可交互元素 `frontend/src/components/layout/SiteHeader.tsx`
- [X] T022 [US2] 移除占位 `href="#"` 并替换为真实路径或禁用态动作 `frontend/src/components/layout/SiteHeader.tsx`
- [X] T023 [P] [US2] 将 Footer 资源伪交互项改为真实链接 `frontend/src/components/portal/SiteFooter.tsx`
- [X] T024 [P] [US2] 将主题卡片点击行为改为语义化 Link/Button `frontend/src/components/home/HomeDiscoveryBlocks.tsx`
- [X] T025 [P] [US2] 将 Hero Trending 伪点击文本改为语义交互元素 `frontend/src/components/home/HeroSection.tsx`
- [X] T026 [US2] 调整审计脚本规则以覆盖伪交互清零校验 `frontend/scripts/ui-guidelines-audit.sh`
- [X] T027 [US2] 记录 US2 独立验收结果（键盘遍历）`specs/001-ui-guideline-remediation/artifacts/regression-checklist.md`

**Checkpoint**: US1 + US2 可独立运行，且导航语义合规

---

## Phase 5: User Story 3 - 文案与时间展示一致性 (Priority: P3)

**Goal**: 统一省略号文案与日期时间展示策略。  
**Independent Test**: 抽样页面中加载文案统一为 `…`，时间展示统一走 locale-aware 工具。

### Implementation for User Story 3

- [X] T028 [US3] 修复账单表格加载文案省略号规范 `frontend/src/components/finance/FinanceInvoicesTable.tsx`
- [X] T029 [US3] 修复反馈表加载文案省略号规范 `frontend/src/app/(admin)/admin/feedback/_components/FeedbackTable.tsx`
- [X] T030 [P] [US3] 替换稿件表固定时间格式为统一工具 `frontend/src/components/editor/ManuscriptTable.tsx`
- [X] T031 [P] [US3] 替换内部笔记固定时间格式为统一工具 `frontend/src/components/editor/InternalNotebook.tsx`
- [X] T032 [P] [US3] 替换审计时间线固定时间格式为统一工具 `frontend/src/components/editor/AuditLogTimeline.tsx`
- [X] T033 [US3] 对用户可见加载文案做抽样清理并对齐 `frontend/src/components/uat/FeedbackWidget.tsx`、`frontend/src/components/editor/ReviewerLibraryList.tsx`、`frontend/src/app/(reviewer)/reviewer/workspace/[id]/action-panel.tsx`、`frontend/src/app/(admin)/editor/production/page.tsx`、`frontend/src/app/(admin)/editor/intake/page.tsx`、`frontend/src/app/(admin)/editor/academic/page.tsx`
- [X] T034 [US3] 更新一致性验收步骤（文案 + 时间）`specs/001-ui-guideline-remediation/quickstart.md`

**Checkpoint**: 三个用户故事全部可独立验收

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 收口验证、结果记录与问题闭环

- [X] T035 [P] 运行前端静态检查并记录结果 `frontend` + `specs/001-ui-guideline-remediation/artifacts/regression-checklist.md`
- [X] T036 [P] 运行 UI 规范审计并记录差异 `frontend/scripts/ui-guidelines-audit.sh` + `specs/001-ui-guideline-remediation/artifacts/finding-mapping.md`
- [X] T037 执行关键路径人工回归并记录证据 `specs/001-ui-guideline-remediation/artifacts/regression-checklist.md`
- [X] T038 更新问题台账状态与遗留项 `problem.md`
- [X] T039 运行分层快速回归并记录结果 `scripts/test-fast.sh` + `specs/001-ui-guideline-remediation/artifacts/regression-checklist.md`

---

## Phase 7: Analyze Remediation (Post-implement Consistency Fixes)

**Purpose**: 补齐 `speckit.analyze` 发现的 Critical/High 文档与验证缺口

- [X] T040 [US1] 显式补充登录/注册可访问性自动化测试 `frontend/src/tests/auth-pages.accessibility.test.tsx`
- [X] T041 [P] 对性能目标补充可执行证据并落盘 `specs/001-ui-guideline-remediation/artifacts/performance-goals.md`
- [X] T042 [P] 对 FR-010 权限不回归补充验证证据 `specs/001-ui-guideline-remediation/artifacts/permission-regression.md`
- [X] T043 将关键路径页面清单固化到规格文档 `specs/001-ui-guideline-remediation/spec.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: 可立即开始
- **Phase 2 (Foundational)**: 依赖 Phase 1 完成；阻塞所有用户故事
- **Phase 3-5 (US1-US3)**: 依赖 Phase 2 完成；建议按 P1 → P2 → P3 递进
- **Phase 6 (Polish)**: 依赖目标用户故事完成后执行

### User Story Dependencies

- **US1 (P1)**: 无业务故事依赖，Foundation 完成后可立即实施（MVP）
- **US2 (P2)**: 依赖 Foundation；可在 US1 后实施，避免交互冲突
- **US3 (P3)**: 依赖 Foundation；建议在 US1/US2 稳定后统一收口

### Within Each User Story

- 先改共享结构，再改页面表层
- 先修复语义/标签，再做文案与样式一致性
- 每个故事完成后立即执行独立验收再进入下一故事

## Parallel Opportunities

- **Setup**: T002、T003 可并行
- **Foundational**: T005、T006、T007 可并行
- **US1**: T010、T011、T014、T015 可并行
- **US2**: T023、T024、T025 可并行
- **US3**: T030、T031、T032 可并行
- **Polish**: T035、T036 可并行

---

## Parallel Example: User Story 1

```bash
# 并行修复表单标签（不同文件）
Task: T010 frontend/src/components/home/HeroSection.tsx
Task: T011 frontend/src/components/admin/UserFilters.tsx
Task: T014 frontend/src/app/review/[token]/page.tsx
Task: T015 frontend/src/app/(public)/review/assignment/[assignmentId]/page.tsx
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. 完成 Phase 1 + Phase 2
2. 完成 US1（T009-T019）
3. 立刻做独立验收（键盘 + 读屏器 + 弹窗关闭路径）
4. 满足后可先交付一版可用改进

### Incremental Delivery

1. US1：先达成“可访问可用”
2. US2：再达成“语义交互一致”
3. US3：最后达成“文案与时间口径统一”
4. 每阶段都可单独演示并验证价值

### Team Parallel Strategy

1. 成员 A：US1（表单与弹窗）
2. 成员 B：US2（导航与语义交互）
3. 成员 C：US3（一致性收口）
4. 由一人负责 Phase 6 汇总回归与问题台账更新

---

## Notes

- `[P]` 任务必须确保文件不冲突且无未完成前置依赖
- 所有任务均绑定具体文件路径，执行时可直接落地
- 本任务单不引入后端接口变化，聚焦前端 UI 规范整改
