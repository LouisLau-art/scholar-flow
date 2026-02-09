# Implementation Plan: Final Decision Workspace (Feature 041)

**Branch**: `041-final-decision-workspace` | **Date**: 2026-02-06 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/041-final-decision-workspace/spec.md`

## Summary

实现一个沉浸式 Final Decision Workspace，支持编辑聚合审稿信息、生成并保存决策信草稿、提交最终决策，并强制满足工作流约束：
- 拒稿只能在 `decision/decision_done` 阶段执行。
- 决策信与附件仅在 `status=final` 后对作者可见。
- 全流程具备乐观锁并发控制与审计日志留痕。

## Technical Context

- **Language/Version**: Python 3.14+, TypeScript 5.x
- **Primary Dependencies**: FastAPI, Pydantic v2, Supabase (PostgreSQL + Storage), Next.js 14, Shadcn UI
- **Storage**:
  - PostgreSQL: `decision_letters`
  - Supabase Storage: `decision-attachments`
- **Testing**: pytest (unit/integration), Vitest, Playwright
- **Target Platform**: Web (Vercel + HF Space Docker)
- **Performance Goals**: Decision context API `P95 < 500ms`
- **Constraints**:
  - Optimistic locking (`updated_at`)
  - Draft support (`draft/final`)
  - RBAC (`editor_in_chief`, manuscript `assigned_editor`, `admin`)
  - Reject stage gate (`decision` / `decision_done` only)

## Architecture & Data Model

- **Backend API**
  - `GET /api/v1/editor/manuscripts/{id}/decision-context`
  - `POST /api/v1/editor/manuscripts/{id}/submit-decision`
  - `POST /api/v1/editor/manuscripts/{id}/decision-attachments`
  - `GET /api/v1/editor/manuscripts/{id}/decision-attachments/{attachment_id}/signed-url` (editor preview)
  - `GET /api/v1/manuscripts/{id}/decision-attachments/{attachment_id}/signed-url` (author final-only)
- **Core Service**
  - `DecisionService.get_decision_context`
  - `DecisionService.submit_decision`（含并发控制、stage gate、状态流转）
  - `DecisionService.upload_attachment` / `get_attachment_url`
- **Audit & Notification**
  - 复用 `status_transition_logs` 记录决策 payload
  - 提交 `final` 后触发作者站内通知

## Implementation Phases

1. **Phase 1 - Schema & Storage**
   - 建立 `decision_letters`、附件存储与访问策略。
2. **Phase 2 - Backend Foundation**
   - 实现 context/submit/attachment API、RBAC、stage gate、审计日志。
3. **Phase 3 - Frontend Workspace**
   - 完成三栏 UI、Markdown 编辑器、草稿与附件交互。
4. **Phase 4 - Quality Gates**
   - 补齐集成/E2E、性能验证、可见性与权限回归。

## Constitution Check

*GATE: Passed (with explicit constraints mapped to implementation tasks).*

- **Glue Coding**: 复用 Reviewer Workspace 的 PDF 预览与已有状态流转能力。
- **Test-First / Coverage**: 每个关键链路（stage gate、final 可见性、并发冲突）均有测试任务。
- **Security First**: 严格 RBAC + 稿件归属校验 + final-only author visibility。
- **Env & Tooling**: 使用 `uv`、`bun` 与现有 CI-like 测试脚本。
- **Workflow Constraint**: 拒稿阶段门禁与宪法保持一致（禁止直达拒稿）。

## Project Structure

### Documentation (this feature)

```text
specs/041-final-decision-workspace/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/v1/editor.py
│   ├── models/decision.py
│   └── services/decision_service.py
└── tests/
    ├── integration/
    └── unit/

frontend/
├── src/
│   ├── app/(admin)/editor/decision/[id]/page.tsx
│   ├── components/editor/decision/
│   ├── lib/decision-utils.ts
│   └── services/editorService.ts
└── tests/
```

## Complexity Tracking

无额外宪法豁免项，按现有架构实现。
