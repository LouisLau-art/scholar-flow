# Implementation Plan: Production Pipeline Workspace (Feature 042)

**Branch**: `042-production-pipeline` | **Date**: 2026-02-09 | **Spec**: [/root/scholar-flow/specs/042-production-pipeline/spec.md](/root/scholar-flow/specs/042-production-pipeline/spec.md)
**Input**: Feature specification from `/root/scholar-flow/specs/042-production-pipeline/spec.md`

## Summary

实现“录用后生产协作闭环”工作间，覆盖三类核心动作：
- 排版编辑创建生产轮次并上传清样（Galley Proof）。
- 作者在截止时间内完成“确认无误”或“提交修正清单”。
- 编辑基于作者反馈执行发布前核准，强制发布仅使用已核准生产版本。

方案遵循现有状态机和门禁：在不破坏 `approved -> layout -> english_editing -> proofreading -> published` 主链路的前提下，新增可审计的“生产轮次域模型”和作者校对交互接口。

## Technical Context

**Language/Version**: Python 3.14+ (local), Python 3.12 (HF Docker runtime), TypeScript 5.x  
**Primary Dependencies**: FastAPI, Pydantic v2, Supabase (PostgreSQL + Storage), Next.js 14 App Router, React 18, Tailwind CSS, Shadcn UI  
**Storage**: Supabase PostgreSQL (`manuscripts`, `status_transition_logs`, new `production_*` tables), Supabase Storage (private buckets: `manuscripts`, `production-proofs`)  
**Testing**: pytest (unit/integration), Vitest, Playwright  
**Target Platform**: Web application (Vercel frontend + Hugging Face Spaces backend)  
**Project Type**: web (frontend + backend + supabase migrations)  
**Performance Goals**: 生产工作间聚合接口 P95 < 500ms；非文件上传交互请求 P95 < 800ms  
**Constraints**: 单稿件仅允许 1 个活跃生产轮次；作者仅可见自身稿件且仅处理被指派轮次；发布必须绑定已核准生产版本；禁止前端直连私有桶  
**Scale/Scope**: MVP/UAT 规模下支持 100-500 篇活跃稿件/月，单稿件 1-3 轮生产迭代

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate Review

- **I. 胶水编程**: PASS  
  复用现有 `production_service`、`status_transition_logs`、站内通知与 signed URL 访问模式，仅补充生产轮次域能力。
- **II. 测试与效率**: PASS  
  采用分层测试策略：先补单元/集成覆盖状态与权限，再补 E2E 关键路径。
- **III. 安全优先**: PASS  
  所有敏感操作需鉴权 + 角色校验 + 稿件归属校验；作者端严格最小权限。
- **IV. 持续同步与提交**: PASS  
  设计若引入新环境约定（bucket、迁移、路由）需同步 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`。
- **V. 环境与工具规范**: PASS  
  前端 `bun`、后端 `uv`、默认云端 Supabase 迁移策略保持一致。

### Post-Phase 1 Design Gate Review

- **I. 胶水编程**: PASS  
  设计已限定在现有架构延伸，不引入额外服务或新基础设施。
- **II. 测试与效率**: PASS  
  合同、数据模型、快速验收步骤均可直接映射到测试任务。
- **III. 安全优先**: PASS  
  合同中明确了编辑/作者权限边界、私有文件访问与最终可见性门禁。
- **IV. 持续同步与提交**: PASS  
  已在计划中标注文档同步触发条件和发布流程要求。
- **V. 环境与工具规范**: PASS  
  仅新增 Supabase schema/storage 变更，符合现有部署约束。

## Project Structure

### Documentation (this feature)

```text
/root/scholar-flow/specs/042-production-pipeline/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api.yaml
└── tasks.md              # 由 /speckit.tasks 生成
```

### Source Code (repository root)

```text
/root/scholar-flow/backend/
├── app/
│   ├── api/v1/editor.py
│   ├── api/v1/manuscripts.py
│   ├── models/production_workspace.py
│   ├── services/production_workspace_service.py
│   └── services/production_service.py
└── tests/
    ├── integration/test_production_workspace_api.py
    ├── integration/test_proofreading_author_flow.py
    └── unit/test_production_workspace_service.py

/root/scholar-flow/frontend/
├── src/
│   ├── app/(admin)/editor/production/[id]/page.tsx
│   ├── app/proofreading/[id]/page.tsx
│   ├── components/editor/production/
│   ├── components/author/proofreading/
│   ├── services/editorApi.ts
│   └── services/manuscriptApi.ts
└── tests/
    ├── e2e/specs/production_pipeline.spec.ts
    └── unit/production-workspace.test.ts

/root/scholar-flow/supabase/migrations/
└── 20260209xxxxxx_production_pipeline_workspace.sql
```

**Structure Decision**: 采用现有“前后端分层 + Supabase 迁移”结构，不新增子项目。后端集中在 `editor.py`/`manuscripts.py` 暴露角色化入口，核心业务放在 `production_workspace_service.py`，前端分别提供编辑端与作者端页面。

## Complexity Tracking

无宪法豁免项；当前设计在既有架构约束内可实现。
