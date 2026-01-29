# Implementation Plan: 完善测试覆盖

**Branch**: `009-test-coverage` | **Date**: 2026-01-29 | **Spec**: [specs/009-test-coverage/spec.md](specs/009-test-coverage/spec.md)
**Input**: Feature specification from `/specs/009-test-coverage/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

完善测试覆盖：增加更多测试场景（错误处理、边界条件、并发请求），添加前端E2E测试（使用Playwright），生成测试覆盖率报告。

**Primary Requirement**: 根据宪章原则XII，必须测试错误场景而不仅仅是happy path。当前仅有17个后端测试和2个前端测试，需要扩展到至少30个后端测试、5个E2E测试，并实现80%后端覆盖率和70%前端覆盖率。

**Technical Approach**:
- 后端：使用pytest增加错误处理、边界条件、并发请求测试
- 前端：使用Playwright添加端到端测试
- 覆盖率：使用coverage.py和Vitest coverage生成报告

## Technical Context

**Language/Version**: Python 3.14+, TypeScript 5.x, Node.js 20.x
**Primary Dependencies**: FastAPI 0.115+, Pydantic v2, pytest, Playwright, Vitest, Supabase-js v2.x, Supabase-py v2.x
**Storage**: PostgreSQL (Supabase)
**Testing**: pytest (backend), Playwright (E2E), Vitest (frontend unit)
**Target Platform**: Linux server (Arch Linux), Web browser (Chrome, Firefox, Safari)
**Project Type**: Web application (frontend + backend)
**Performance Goals**: Backend tests <5min, E2E tests <10min
**Constraints**: 100% test pass rate required before delivery
**Scale/Scope**: 30+ backend tests, 5+ E2E tests, 80% backend coverage, 70% frontend coverage

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Governance (Principles I-V)
1. **治理合规 (SD/PG)**: ✅ 有完整 Spec（spec.md），遵循阶段门控（0->1->2->3+）
2. **交付模型 (TI/MVP)**: ✅ 按独立可测试的 User Story 拆分（3个故事），MVP 优先
3. **架构简约 (AS)**: ✅ 避免"黑盒"逻辑，测试逻辑清晰可见
4. **可观测性 (OT)**: ✅ 包含异常处理、结构化日志，任务可追踪

### Security & Authentication (Principle XIII)
5. **认证优先**: ✅ 所有敏感操作要求身份验证（JWT测试）
6. **JWT 验证**: ✅ 测试有效/缺失/无效/过期JWT令牌
7. **真实用户上下文**: ✅ 使用真实用户ID进行测试
8. **RBAC**: ✅ 测试基于角色的访问控制（作者、编辑）
9. **安全设计**: ✅ 安全考虑在测试设计阶段就已解决

### API Development (Principle XIV)
10. **API 优先**: ✅ 已定义API规范（OpenAPI/Swagger）
11. **路径一致性**: ✅ 确保前后端API路径完全一致
12. **版本控制**: ✅ API使用版本控制（/api/v1/）
13. **错误处理**: ✅ 测试统一的错误处理中间件
14. **数据验证**: ✅ 测试多层验证（前端 + 后端 + 数据库）

### Testing Strategy (Principle XII)
15. **完整 API 测试**: ✅ 测试所有HTTP方法（GET、POST、PUT、DELETE）
16. **身份验证测试**: ✅ 测试有效/缺失/无效token的场景
17. **错误场景测试**: ✅ 测试错误情况，不仅仅是happy path
18. **集成测试**: ✅ 使用真实的数据库连接（而非仅Mock）
19. **100% 测试通过率**: ✅ 所有自动化测试必须100%通过

### Architecture & Version (Principles VI-VII)
20. **架构与版本**: ✅ 满足Next.js 14.2 / Pydantic v2 / Supabase约束
21. **数据流规范**: ✅ 采用Server Components优先且显性逻辑设计
22. **容错机制**: ✅ 测试并发请求、网络中断等异常场景
23. **视觉标准**: ✅ 符合Frontiers风格及Shadcn/Tailwind配色限制

### User Experience (Principle XV)
24. **功能完整性**: ✅ 测试完整用户工作流（作者提交、编辑分配、审稿人查看）
25. **个人中心**: ✅ 测试用户查看自己数据的场景
26. **清晰导航**: ✅ 测试用户导航和状态反馈
27. **错误恢复**: ✅ 测试优雅的错误处理和清晰的下一步指导

### AI 协作 (Principle VII)
28. **任务原子化**: ✅ 任务原子化（<5文件），每个测试独立
29. **中文注释**: ✅ 测试代码包含中文注释
30. **文档同步**: ✅ 文档与代码同步更新

## Project Structure

### Documentation (this feature)

```text
specs/009-test-coverage/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/
    ├── contract/        # Contract tests for API endpoints
    ├── integration/     # Integration tests with real database
    └── unit/            # Unit tests for individual functions

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/
    ├── unit/            # Vitest unit tests
    └── e2e/             # Playwright E2E tests

scripts/
└── coverage/            # Coverage report generation scripts
```

**Structure Decision**: Web application (frontend + backend) - Option 2
- Backend tests: `backend/tests/` (pytest)
- Frontend unit tests: `frontend/tests/unit/` (Vitest)
- Frontend E2E tests: `frontend/tests/e2e/` (Playwright)
- Coverage reports: Generated in project root

## Phase 0: Research

### Research Topics

1. **Playwright vs Cypress for Next.js E2E Testing**
   - Decision: Use Playwright
   - Rationale: Better cross-browser support, TypeScript-first, faster execution
   - Alternatives: Cypress (simpler API but limited browser support)

2. **pytest Coverage Configuration**
   - Decision: Use pytest-cov with 80% threshold
   - Rationale: Industry standard, integrates well with pytest
   - Configuration: `.coveragerc` with branch coverage enabled

3. **Playwright Test Organization**
   - Decision: Use Page Object Model pattern
   - Rationale: Maintainable, reusable, follows best practices
   - Structure: `tests/e2e/pages/` for page objects, `tests/e2e/specs/` for tests

4. **Database Test Isolation**
   - Decision: Use transaction rollback for each test
   - Rationale: Fast, isolated, no cleanup needed
   - Implementation: pytest fixtures with Supabase transactions

5. **JWT Test Token Generation**
   - Decision: Generate real JWT tokens using Supabase secret
   - Rationale: Tests actual token validation, not mocks
   - Implementation: Use `supabase.auth.sign_in_with_password()` for real tokens

### Research Output

**Output**: research.md with all decisions documented

## Technical Decisions

### 1. Testing Framework Selection
- **后端测试**: 使用 pytest（项目现有标准）
  - 优势：成熟稳定，与FastAPI集成良好
  - 覆盖：单元测试、集成测试、API端点测试

- **前端E2E测试**: 使用 Playwright（已澄清）
  - 优势：更好的跨浏览器支持（Chrome, Firefox, Safari），更适合TypeScript/Next.js
  - 替代方案：Cypress（未选择，浏览器支持较弱）

- **前端单元测试**: 使用 Vitest（项目现有标准）
  - 优势：与Vite集成，速度快，API与Jest兼容

### 2. 测试策略
- **测试金字塔**:
  ```
  E2E测试 (5+个) - 模拟真实用户工作流
      ↓
  集成测试 (10+个) - 使用真实数据库
      ↓
  单元测试 (15+个) - 测试单个函数/组件
  ```

- **覆盖率目标**:
  - 后端：>80%（行覆盖率、分支覆盖率）
  - 前端：>70%（行覆盖率、分支覆盖率）
  - 关键业务逻辑：100%

### 3. 数据库测试
- **真实连接**: 集成测试必须使用真实数据库连接（Supabase）
- **测试数据**: 使用独立的测试数据库，避免污染生产数据
- **清理策略**: 每个测试后清理测试数据

### 4. 安全测试
- **JWT测试**: 测试有效、缺失、无效、过期令牌
- **RBAC测试**: 测试不同用户角色的权限控制
- **边界测试**: 测试并发请求、数据一致性

## Quality Assurance (QA Suite)

### Test Requirements (Principle XII)
- **QA 刚性要求**: 本Feature包含完整的自动化测试（Backend Pytest, Frontend Playwright/Vitest）。DoD包含测试全通过报告。
- **完整 API 测试**: 测试所有HTTP方法（GET、POST、PUT、DELETE）对每个端点。
- **路径一致性测试**: 确保前端和后端API路径完全一致（包括尾部斜杠处理）。
- **身份验证测试**: 每个需要身份验证的端点测试有效身份验证、缺少身份验证、无效/过期令牌。
- **验证测试**: 测试所有输入验证规则（必填字段、长度限制、格式约束）。
- **错误场景测试**: 测试错误情况，不仅仅是happy path。
- **集成测试**: 使用真实的数据库连接以捕获集成问题。
- **覆盖率目标**: 后端>80%，前端>70%，关键业务逻辑100%。

### Security Requirements (Principle XIII)
- **认证优先**: 所有敏感操作必须要求身份验证。
- **JWT 验证**: 所有经过身份验证的请求必须使用Supabase JWT令牌。
- **真实用户上下文**: 使用来自身份验证上下文的实际用户ID。
- **RBAC**: 为不同的用户类型（作者、审稿人、编辑）实现适当的角色权限控制。

### API Development Requirements (Principle XIV)
- **API 优先设计**: 在实现之前定义API规范（OpenAPI/Swagger）。
- **路径约定**: 使用一致的路径模式（除非必要，否则不使用尾部斜杠）。
- **版本控制**: 始终对API进行版本控制（例如 `/api/v1/`）。
- **错误处理**: 使用中间件实现一致的错误响应。
- **数据验证**: 多层验证（前端基本验证 + 后端全面验证 + 数据库约束）。

### User Experience Requirements (Principle XV)
- **角色完整**: 每个用户角色必须有完整的工作流程。
- **个人中心**: 用户应该能够查看自己的数据（例如"我的稿件"）。
- **清晰导航**: 用户始终知道他们在哪里以及可以做什么。
- **错误恢复**: 优雅的错误处理和清晰的下一步指导。
