# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [single/web/mobile - determines source structure]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **治理合规 (SD/PG)**: 是否有完整 Spec？是否遵循了阶段门控（0->1->2->3+）？
2. **交付模型 (TI/MVP)**: 是否按独立可测试的 User Story 拆分？是否 MVP 优先？
3. **架构与版本**: 是否满足 Next.js 14.2 / Pydantic v2 / Supabase 约束？
4. **数据流规范**: 是否采用 Server Components 优先且显性逻辑设计？
5. **容错机制**: 财务操作是否有幂等性方案？是否有优雅降级设计？
6. **视觉标准**: 是否符合 Frontiers 风格及 Shadcn/Tailwind 配色限制？
7. **AI 协作**: 任务是否原子化（<5文件）？是否有中文注释计划？

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
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
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Technical Decisions

### 1. Architecture & Routing
- **显性路由**: 必须在方法装饰器上定义完整路径（如 `/manuscripts/upload`），严禁过度依赖 APIRouter 的 prefix。
- **全栈切片**: 每一个交付单元必须包含 API、UI 及导航入口。

### 2. Dependencies & SDKs
- **原生优先**: 优先使用 Supabase 原生 `supabase-js`/`supabase-py`，严禁使用不稳定的第三方 Helper 库。
- **交互标准**: 严禁使用浏览器原生 `alert()`，必须统一使用 Shadcn/Sonner Toast。

## Quality Assurance (QA Suite)
- **QA 刚性要求**: 任何 Feature 必须包含对应的自动化测试（Backend Pytest, Frontend Vitest）。DoD 必须包含测试全通过截图/报告。
