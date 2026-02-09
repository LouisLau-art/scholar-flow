# Implementation Plan: GAP-P0-03 Internal Collaboration Enhancement

**Branch**: `045-internal-collaboration-enhancement` | **Date**: 2026-02-09 | **Spec**: [/root/scholar-flow/specs/045-internal-collaboration-enhancement/spec.md](/root/scholar-flow/specs/045-internal-collaboration-enhancement/spec.md)  
**Input**: Feature specification from `/root/scholar-flow/specs/045-internal-collaboration-enhancement/spec.md`

## Summary

本特性的目标是把 Feature 036 的“评论协作”升级为“可触达、可执行、可排程”的内部协作闭环：
- 在 Internal Notebook 支持 `@mentions` 并触发站内通知；
- 新增稿件级内部任务（负责人、截止时间、状态、操作轨迹）；
- 在 Process 列表展示逾期风险并支持“仅看逾期”筛选。

实现策略遵循“胶水编程”：复用现有评论接口、通知中心、Process 列表查询框架与详情页布局，只在必要处新增最小数据表与聚合字段。

## Technical Context

**Language/Version**: Python 3.14+（本地开发）/ Python 3.12（HF Docker），TypeScript 5.x（Strict）  
**Primary Dependencies**: FastAPI 0.115+, Pydantic v2, Supabase-py v2, Next.js 14.2 (App Router), React 18, Tailwind + Shadcn, date-fns  
**Storage**: Supabase PostgreSQL（新增 mention/task 相关表），Supabase Storage（复用，无新增 bucket）  
**Testing**: pytest（unit/integration/contract），Vitest，Playwright（mocked E2E + 关键协作路径）  
**Target Platform**: Vercel（Frontend）+ Hugging Face Spaces（Backend）+ Cloud Supabase  
**Project Type**: web（frontend + backend + migrations）  
**Performance Goals**:  
- 评论提及通知写入在单次提交 5 个提及对象下 p95 < 500ms  
- Process 列表逾期筛选在 50 条分页下 p95 < 300ms  
**Constraints**:  
- 敏感操作必须通过内部角色鉴权  
- 逾期规则固定为“当前时间 > 截止时间 且任务未完成”  
- 不新增前端独立入口，继续沿用 `/editor/manuscript/[id]` 与 `/editor/process`  
**Scale/Scope**:  
- 单稿件最多 200 条内部任务、1000 条内部评论  
- 单评论最多 20 个有效提及对象

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate Review

- **I. 胶水编程**: PASS  
  复用现有 `internal_comments`、`notifications`、`EditorService.list_manuscripts_process` 与详情页组件，不引入新服务形态。
- **II. 测试与效率**: PASS  
  采用“后端单元+集成 + 前端单测 + mocked E2E”分层验证，符合 Tier-1/Tier-2/Tier-3 策略。
- **III. 安全优先**: PASS  
  评论提及和任务操作均限定内部角色，任务编辑动作走服务层权限判断。
- **IV. 持续同步与提交**: PASS  
  本阶段执行 `update-agent-context.sh bob`，后续实现阶段继续保持三份上下文同步。
- **V. 环境与工具规范**: PASS  
  仅使用 `uv`/`bun` 与云端 Supabase，遵循现有迁移与部署约定。

### Post-Phase 1 Design Gate Review

- **I. 胶水编程**: PASS  
  设计采用“新增最小表 + 读时聚合”方案，不引入消息队列或独立协作子系统。
- **II. 测试与效率**: PASS  
  合同、数据模型、quickstart 均可映射为可执行测试任务。
- **III. 安全优先**: PASS  
  提及对象、任务负责人和任务编辑权限均有明确鉴权边界。
- **IV. 持续同步与提交**: PASS  
  计划阶段已执行 agent context 更新；实现阶段可直接沿用流程。
- **V. 环境与工具规范**: PASS  
  无额外运行时依赖，不改变现有部署形态。

## Project Structure

### Documentation (this feature)

```text
/root/scholar-flow/specs/045-internal-collaboration-enhancement/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api.yaml
└── tasks.md
```

### Source Code (repository root)

```text
/root/scholar-flow/backend/
├── app/
│   ├── api/v1/editor.py
│   ├── services/editor_service.py
│   └── services/notification_service.py
└── tests/
    ├── contract/test_api_paths.py
    ├── integration/test_internal_collaboration_flow.py
    ├── integration/test_editor_service.py
    └── unit/test_internal_tasks_service.py

/root/scholar-flow/frontend/
├── src/
│   ├── components/editor/InternalNotebook.tsx
│   ├── components/editor/InternalTasksPanel.tsx
│   ├── components/editor/ManuscriptTable.tsx
│   ├── components/editor/ProcessFilterBar.tsx
│   ├── services/editorApi.ts
│   └── app/(admin)/editor/manuscript/[id]/page.tsx
└── tests/
    ├── unit/internal-notebook-mentions.test.tsx
    └── e2e/specs/internal-collaboration-overdue.spec.ts

/root/scholar-flow/supabase/migrations/
└── 20260209xxxxxx_internal_collaboration_mentions_tasks.sql
```

**Structure Decision**: 采用“稿件详情协作增强 + Process 聚合扩展”的增量结构。  
不新增独立页面域，优先把协作能力附着在已有编辑工作流上，降低迁移和培训成本。

## Complexity Tracking

无宪法违规项，无需豁免记录。
