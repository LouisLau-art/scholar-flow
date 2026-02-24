# Implementation Plan: Editor Performance Refactor

**Branch**: `001-editor-performance-refactor` | **Date**: 2026-02-24 | **Spec**: `/root/scholar-flow/specs/001-editor-performance-refactor/spec.md`
**Input**: Feature specification from `/specs/001-editor-performance-refactor/spec.md`

## Summary

本特性面向编辑端性能与可运维性收敛：
1. 保持已完成的详情链路降载改造收益（首屏优先、区块惰性、局部刷新）。
2. 将同等级降载策略扩展到流程列表与工作台链路。
3. 补齐审稿候选搜索的“弹窗后加载 + 防抖 + 短缓存”一致策略。
4. 建立可复用的改前/改后基线与发布回归门槛，避免后续性能回退。

## Technical Context

**Language/Version**: Python 3.14+（backend）, TypeScript 5.x（frontend）  
**Primary Dependencies**: FastAPI, Pydantic v2, Supabase-py, Next.js 14 App Router, React 18, bun, uv  
**Storage**: Supabase PostgreSQL（云端）+ 前端内存短缓存（会话级）+ 文档化基线产物（仓库 specs）  
**Testing**: pytest, Vitest, Playwright, `./scripts/test-fast.sh`, `./scripts/run-all-tests.sh`  
**Target Platform**: Web（Vercel 前端 + HF Spaces backend）
**Project Type**: web（frontend + backend）  
**Performance Goals**: 
- 详情页：95% 请求在 3 秒内进入首屏可操作。
- 流程列表/工作台：95% 首次进入或刷新在 2.5 秒内核心可操作。
- 候选重复查询：95% 响应时间 ≤ 首次查询的 50%。  
**Constraints**:
- 不改变现有 RBAC 与业务状态机语义。
- 不引入前端持有敏感凭证。
- 不牺牲可观测性与回归可验证性。
- 与已有 `timeline-context`、`cards-context`、`release-validation` 能力保持兼容。  
**Scale/Scope**: 
- 页面范围：编辑详情页、`/editor/process`、`/editor/workspace`、审稿分配弹窗。
- 角色范围：managing_editor、assistant_editor、editor_in_chief、admin。
- 交付范围：性能优化 + 基线门禁，不扩展新的业务流程能力。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase-0 Gate

- **I. 胶水编程**: PASS
  - 方案基于现有 API 与现有组件模式（惰性加载、缓存、局部刷新）收敛，不引入新框架。
- **II. 测试与效率**: PASS
  - 采用 Tier 1/2/3 分层验证；性能基线与功能回归同时纳入门禁。
- **III. 安全优先**: PASS
  - 不新增匿名敏感接口；继续复用后端鉴权与 RBAC 控制。
- **IV. 持续同步与提交**: PASS
  - 本计划会产出完整 specs 文档；实现阶段继续同步 AGENTS/CLAUDE/GEMINI。
- **V. 环境与工具规范**: PASS
  - 命令链路遵循 bun/uv，默认云端 Supabase 假设不变。

### Post-Phase-1 Re-check

- **I. 胶水编程**: PASS（数据模型、契约均复用现有结构，未引入新基础设施）
- **II. 测试与效率**: PASS（quickstart 已定义定向与全量回归路径）
- **III. 安全优先**: PASS（契约不引入越权读取路径）
- **IV. 持续同步与提交**: PASS（产物完整：plan/research/data-model/contracts/quickstart）
- **V. 环境与工具规范**: PASS（无工具链偏离）

## Project Structure

### Documentation (this feature)

```text
specs/001-editor-performance-refactor/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── editor-performance.openapi.yaml
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/v1/
│   ├── services/
│   ├── models/
│   └── core/
└── tests/
    ├── unit/
    ├── integration/
    └── contract/

frontend/
├── src/
│   ├── app/(admin)/editor/
│   ├── components/editor/
│   ├── components/
│   └── services/
└── tests/
    ├── unit/
    └── e2e/

scripts/
├── perf/
│   ├── capture-editor-baseline.sh
│   ├── compare-editor-baseline.sh
│   └── write-regression-report.sh
├── run-all-tests.sh
└── validate-editor-performance.sh
```

**Structure Decision**: 使用现有 Web 双端结构，重点改动落在 `frontend` 的编辑端链路与 `backend/app/api/v1` 的聚合接口行为，不新增新层级目录。

## Phase Plan

### Phase 0: Research & Decision Lock

- 锁定“短缓存”策略边界：缓存键、TTL、失效条件、并发去重策略。
- 锁定 process/workspace 降载策略：首屏优先字段、延迟加载边界、刷新策略。
- 锁定基线与门禁策略：采样口径、阈值、失败处置。

### Phase 1: Design & Contracts

- 输出性能相关实体模型与状态规则（data-model）。
- 输出优化链路契约（contracts），覆盖详情、流程、工作台、审稿候选搜索、回归门禁读取。
- 输出 quickstart 验证路径（开发定向 + 发布前全量 + 基线对比）。

### Phase 2: Task Planning Input Preparation

- 明确 P1/P2/P3 用户故事对应交付切片与可独立验收标准。
- 明确测试任务拆分边界（定向测试、全量回归、性能对比报告）。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Risks & Mitigations

- **风险**: `001-*` 前缀已有历史 spec，`setup-plan.sh` 会打印多目录提示。  
  **缓解**: 当前分支已绑定到 `/specs/001-editor-performance-refactor`，后续任务全部显式使用绝对路径。
- **风险**: 前端短缓存若失效策略不当，可能展示旧候选数据。  
  **缓解**: 缓存键绑定 `manuscript_id + query + role scope`，并在弹窗关闭/稿件切换时主动失效。
- **风险**: 仅做性能优化易引入行为回归。  
  **缓解**: 将 RBAC/状态流转相关回归纳入 quickstart 必跑项。
