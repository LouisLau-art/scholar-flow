# Implementation Plan: Automated Invoice PDF (Feature 026)

**Branch**: `026-automated-invoice-pdf` | **Date**: 2026-02-03 | **Spec**: `specs/026-automated-invoice-pdf/spec.md`
**Input**: Feature specification from `specs/026-automated-invoice-pdf/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

When a manuscript is accepted (`approved`), generate a professional invoice PDF automatically, store it in Supabase Storage, and allow authorized users (Author + internal roles) to download it. Support regeneration without changing payment status or creating duplicate invoice records.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.14+  
**Primary Dependencies**: FastAPI, Pydantic v2, Supabase-py v2.x, Jinja2, WeasyPrint  
**Storage**: Supabase (PostgreSQL + Storage)  
**Testing**: pytest (unit + integration)  
**Target Platform**: Linux server (containerized deploy)  
**Project Type**: web  
**Performance Goals**: Invoice generation completes within 60s of acceptance (async); download link resolves within ~1s typical.  
**Constraints**: PDF generation must not block editor decision UX; failures must be visible and retryable.  
**Scale/Scope**: MVP scale; concurrency-safe generation (no duplicate invoices).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- ✅ 胶水编程：复用 Jinja2（已存在）+ WeasyPrint 生成 PDF；最少自定义逻辑只做组装与权限校验。
- ✅ 测试与效率：为关键路径补充单元/集成测试；不要求每次全量跑，但合并前可回归。
- ✅ 安全优先：下载必须鉴权；前端不接触 `service_role key`；Storage 默认走后端签名链接。
- ⚠️ MVP 延期清单冲突：宪法里“账单 PDF 存储闭环”原标记为 MVP 延期；但本 Feature 026 的目的就是实现该闭环（业务明确要求“正式 PDF 账单”）。实现后需要同步更新宪法与 `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`（移出延期项或标注已完成）。

## Project Structure

### Documentation (this feature)

```text
specs/026-automated-invoice-pdf/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── services/
│   └── lib/
└── tests/

frontend/
├── src/
│   ├── app/
│   ├── components/
│   └── services/
└── tests/
```

**Structure Decision**: 采用 Web application 结构（`backend/` + `frontend/`）。本 Feature 主要改动集中在 `backend/app/services`、`backend/app/api/v1`、以及 Supabase migration / Storage bucket 约定；前端只需要增加“下载账单”入口并调用新接口（如已有占位则复用）。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| MVP 延期项被实现 | 业务要求“正式可下载 PDF 账单”，用于付款流程与对外展示 | “即时生成不落盘”无法满足“正式账单”与“随时下载”的需求 |

## Phase Plan

### Phase 0 (Research)

产出 `specs/026-automated-invoice-pdf/research.md`，覆盖：
- WeasyPrint 在容器环境的系统依赖清单（APT 包）与常见坑（字体、Pango/Cairo）
- Storage 私有桶 + signed URL 下载的安全模式（避免回填短期 signed URL）
- invoice number 规则与幂等策略（同一稿件仅一个 invoice；重复生成覆盖 PDF，不改支付状态）

### Phase 1 (Design & Contracts)

产出：
- `specs/026-automated-invoice-pdf/data-model.md`：`invoices` 字段扩展与约束（invoice_number、pdf_path、pdf_generated_at、pdf_error 等）
- `specs/026-automated-invoice-pdf/contracts/`：新增/变更 API 的 OpenAPI 片段（下载、再生成）
- `specs/026-automated-invoice-pdf/quickstart.md`：本地/云端验证步骤（迁移、创建 bucket、accept 触发、下载验证）

并执行 Agent Context 同步：
- 运行 `.specify/scripts/bash/update-agent-context.sh`（无参数，更新所有已存在 Agent 上下文文件）

### Phase 2 (Implementation - 下一步由 /speckit.implement 执行)

按 tasks.md 拆分实现：
- 后端：生成 PDF、上传 Storage、回填 invoices、下载/再生成接口、权限校验、测试
- Supabase：创建 `invoices` 桶与策略（或完全由后端 signed URL 访问）
- 前端：作者/编辑下载按钮（复用现有 Invoice UI）
