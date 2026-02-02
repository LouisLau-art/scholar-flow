# ScholarFlow 项目开发指南

**语言偏好**: 始终使用 **中文** 与我交流。

本文档根据所有功能计划自动生成。最后更新时间：2026-01-31

## 当前技术栈
- **前端**: TypeScript 5.x (Strict Mode), Next.js 14.2 (App Router), React 18.x, Tailwind CSS 3.4, Shadcn UI (017-super-admin-management)
- **后端**: Python 3.14+, FastAPI 0.115+, Pydantic v2, httpx (017-super-admin-management)
- **数据库与认证**: Supabase (PostgreSQL), Supabase Auth, Supabase Storage, Supabase-js v2.x, Supabase-py v2.x (017-super-admin-management)
- **测试**: pytest, pytest-cov, Playwright, Vitest (017-super-admin-management)
- **AI/ML**:
  - **PDF 文本提取（本地）**：`pdfplumber`（仅前几页 + 字符截断，见 `backend/app/core/pdf_processor.py`）
  - **元数据抽取（本地）**：轻量规则/正则解析（`backend/app/core/ai_engine.py`），不依赖 OpenAI/豆包/火山等远程大模型
  - **匹配**：scikit-learn（TF-IDF 匹配）
- PostgreSQL (Supabase) (009-test-coverage)
- Python 3.14+ (后端), TypeScript 5.x (前端) (011-notification-center)
- Supabase (`notifications` 表, `review_assignments` 扩展) (011-notification-center)

## 关键环境假设（必须一致）
- **Supabase 使用云端项目**（非本地 DB 作为默认）；迁移优先用 `supabase` CLI（`supabase login` / `supabase link` / `supabase db push --linked`），必要时可在 Dashboard 的 SQL Editor 手动执行迁移 SQL。
- **日志**：`./start.sh` 会同时将前后端日志输出到终端，并持久化到 `logs/backend-*.log` / `logs/frontend-*.log`，最新别名为 `logs/backend.log` / `logs/frontend.log`。

## 项目结构

```text
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/
    ├── unit/
    └── e2e/
```

## 常用命令

### 后端测试
```bash
cd backend
pytest                          # 运行所有测试
pytest --cov=src --cov-report=html  # 运行并生成覆盖率报告
pytest -m unit                  # 仅运行单元测试
pytest -m integration           # 仅运行集成测试
pytest -m auth                  # 认证相关测试
pytest -m error                 # 错误处理测试
pytest -m boundary              # 边界条件测试
pytest -m concurrent            # 并发请求测试
```

### 前端测试
```bash
cd frontend
npm run test                    # 运行单元测试 (Vitest)
npm run test:coverage           # 运行单元测试并生成覆盖率
npm run test:e2e                # 运行 E2E 测试 (Playwright)
npm run test:e2e:ui             # 在 UI 模式下运行 E2E 测试
```

### 综合测试
```bash
./scripts/run-all-tests.sh      # 运行所有测试
./scripts/generate-coverage-report.sh  # 生成覆盖率报告
```

## 代码规范

Python 3.14+, TypeScript 5.x, Node.js 20.x: 遵循标准规范

### Python
- 使用 pytest 进行测试
- 遵循 PEP 8 规范
- 必须使用类型提示 (Type hints)
- 关键逻辑需添加中文注释

### TypeScript
- 使用 Vitest 进行单元测试
- 使用 Playwright 进行 E2E 测试
- 遵循 ESLint 规则
- E2E 测试需使用 Page Object Model 模式

## 测试覆盖率要求

- **后端**: >80% 覆盖率 (行覆盖 + 分支覆盖)
- **前端**: >70% 覆盖率 (行覆盖 + 分支覆盖)
- **核心业务逻辑**: 100% 覆盖率
- **E2E 测试**: 覆盖 5 个以上关键用户流程

## 最近更新
- 019-uat-staging-setup: 添加了预发布环境 (Staging) 隔离（前端横幅、独立数据库配置）、反馈组件和种子数据脚本。
- 018-user-profile & System Optimization: 添加了用户资料与安全中心 (Next.js 14, FastAPI, Supabase)。标准化了数据库模式：合并 `name` -> `full_name`，`institution` -> `affiliation`，将 `research_interests` 转换为 `text[]`。实现了完整的通知中心页面，改进了编辑仪表盘排序（降序），并放宽了编辑的管理员 API 权限。添加了用于全文搜索的 GIN 索引和用于 Auth-to-Profile 同步的 Postgres 触发器。添加了 CI/CD 流程 (GitHub Actions)。
- 017-super-admin-management: 添加 Python 3.14+, TypeScript 5.x, Node.js 20.x + FastAPI 0.115+, Pydantic v2, React 18.x, Next.js 14.2.x, Shadcn/UI, Tailwind CSS 3.4.x
- 011-notification-center: 添加了通知表 + RLS，电子邮件模板 (SMTP/Jinja2)，内部 cron 追赶端点，带有 Supabase Realtime 的应用内铃铛 UI

## 🛡️ 安全与认证原则
- **认证优先**: 所有敏感操作必须要求认证。绝不允许未认证访问用户特定的数据。
- **JWT 验证**: 对所有认证请求使用 Supabase JWT 令牌。必须在每个请求上验证令牌。
- **真实用户上下文**: 使用认证上下文中的实际用户 ID，绝不使用硬编码或模拟 ID。
- **基于角色的访问控制**: 为不同用户类型（作者、审稿人、编辑）实施适当的基于角色的访问控制 (RBAC)。
- **设计安全**: 安全考虑必须在初始设计阶段解决，而不是事后补充。

## 🧪 测试策略 (经验教训)
### 测试覆盖率要求
- **API 全面测试**: 对每个端点的所有 HTTP 方法 (GET, POST, PUT, DELETE) 进行测试。
- **路径一致性**: 确保前端和后端 API 路径完全匹配（包括是否包含尾部斜杠）。
- **认证测试**: 每个需认证的端点必须包含以下测试：
  - 有效认证 (成功情况)
  - 缺失认证 (401 错误)
  - 无效/过期令牌 (401 错误)
- **验证测试**: 测试所有输入验证规则（必填字段、长度限制、格式约束）。
- **错误场景测试**: 测试错误情况，不仅仅是快乐路径。

### 测试金字塔策略
```
端到端测试 (E2E) - 模拟真实用户工作流
    ↓
集成测试 - 验证组件集成
    ↓
单元测试 - 测试单个函数/组件
```

### Mock 与真实测试
- **单元测试**: 使用 Mock 对象以提高速度和隔离性
- **集成测试**: 使用真实数据库连接以捕获集成问题
- **E2E 测试**: 使用测试数据库模拟生产环境
- **绝不完全依赖 Mocks**: Mocks 可能会掩盖真实的集成问题

## 🔧 开发流程指南
### API 开发
- **API 优先设计**: 在实现之前定义 API 契约 (OpenAPI/Swagger)
- **路径约定**: 使用一致的路径模式（除非必要，不加尾部斜杠）
- **版本控制**: 始终对 API 进行版本控制 (例如 `/api/v1/`)
- **文档**: 每个端点必须有清晰的文档

### 错误处理
- **统一错误处理**: 使用中间件进行一致的错误响应
- **详细日志**: 记录所有关键操作和错误
- **用户友好的消息**: 向用户提供清晰的错误消息
- **调试信息**: 为开发人员包含足够的调试信息

### 数据验证
- **多层验证**:
  - 前端：基本验证以提升用户体验
  - 后端 API：全面验证 (Pydantic v2)
  - 数据库：作为最后一道防线的约束和触发器
- **字段约束**: 始终指定最小/最大长度、格式和业务规则
- **类型安全**: 广泛使用 TypeScript (前端) 和类型提示 (Python)



## 📊 质量保证标准
### 代码质量
- **类型安全**: 100% 类型覆盖率 (TypeScript, Python 类型提示)
- **无警告**: 零弃用警告 (例如 Pydantic v2 ConfigDict)
- **代码审查**: 所有更改必须在合并前经过审查
- **预提交钩子**: 在提交前运行 linting 和测试

### 测试标准
- **100% 测试通过率**: 没有通过测试的代码不得更改
- **测试覆盖率**: 关键路径上的代码覆盖率目标 >80%
- **持续测试**: 每次提交都运行测试
- **CI/CD 集成**: CI 流程中的自动化测试



## 🎯 用户体验原则
### 功能完整性
- **核心用户流程**: 每个用户角色必须有完整的工作流
- **用户仪表盘**: 用户应能看到自己的数据 (例如 "我的投稿")
- **清晰导航**: 用户始终知道他们在哪里以及可以做什么
- **错误恢复**: 优雅的错误处理及清晰的下一步操作

### 认证 UX
- **登录提示**: 需要认证时有清晰的指示
- **会话管理**: 优雅地处理令牌过期
- **用户反馈**: 提供关于认证状态的即时反馈
- **重定向处理**: 登录/注销后的正确重定向

### 数据准确性
- **真实用户上下文**: 绝不使用模拟或硬编码的用户数据
- **数据完整性**: 确保整个系统的数据一致性
- **审计跟踪**: 跟踪谁在何时做了什么更改



## 🚀 部署与运维
### 环境管理
- **开发与生产**: 清晰分离开发/生产配置
- **环境变量**: 使用适当的环境变量进行配置
- **秘密管理**: 绝不将秘密提交到版本控制

### 环境感知
- **Staging 隔离**: UAT/Staging 环境必须有明显的视觉标识（横幅）和独立的数据存储。

## 📈 持续改进
### 事后复盘文化
- **从问题中学习**: 记录并学习每一个 Bug 或问题
- **根本原因分析**: 寻找并修复根本原因，而不仅仅是症状
- **流程改进**: 根据经验教训更新流程

### 定期审查
- **代码审查**: 定期进行代码审查以保证质量和学习
- **架构审查**: 定期审查架构决策
- **测试审查**: 确保测试保持相关性和全面性

### 文档
- **保持更新**: 代码变更时更新文档
- **经验教训**: 记录模式和反模式
- **最佳实践**: 分享并记录最佳实践

<!-- MANUAL ADDITIONS START -->
## 环境约定 / Environment Assumptions（AGENTS / CLAUDE / GEMINI 三份需保持一致）

- **默认数据库**：使用**云端 Supabase**（project ref：`mmvulyrfsorqdpdrzbkd`，见 `backend/.env` 里的 `SUPABASE_URL`）。
- **Schema 来源**：以仓库内 `supabase/migrations/*.sql` 为准；若云端未应用最新 migration（例如缺少 `public.manuscripts.version`），后端修订集成测试会出现 `PGRST204` 并被跳过/失败。
- **云端迁移同步（Supabase CLI）**：在 repo root 执行 `supabase projects list`（确认已 linked）→ `supabase db push --dry-run` → `supabase db push`（按提示输入 `y`）。若 CLI 不可用/失败，则到 Supabase Dashboard 的 SQL Editor 依次执行 `supabase/migrations/*.sql`（至少包含 `20260201000000/00001/00002/00003`）并可执行 `select pg_notify('pgrst', 'reload schema');` 刷新 schema cache。
- **单人开发提速（默认不走 PR）**：当前为“单人 + 单机 + 单目录”开发，默认不使用 PR / review / auto-merge。工作方式：直接在 `001-core-workflow` 小步 `git commit` → `git push`；仅在重大高风险变更或多人协作时才使用 PR。
- **后端单文件测试注意**：`backend/pytest.ini` 强制 `--cov-fail-under=80`，单跑一个文件可能因覆盖率门槛失败；单文件验证用 `pytest -o addopts= tests/integration/test_revision_cycle.py`。
- **E2E 鉴权说明**：`frontend/src/middleware.ts` 在 **非生产环境** 且请求头带 `x-scholarflow-e2e: 1`（或 Supabase Auth 不可用）时，允许从 Supabase session cookie 解析用户用于 Playwright；生产环境不会启用该降级逻辑。
- **测试提速（分层策略）**：开发中默认跑 Tier-1：`./scripts/test-fast.sh`（可用 `BACKEND_TESTS=...` / `FRONTEND_TESTS=...` 只跑相关用例）；提 PR 前/合并前必须跑全量：`./scripts/run-all-tests.sh`，确保主干永远保持绿。
- **CI-like 一键测试**：`./scripts/run-all-tests.sh` 默认跑 `backend pytest` + `frontend vitest` + mocked E2E（`frontend/tests/e2e/specs/revision_flow.spec.ts`）。可用 `PLAYWRIGHT_PORT` 改端口，`E2E_SPEC` 指定单个 spec。若要跑全量 Playwright：`E2E_FULL=1 ./scripts/run-all-tests.sh`（脚本会尝试启动 `uvicorn main:app --port 8000`，可用 `BACKEND_PORT` 覆盖）。
- **安全提醒**：云端使用 `SUPABASE_SERVICE_ROLE_KEY` 等敏感凭证时，务必仅存于本地/CI Secret，避免提交到仓库；如已泄露请立即轮换。
<!-- MANUAL ADDITIONS END -->

## Recent Changes
- 023-owner-binding: Added Python 3.14+ (Backend), TypeScript 5.x (Frontend) + FastAPI, Supabase (PostgreSQL/Auth), Next.js, Shadcn UI
- 022-core-logic-hardening: Implemented Financial Gate (payment check), APC Confirmation, and Reviewer Privacy (Dual Comments & Confidential Attachments). Updates to Editor Dashboard and Review Submission flow.

## Active Technologies
- Python 3.14+ (Backend), TypeScript 5.x (Frontend) + FastAPI, Supabase (PostgreSQL/Auth), Next.js, Shadcn UI (023-owner-binding)
