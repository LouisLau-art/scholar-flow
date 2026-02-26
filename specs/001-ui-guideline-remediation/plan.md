# Implementation Plan: UI Guideline Remediation

**Branch**: `001-ui-guideline-remediation` | **Date**: 2026-02-26 | **Spec**: `/root/scholar-flow/specs/001-ui-guideline-remediation/spec.md`  
**Input**: Feature specification from `/root/scholar-flow/specs/001-ui-guideline-remediation/spec.md`

## Summary

本特性目标是将 `problem.md` 中已识别的 UI 规范问题按优先级系统性收敛，重点覆盖三类高收益整改：

1. **可访问性闭环**：关键表单标签、焦点可见性、弹窗关闭路径与键盘可达性。
2. **语义交互收敛**：清理伪交互（`cursor-pointer` 非语义点击）、替换占位导航。
3. **一致性治理**：统一加载文案省略号与时间展示口径，降低页面碎片化体验。

技术策略：优先复用现有 shadcn/ui 与项目公共工具（`date-display`、`Dialog`、`Input`、`Button`），避免新增重框架与后端改造。

## Technical Context

**Language/Version**: TypeScript 5.x（strict）, Next.js 14.2（App Router）, React 18  
**Primary Dependencies**: shadcn/ui（Radix primitives）, Tailwind CSS v4, next-themes, lucide-react  
**Storage**: N/A（本特性不新增存储结构）  
**Testing**: Vitest（组件/单元）, Playwright（关键路径键盘与交互验证）, ESLint  
**Target Platform**: Web（桌面 + 移动浏览器）  
**Project Type**: Web application（frontend 主改造，backend 无接口新增）  
**Performance Goals**:
- 首屏请求数不增加；
- 关键页面交互不引入额外网络请求；
- 无明显渲染回退（与当前主干持平或更优）。
**Constraints**:
- 不改业务权限语义与后端状态机；
- 不引入新的鉴权路径；
- 保持现有路由与接口兼容；
- 修复应可按页面分批回归，不阻断主业务流。
**Scale/Scope**:
- 范围覆盖 `problem.md` 中 Tailwind/shadcn/web-guidelines 三部分前端问题；
- 优先处理 High 与 Medium 问题；
- 目标涉及约 10-20 个前端文件的渐进改造。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Gate

- **I. 胶水编程**: PASS  
  方案以“复用现有 UI 基座”为主，不新增大型基础设施；优先组合现有 `Dialog/Input/Button/date-display`。
- **II. 测试与效率**: PASS  
  采用分层回归：先跑改动相关 Vitest/Playwright，再做关键路径抽样验证。
- **III. 安全优先**: PASS  
  本次不新增敏感接口与权限逻辑，不改变后端安全边界。
- **IV. 持续同步与提交**: PASS  
  计划产物与实现范围均落在 feature 目录；后续实现完成后按约定同步上下文文档。
- **V. 环境与工具规范**: PASS  
  使用既有技术栈与工具链（`bun`/Next.js/Tailwind/shadcn）。

### Post-Design Gate (Re-check)

- **I. 胶水编程**: PASS  
  研究与数据模型均基于现有组件/规范，不引入额外框架。
- **II. 测试与效率**: PASS  
  quickstart 已明确分层测试命令与人工验收步骤。
- **III. 安全优先**: PASS  
  合同文件仅约束既有 API 兼容，不引入新鉴权风险。
- **IV. 持续同步与提交**: PASS  
  计划阶段产物齐全，便于后续 tasks/implement 分批推进。
- **V. 环境与工具规范**: PASS  
  方案与当前云端 Supabase + Vercel/HF 架构兼容，无新增环境依赖。

## Project Structure

### Documentation (this feature)

```text
/root/scholar-flow/specs/001-ui-guideline-remediation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ui-regression-api.openapi.yaml
└── tasks.md                     # 由 /speckit.tasks 生成
```

### Source Code (repository root)

```text
/root/scholar-flow/frontend/
├── src/app/
│   ├── login/page.tsx
│   ├── signup/page.tsx
│   ├── page.tsx
│   └── (public)/review/assignment/[assignmentId]/page.tsx
├── src/components/
│   ├── AcademicCheckModal.tsx
│   ├── layout/SiteHeader.tsx
│   ├── portal/SiteFooter.tsx
│   ├── admin/UserFilters.tsx
│   ├── finance/FinanceInvoicesTable.tsx
│   └── editor/
│       ├── ManuscriptTable.tsx
│       ├── InternalNotebook.tsx
│       └── AuditLogTimeline.tsx
└── src/lib/
    └── date-display.ts
```

**Structure Decision**: 采用既有前端单仓结构，仅在 `frontend/src` 内分层修复（页面层、组件层、公共工具层），不触发后端目录结构变化。

## Implementation Phases

### Phase 0 - Research & Rule Freezing

- 冻结 UI 规范口径：label、语义交互、focus、ellipsis、date format。
- 形成可执行决策，产出 `research.md`。

### Phase 1 - Design & Contracts

- 抽取本次整改涉及的数据与约束对象，产出 `data-model.md`。
- 对关键用户动作涉及的既有 API 建立兼容合同，产出 `contracts/ui-regression-api.openapi.yaml`。
- 编写可回归步骤，产出 `quickstart.md`。

### Phase 2 - Task-ready Planning

- 进入 `/speckit.tasks`，将问题按“高优先级可访问性 -> 语义交互 -> 一致性”拆批执行。

## Complexity Tracking

当前无宪法豁免项，无额外复杂度例外申请。
