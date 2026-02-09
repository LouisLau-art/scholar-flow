# Implementation Plan: Cloud Rollout Regression (GAP-P0-02)

**Branch**: `043-production-cloud-rollout` | **Date**: 2026-02-09 | **Spec**: [/root/scholar-flow/specs/043-production-cloud-rollout/spec.md](/root/scholar-flow/specs/043-production-cloud-rollout/spec.md)
**Input**: Feature specification from `/root/scholar-flow/specs/043-production-cloud-rollout/spec.md`

## Summary

目标是把 Feature 042 从“本地已实现”推进到“云端可稳定放行”，并形成可审计的上线验收机制。  
本次计划将交付三块能力：
- 统一的云端就绪检查（schema/storage/permission/gate）。
- 真实环境业务回归执行与阻塞项判定（禁止带 skip 放行）。
- 可追溯验收报告与失败回退指引。

实现方式遵循“胶水编程”：复用已有 `internal` 管理入口、现有生产协作接口与测试体系，仅补充最小的验收编排服务与报告持久化。

## Technical Context

**Language/Version**: Python 3.14+（本地），Python 3.12（HF Docker），TypeScript 5.x  
**Primary Dependencies**: FastAPI, Pydantic v2, Supabase PostgreSQL/Storage, Next.js 14, pytest, Playwright  
**Storage**: Supabase PostgreSQL（新增 release validation 记录表），Supabase Storage（复用现有 bucket 验证）  
**Testing**: pytest（unit/integration），Playwright（目标 spec），shell 回归脚本  
**Target Platform**: Hugging Face Spaces backend + Vercel frontend + Cloud Supabase  
**Project Type**: web（frontend + backend + migrations + scripts）  
**Performance Goals**: 单次就绪检查 < 5 分钟；单次真实回归验收 < 30 分钟；验收报告生成 < 10 秒  
**Constraints**: 必须通过 `ADMIN_API_KEY` 保护内部验收接口；不得暴露敏感密钥；关键场景 skip 数必须为 0 才允许放行  
**Scale/Scope**: 每次发布窗口 1-5 次验收执行；每次验收覆盖 1 条完整生产协作链路 + 关键门禁场景

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate Review

- **I. 胶水编程**: PASS  
  复用 `backend/app/api/v1/internal.py`、既有生产协作 API、既有测试脚本，不引入新平台组件。
- **II. 测试与效率**: PASS  
  验收机制本身就是测试导向，分层覆盖（快速检查 + 真实回归 + 报告）。
- **III. 安全优先**: PASS  
  内部接口使用 `ADMIN_API_KEY`，执行动作与报告读取仅限内部角色。
- **IV. 持续同步与提交**: PASS  
  若新增环境变量或迁移要求，必须同步 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`。
- **V. 环境与工具规范**: PASS  
  保持 `bun`/`uv` 和云端 Supabase 约定，不引入偏离工具链。

### Post-Phase 1 Design Gate Review

- **I. 胶水编程**: PASS  
  设计只新增“验收编排层 + 报告模型”，核心业务仍调用现有生产协作能力。
- **II. 测试与效率**: PASS  
  合同、数据模型、快速验收步骤都能直接映射到 `/speckit.tasks`。
- **III. 安全优先**: PASS  
  报告中不保存密钥；内部端点维持 `require_admin_key` 保护。
- **IV. 持续同步与提交**: PASS  
  计划包含上下文文档同步步骤与主干绿灯检查步骤。
- **V. 环境与工具规范**: PASS  
  仅新增必要 migration 与脚本；执行命令符合仓库规范。

## Project Structure

### Documentation (this feature)

```text
/root/scholar-flow/specs/043-production-cloud-rollout/
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
│   ├── api/v1/internal.py
│   ├── models/release_validation.py
│   └── services/release_validation_service.py
└── tests/
    ├── integration/test_release_validation_api.py
    └── unit/test_release_validation_service.py

/root/scholar-flow/scripts/
└── validate-production-rollout.sh

/root/scholar-flow/supabase/migrations/
└── 20260209xxxxxx_release_validation_runs.sql

/root/scholar-flow/specs/043-production-cloud-rollout/
└── quickstart.md
```

**Structure Decision**: 采用“后端 internal 验收入口 + 服务层编排 + 独立审计数据表 + 验收脚本”结构。  
不新增前端页面，避免为一次性放行能力引入 UI 复杂度。

## Complexity Tracking

无宪法违规项，无需豁免记录。
