# Implementation Plan: GAP-P0-01 Pre-check Role Hardening

**Branch**: `044-precheck-role-hardening` | **Date**: 2026-02-09 | **Spec**: [/root/scholar-flow/specs/044-precheck-role-hardening/spec.md](/root/scholar-flow/specs/044-precheck-role-hardening/spec.md)  
**Input**: Feature specification from `/root/scholar-flow/specs/044-precheck-role-hardening/spec.md`

## Summary

本特性的目标是把已有但较薄的 Feature 038 预审链路，升级为可上线的角色闭环：
- 后端补齐 ME->AE->EIC 的严格 RBAC、状态前置条件、并发/幂等处理；
- 补齐 AE“修回”必填 comment、EIC 决策规范化与拒稿路径门禁；
- 统一把关键预审动作写入 `status_transition_logs`，形成可追责时间线；
- 在 Process 列表与稿件详情页展示预审子阶段、当前责任角色、关键时间点；
- 将当前占位式 pre-check E2E 改成可执行回归场景。

实现策略遵循“胶水编程”：复用现有 `editor.py` 路由、`EditorService`、`EditorialService`、`status_transition_logs`，不引入新外部依赖或新微服务。

## Technical Context

**Language/Version**: Python 3.14+（本地开发）/ Python 3.12（HF Docker），TypeScript 5.x（Strict）  
**Primary Dependencies**: FastAPI 0.115+, Pydantic v2, Supabase-py v2, Next.js 14.2 (App Router), React 18, Tailwind + Shadcn  
**Storage**: Supabase PostgreSQL（`manuscripts`, `user_profiles`, `status_transition_logs`），Supabase Storage（复用）  
**Testing**: pytest（unit/integration/contract），Vitest，Playwright（mocked E2E + 回归场景）  
**Target Platform**: Vercel（Frontend）+ Hugging Face Spaces（Backend）+ Cloud Supabase  
**Project Type**: web（frontend + backend + migrations）  
**Performance Goals**: 预审队列接口在 50 条分页场景下 p95 < 300ms；详情页时间线查询 p95 < 500ms  
**Constraints**: 拒稿仅允许经 `decision/decision_done`；AE 修回必须 comment；不破坏现有 `/editor/process` 主入口；敏感操作保持鉴权  
**Scale/Scope**: 覆盖全部 `pre_check` 稿件；支持 1k+ 稿件 process 列表过滤与审计查询

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate Review

- **I. 胶水编程**: PASS  
  复用 `EditorService` / `EditorialService` 与现有表结构，优先补齐校验与审计，不重建工作流子系统。
- **II. 测试与效率**: PASS  
  采用分层回归：后端关键单元+集成、前端 mocked E2E 主路径，保证可回归而不牺牲迭代速度。
- **III. 安全优先**: PASS  
  预审关键操作全部要求登录与角色；服务层再做“被分配 AE”归属校验，防越权。
- **IV. 持续同步与提交**: PASS  
  本轮是重大流程规划，需运行 agent context 更新脚本并同步上下文文件。
- **V. 环境与工具规范**: PASS  
  严格沿用 `uv` + `bun`、云端 Supabase 迁移流程，不新增偏离工具链。

### Post-Phase 1 Design Gate Review

- **I. 胶水编程**: PASS  
  数据模型以“现有表 + payload 约定”为主，仅在必要时添加轻量约束/索引。
- **II. 测试与效率**: PASS  
  合同、数据模型、quickstart 已映射到可执行测试命令与验收场景。
- **III. 安全优先**: PASS  
  RBAC 与归属校验明确分层（路由 + 服务）并写入合同。
- **IV. 持续同步与提交**: PASS  
  计划中包含上下文同步与后续任务拆分入口。
- **V. 环境与工具规范**: PASS  
  设计不依赖本地私有能力，能直接在 HF/Vercel/Supabase 环境执行。

## Project Structure

### Documentation (this feature)

```text
/root/scholar-flow/specs/044-precheck-role-hardening/
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
│   ├── services/editorial_service.py
│   └── models/manuscript.py
└── tests/
    ├── integration/test_precheck_flow.py
    ├── integration/test_editor_service.py
    └── unit/test_editor_service.py

/root/scholar-flow/frontend/
├── src/
│   ├── app/(admin)/editor/process/page.tsx
│   ├── components/editor/ManuscriptTable.tsx
│   ├── components/editor/ManuscriptActions.tsx
│   ├── services/editorApi.ts
│   ├── services/editorService.ts
│   └── pages/editor/{intake,workspace,academic}/page.tsx
└── tests/e2e/specs/precheck_workflow.spec.ts

/root/scholar-flow/supabase/migrations/
└── 20260206150000_add_precheck_fields.sql (已存在，作为本特性基线)
```

**Structure Decision**: 采用“后端服务强化 + Process/详情页可视化 + E2E 回归补齐”的最小增量路线。  
不新开独立 pre-check 前端站点，不引入新服务，优先把已有主入口 `/editor/process` 做成可操作的预审闭环。

## Complexity Tracking

无宪法违规项，无需豁免记录。
