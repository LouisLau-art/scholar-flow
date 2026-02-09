# Implementation Plan: GAP-P1-01 Finance Real Invoices Sync

**Branch**: `046-finance-invoices-sync` | **Date**: 2026-02-09 | **Spec**: [/root/scholar-flow/specs/046-finance-invoices-sync/spec.md](/root/scholar-flow/specs/046-finance-invoices-sync/spec.md)  
**Input**: Feature specification from `/root/scholar-flow/specs/046-finance-invoices-sync/spec.md`

## Summary

本特性的目标是把 `/finance` 从本地演示页升级为真实可用的内部财务工作台：
- Finance 列表改为读取 `public.invoices` 真实数据并展示稿件关联信息；
- 支持 `unpaid/paid/waived` 状态筛选，并提供“当前筛选快照”导出（CSV）；
- 与 Editor Pipeline 现有 `Mark Paid` 共享同一支付确认事实来源，避免双入口状态漂移；
- 在确认支付接口增加并发冲突识别（乐观校验），并写入审计日志。

实现策略遵循“胶水编程”：复用 `editor/invoices/confirm`、`status_transition_logs`、现有鉴权与角色体系，不引入新服务形态或新外部依赖。

## Technical Context

**Language/Version**: Python 3.14+（本地）/ Python 3.12（HF Docker），TypeScript 5.x（Strict）  
**Primary Dependencies**: FastAPI 0.115+, Pydantic v2, Supabase-py v2, Next.js 14.2 (App Router), React 18, Tailwind + Shadcn  
**Storage**: Supabase PostgreSQL（`invoices`, `manuscripts`, `user_profiles`, `status_transition_logs`），Supabase Storage（复用 `invoices` bucket）  
**Testing**: pytest（unit/integration/contract），Vitest，Playwright（mocked E2E + 财务闭环场景）  
**Target Platform**: Vercel（Frontend）+ Hugging Face Spaces（Backend）+ Cloud Supabase  
**Project Type**: web（frontend + backend + migrations）  
**Performance Goals**:
- Finance 列表接口（page_size=50）p95 < 500ms
- CSV 导出 1k 条记录在 10 秒内完成并返回可下载文件  
**Constraints**:
- 仅 `editor/admin` 可访问 Finance 数据与导出
- 前端不得直连 Supabase `invoices`，统一走后端 API
- 与 `POST /api/v1/editor/invoices/confirm` 行为一致，不新增并行事实源
- 并发确认支付需返回可识别冲突（409），禁止静默覆盖  
**Scale/Scope**:
- Finance 列表按分页支持 10k+ 账单总量
- 单次导出目标支持当前筛选下最多 5k 记录（MVP 级对账范围）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate Review

- **I. 胶水编程**: PASS  
  复用 `invoices` 表、`editor/invoices/confirm` 与 `status_transition_logs`，不引入新账务子系统。
- **II. 测试与效率**: PASS  
  采用分层验证：后端单元/集成 + 前端单测 + E2E 对账主路径。
- **III. 安全优先**: PASS  
  财务读写与导出均限制 `editor/admin`，并保持 JWT + 角色校验。
- **IV. 持续同步与提交**: PASS  
  本阶段执行 `update-agent-context.sh bob`，后续实现阶段继续同步上下文文件。
- **V. 环境与工具规范**: PASS  
  沿用 `uv` + `bun` 与云端 Supabase，不引入偏离部署环境的依赖。

### Post-Phase 1 Design Gate Review

- **I. 胶水编程**: PASS  
  数据模型以“现有表 + 读模型映射”实现，新增仅限必要索引与接口编排。
- **II. 测试与效率**: PASS  
  合同、数据模型与 quickstart 已映射成可执行测试清单。
- **III. 安全优先**: PASS  
  页面保护（middleware）与后端 RBAC 双层防护，导出仍需鉴权。
- **IV. 持续同步与提交**: PASS  
  计划产物与 agent context 已覆盖后续 `speckit.tasks` 输入。
- **V. 环境与工具规范**: PASS  
  方案可直接在 Vercel/HF/Supabase 现有架构落地。

## Project Structure

### Documentation (this feature)

```text
/root/scholar-flow/specs/046-finance-invoices-sync/
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
│   └── models/invoices.py
└── tests/
    ├── contract/test_api_paths.py
    ├── integration/test_finance_invoices_sync.py
    └── unit/test_finance_invoice_mapping.py

/root/scholar-flow/frontend/
├── src/
│   ├── app/finance/page.tsx
│   ├── services/editorApi.ts
│   ├── components/finance/FinanceInvoicesTable.tsx
│   └── middleware.ts
└── tests/
    ├── unit/finance-dashboard.test.tsx
    └── e2e/specs/finance-invoices-sync.spec.ts

/root/scholar-flow/supabase/migrations/
└── 20260209xxxxxx_finance_invoices_indexes.sql (如需补齐筛选/导出索引)
```

**Structure Decision**: 采用“现有 editor + finance 路径增量增强”方案。  
后端在 `editor.py` 内增加 Finance 读取/导出接口并增强支付确认冲突校验；前端继续使用 `/finance` 路由，但改为真实 API 驱动并补齐权限保护。

## Complexity Tracking

无宪法违规项，无需豁免记录。
