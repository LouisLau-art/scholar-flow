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

### Core Governance (Principles I-V)
1. **治理合规 (SD/PG)**: 是否有完整 Spec？是否遵循了阶段门控（0->1->2->3+）？
2. **交付模型 (TI/MVP)**: 是否按独立可测试的 User Story 拆分？是否 MVP 优先？
3. **架构简约 (AS)**: 是否避免了"黑盒"逻辑？核心业务门禁是否清晰可见？
4. **可观测性 (OT)**: 是否包含异常处理、结构化日志？任务是否可追踪？

### Security & Authentication (Principle XIII)
5. **认证优先**: 所有敏感操作是否要求身份验证？
6. **JWT 验证**: 是否验证 Supabase JWT 令牌？
7. **真实用户上下文**: 是否使用实际用户 ID，而非模拟数据？
8. **RBAC**: 是否实现了基于角色的访问控制？
9. **安全设计**: 安全考虑是否在初始设计阶段就已解决？

### API Development (Principle XIV)
10. **API 优先**: 是否先定义了 API 规范（OpenAPI/Swagger）？
11. **路径一致性**: 前后端 API 路径是否完全一致（无尾部斜杠）？
12. **版本控制**: API 是否有版本控制（如 `/api/v1/`）？
13. **错误处理**: 是否有统一的错误处理中间件？
14. **数据验证**: 是否有多层验证（前端 + 后端 + 数据库）？

### Testing Strategy (Principle XII)
15. **完整 API 测试**: 是否测试了所有 HTTP 方法（GET、POST、PUT、DELETE）？
16. **身份验证测试**: 是否测试了有效/缺失/无效 token 的场景？
17. **错误场景测试**: 是否测试了错误情况，不仅仅是 happy path？
18. **集成测试**: 是否使用了真实的数据库连接（而非仅 Mock）？
19. **100% 测试通过率**: 所有自动化测试是否都能通过？

### Architecture & Version (Principles VI-VII)
20. **架构与版本**: 是否满足 Next.js 14.2 / Pydantic v2 / Supabase 约束？
21. **数据流规范**: 是否采用 Server Components 优先且显性逻辑设计？
22. **容错机制**: 财务操作是否有幂等性方案？是否有优雅降级设计？
23. **视觉标准**: 是否符合 Frontiers 风格及 Shadcn/Tailwind 配色限制？

### User Experience (Principle XV)
24. **功能完整性**: 是否有完整的用户工作流（作者、审稿人、编辑）？
25. **个人中心**: 用户是否能查看自己的数据（如"我的稿件"）？
26. **清晰导航**: 用户是否始终知道他们在哪里以及可以做什么？
27. **错误恢复**: 是否有优雅的错误处理和清晰的下一步指导？

### AI 协作 (Principle VII)
28. **任务原子化**: 任务是否原子化（<5文件）？
29. **中文注释**: 是否有中文注释计划？
30. **文档同步**: 是否有文档同步计划？

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

### Test Requirements (Principle XII)
- **QA 刚性要求**: 任何 Feature 必须包含对应的自动化测试（Backend Pytest, Frontend Vitest）。DoD 必须包含测试全通过截图/报告。
- **完整 API 测试**: 必须测试所有 HTTP 方法（GET、POST、PUT、DELETE）对每个端点。
- **路径一致性测试**: 确保前端和后端 API 路径完全一致（包括尾部斜杠处理）。
- **身份验证测试**: 每个需要身份验证的端点必须测试有效身份验证、缺少身份验证、无效/过期令牌。
- **验证测试**: 测试所有输入验证规则（必填字段、长度限制、格式约束）。
- **错误场景测试**: 必须测试错误情况，不仅仅是 happy path。
- **集成测试**: 必须使用真实的数据库连接以捕获集成问题。

### Security Requirements (Principle XIII)
- **认证优先**: 所有敏感操作必须要求身份验证。
- **JWT 验证**: 所有经过身份验证的请求必须使用 Supabase JWT 令牌。
- **真实用户上下文**: 使用来自身份验证上下文的实际用户 ID。
- **RBAC**: 为不同的用户类型（作者、审稿人、编辑）实现适当的角色权限控制。

### API Development Requirements (Principle XIV)
- **API 优先设计**: 在实现之前定义 API 规范（OpenAPI/Swagger）。
- **路径约定**: 使用一致的路径模式（除非必要，否则不使用尾部斜杠）。
- **版本控制**: 始终对 API 进行版本控制（例如 `/api/v1/`）。
- **错误处理**: 使用中间件实现一致的错误响应。
- **数据验证**: 多层验证（前端基本验证 + 后端全面验证 + 数据库约束）。

### User Experience Requirements (Principle XV)
- **角色完整**: 每个用户角色必须有完整的工作流程。
- **个人中心**: 用户应该能够查看自己的数据（例如"我的稿件"）。
- **清晰导航**: 用户始终知道他们在哪里以及可以做什么。
- **错误恢复**: 优雅的错误处理和清晰的下一步指导。
