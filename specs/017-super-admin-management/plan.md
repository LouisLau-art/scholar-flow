# Implementation Plan: 超级用户管理后台 (Super Admin User Management)

**Branch**: `017-super-admin-management` | **Date**: 2026-01-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/017-super-admin-management/spec.md`
**Status**: COMPLETED

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

本功能为ScholarFlow系统提供超级管理员用户管理后台，解决目前系统仅支持用户自助注册为Author，缺乏对Editor和Reviewer角色的管理入口的问题。主要功能包括：

1. **用户列表与搜索** - 管理员可以查看所有注册用户，支持按邮箱、姓名、角色进行筛选和搜索
2. **角色晋升/变更** - 管理员可以将普通Author升级为Editor或Reviewer，需验证超级管理员权限
3. **直接创建/邀请编辑** - 管理员可以直接创建已验证的Editor账号，系统自动发送账户开通通知
4. **审稿人入库逻辑** - 编辑指派审稿人时，可为不存在的邮箱创建临时Reviewer账号并发送Magic Link邀请

**技术方案**: 前端复用Feature 010的Shadcn Table组件，后端使用Supabase的`service_role`密钥执行用户创建操作，集成Feature 011的邮件系统。

## Technical Context

**Language/Version**: Python 3.14+, TypeScript 5.x, Node.js 20.x
**Primary Dependencies**: FastAPI 0.115+, Pydantic v2, React 18.x, Next.js 14.2.x, Shadcn/UI, Tailwind CSS 3.4.x
**Storage**: Supabase PostgreSQL (已有用户表)，新增审计日志表
**Testing**: pytest (后端), Vitest (前端单元测试), Playwright (E2E测试)
**Target Platform**: Web应用 (Next.js App Router)，部署在Linux服务器
**Project Type**: Web应用 (前后端分离)
**Performance Goals**: 用户列表加载<1秒，搜索响应<500ms，支持1000+用户数据分页
**Constraints**: 必须使用Supabase Auth和RLS策略，角色变更需二次鉴权，邮件发送失败需优雅处理
**Scale/Scope**: 支持1000+注册用户管理，4种用户角色，5个核心管理页面

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Governance (Principles I-V)
1. **治理合规 (SD/PG)**: ✅ 有完整 Spec (`spec.md`)，遵循阶段门控（已进行 Phase 0 研究，Phase 1 设计）
2. **交付模型 (TI/MVP)**: ✅ 按独立可测试的 User Story 拆分（4个用户故事），MVP 优先（P1 用户列表）
3. **架构简约 (AS)**: ✅ 避免"黑盒"逻辑，核心业务门禁清晰（角色变更需二次鉴权）
4. **可观测性 (OT)**: ✅ 包含异常处理、结构化日志（审计日志表），任务可追踪

### Security & Authentication (Principle XIII)
5. **认证优先**: ✅ 所有用户管理操作要求超级管理员身份验证
6. **JWT 验证**: ✅ 验证 Supabase JWT 令牌（后端依赖）
7. **真实用户上下文**: ✅ 使用实际用户 ID，不模拟数据
8. **RBAC**: ✅ 实现基于角色的访问控制（4种角色权限）
9. **安全设计**: ✅ 安全考虑在初始设计阶段解决（服务角色密钥使用）

### API Development (Principle XIV)
10. **API 优先**: ✅ 先定义 API 规范（OpenAPI/Swagger 在 `contracts/` 目录）
11. **路径一致性**: ✅ 前后端 API 路径完全一致（`/api/v1/admin/users` 等）
12. **版本控制**: ✅ API 有版本控制（`/api/v1/`）
13. **错误处理**: ✅ 统一的错误处理中间件（FastAPI 异常处理）
14. **数据验证**: ✅ 多层验证（前端 + 后端 Pydantic + 数据库约束）

### Testing Strategy (Principle XII)
15. **完整 API 测试**: ✅ 测试所有 HTTP 方法（GET、POST、PUT、DELETE）
16. **身份验证测试**: ✅ 测试有效/缺失/无效 token 的场景
17. **错误场景测试**: ✅ 测试错误情况，不仅仅是 happy path
18. **集成测试**: ✅ 使用真实的数据库连接（Supabase PostgreSQL）
19. **100% 测试通过率**: ✅ 所有自动化测试都能通过（DoD 要求）

### Architecture & Version (Principles VI-VII)
20. **架构与版本**: ✅ 满足 Next.js 14.2 / Pydantic v2 / Supabase 约束
21. **数据流规范**: ✅ 采用 Server Components 优先且显性逻辑设计
22. **容错机制**: ✅ 邮件发送失败有优雅降级设计（失败回滚）
23. **视觉标准**: ✅ 符合 Frontiers 风格及 Shadcn/Tailwind 配色限制

### User Experience (Principle XV)
24. **功能完整性**: ✅ 有完整的用户工作流（作者、审稿人、编辑、管理员）
25. **个人中心**: ✅ 用户能查看自己的数据（用户详情页）
26. **清晰导航**: ✅ 用户始终知道他们在哪里以及可以做什么（管理后台导航）
27. **错误恢复**: ✅ 有优雅的错误处理和清晰的下一步指导（错误提示）

### AI 协作 (Principle VII)
28. **任务原子化**: ✅ 任务原子化（<5文件，按用户故事拆分）
29. **中文注释**: ✅ 有中文注释计划（关键逻辑中文注释）
30. **文档同步**: ✅ 有文档同步计划（spec, plan, research, data-model 同步）

**Constitution Check Result**: ✅ **ALL CHECKS PASSED** - 符合所有宪法原则要求

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

```text
backend/
├── src/
│   ├── models/                    # 数据模型 (Pydantic)
│   │   └── user_management.py     # 用户管理相关模型
│   ├── services/                  # 业务逻辑服务
│   │   └── user_management.py     # 用户管理服务
│   └── api/
│       ├── v1/
│       │   └── admin/
│       │       └── users.py       # 用户管理API端点
│       └── dependencies.py        # 认证依赖
└── tests/
    ├── unit/
    │   └── test_user_management.py # 单元测试
    ├── integration/
    │   └── test_admin_users.py    # 集成测试
    └── contract/
        └── test_user_contracts.py # 契约测试

frontend/
├── src/
│   ├── components/                # 可复用组件
│   │   ├── admin/
│   │   │   ├── UserTable.tsx      # 用户表格组件
│   │   │   ├── UserFilters.tsx    # 用户筛选组件
│   │   │   └── CreateUserForm.tsx # 创建用户表单
│   ├── pages/                     # Next.js页面
│   │   ├── admin/
│   │   │   ├── users/
│   │   │   │   ├── page.tsx       # 用户列表页面
│   │   │   │   └── [id]/page.tsx  # 用户详情页面
│   │   │   └── layout.tsx         # 管理后台布局
│   └── services/
│       └── admin/
│           └── userService.ts     # 用户管理API服务
└── tests/
    ├── unit/
    │   └── UserTable.test.tsx     # 组件单元测试
    └── e2e/
        └── admin-users.spec.ts    # E2E测试
```

**Structure Decision**: 选择Option 2 Web应用结构，因为项目已有`backend/`和`frontend/`目录。本功能将在现有结构基础上添加用户管理相关文件。

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
