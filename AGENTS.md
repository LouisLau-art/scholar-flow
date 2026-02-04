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
  - **元数据抽取（本地）**：优先用 PDF 版面信息（字号/位置）+ 轻量规则/正则（`backend/app/core/ai_engine.py`），不依赖 OpenAI/豆包/火山等远程大模型（可用 `PDF_LAYOUT_MAX_PAGES` / `PDF_LAYOUT_MAX_LINES` 调整版面扫描范围）
  - **匹配**：scikit-learn（TF-IDF 匹配）
- PostgreSQL (Supabase) (009-test-coverage)
- Python 3.14+ (后端), TypeScript 5.x (前端) (011-notification-center)
- Supabase (`notifications` 表, `review_assignments` 扩展) (011-notification-center)

## 关键环境假设（必须一致）
- **Supabase 使用云端项目**（非本地 DB 作为默认）；迁移优先用 `supabase` CLI（`supabase login` / `supabase link` / `supabase db push --linked`），必要时可在 Dashboard 的 SQL Editor 手动执行迁移 SQL。
- **环境变量与密钥**：真实密钥只放本地/CI/平台 Secrets；仓库只保留模板（`.env.example` / `backend/.env.example` / `frontend/.env.local.example`），严禁提交 `SUPABASE_SERVICE_ROLE_KEY` 等敏感信息。
- **日志**：`./start.sh` 会同时将前后端日志输出到终端，并持久化到 `logs/backend-*.log` / `logs/frontend-*.log`，最新别名为 `logs/backend.log` / `logs/frontend.log`。
- **AI 推荐模型缓存（本地 CPU）**：Matchmaking 使用 `sentence-transformers`（本地推理），首次可能从 Hugging Face 下载模型；`./start.sh` 默认将缓存放到 `./.cache/` 以便“下载一次后复用”，并默认设置 `HF_ENDPOINT=https://hf-mirror.com`（如需改回官方源可在环境变量里覆盖）。当本地已存在模型缓存时，`./start.sh` 会自动设置 `MATCHMAKING_LOCAL_FILES_ONLY=1`，彻底避免每次重启都发起 HF 网络请求。
- **公开文章 PDF 预览**：`/articles/[id]` 不依赖前端直连 Storage（匿名会 400/权限不一致），统一走后端 `GET /api/v1/manuscripts/articles/{id}/pdf-signed` 返回 `signed_url`；同时 `GET /api/v1/manuscripts/articles/{id}` 仅返回 `status='published'` 的稿件。
- **部署架构（Vercel + Hugging Face Spaces）**：
  - **Frontend**: 部署于 **Vercel**。需设置 `NEXT_PUBLIC_API_URL` 指向 HF Space 地址（无尾部斜杠）。
  - **Backend**: 部署于 **Hugging Face Spaces (Docker)**。
    - **Docker策略**: 使用项目根目录 `Dockerfile`（基于 `python:3.14-slim`, 包含 `build-essential` 用于编译 `pyroaring`, 强制使用非 root 用户 `user:1000`）。
    - **环境变量**: 在 HF Settings 填入 `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `FRONTEND_ORIGIN` (Vercel 域名)。
    - **CI/CD**: GitHub Actions (`.github/workflows/deploy-hf.yml`) 监听 `main` 分支，自动同步 `backend/` 和 `Dockerfile` 到 HF Space（需配置 GitHub Secret `HF_TOKEN`）。
  - **Legacy**: Render/Railway/Zeabur 方案已降级为备选，相关配置文件 (`deploy/*.env`) 仍保留供参考。
- **Sentry（Feature 027，全栈监控）**：
  - **Frontend**：`@sentry/nextjs`（`frontend/sentry.client.config.ts` / `frontend/sentry.server.config.ts` / `frontend/sentry.edge.config.ts`），UAT 阶段 `replaysSessionSampleRate=1.0`、`tracesSampleRate=1.0`。
  - **Sourcemaps**：Vercel 构建环境需设置 `SENTRY_AUTH_TOKEN` / `SENTRY_ORG` / `SENTRY_PROJECT`；缺失时仍可上报事件（DSN），但不会上传 sourcemaps。
  - **Backend**：`sentry-sdk` 在 `backend/main.py` 初始化并启用 `SqlalchemyIntegration`；隐私策略为“永不上传请求体”（PDF/密码）且初始化失败不阻塞启动（零崩溃原则）。
  - **自测入口**：后端 `GET /api/v1/internal/sentry/test-error`（需 `ADMIN_API_KEY`）；前端 `/admin/sentry-test`。
- **Invoice PDF（Feature 026）**：后端需配置 `INVOICE_PAYMENT_INSTRUCTIONS` / `INVOICE_SIGNED_URL_EXPIRES_IN`，并确保云端已应用 `supabase/migrations/20260204120000_invoice_pdf_fields.sql` 与 `supabase/migrations/20260204121000_invoices_bucket.sql`。
- **MVP 状态机与财务门禁（重要约定）**：
  - **Reject 终态**：拒稿使用 `status='rejected'`（不再使用历史遗留的 `revision_required`）。
  - **修回等待**：需要作者修回使用 `status='revision_requested'`（作者在 `/submit-revision/[id]` 提交后进入 `resubmitted`）。
  - **录用与门禁**：录用进入 `approved` 并创建/更新 `invoices`；**Publish 必须通过 Payment Gate**（`amount>0` 且 `status!=paid` 时禁止发布）。
  - **账单 PDF（Feature 026）**：录用后生成并持久化 Invoice PDF（WeasyPrint + Storage `invoices`），回填 `invoices.pdf_path` 供作者/编辑下载。
  - **Production Gate（可选）**：为提速 MVP，`final_pdf_path` 门禁默认关闭；如需强制 Production Final PDF，设置 `PRODUCTION_GATE_ENABLED=1`（启用后 `final_pdf_path` 为空将禁止发布；云端可执行 `supabase/migrations/20260203143000_post_acceptance_pipeline.sql` 补齐字段）。
  - **人工确认到账（MVP）**：Editor 在 Pipeline 的 Approved 卡片上可点 `Mark Paid`，调用 `POST /api/v1/editor/invoices/confirm` 把 invoice 标记为 `paid` 后才能发布。
  - **云端数据清理**：若云端存在 `status='revision_required'` 的旧数据，需要在 Supabase Dashboard 的 SQL Editor 执行 `supabase/migrations/20260203120000_status_cleanup.sql`（或直接跑其中的 `update public.manuscripts ...`）以迁移到 `rejected`。

## MVP 已砍/延期清单（提速约束，三份文档需一致）
- **Magic Link（生产级）**：MVP 不做稳定化；本地默认用 reviewer token 页面 + `dev-login` 测试。
- **全量 RLS**：MVP 主要靠后端鉴权 + `service_role`；不强制把 `manuscripts/review_assignments/review_reports` 的 RLS 全补齐（但前端严禁持有 `service_role key`）。
- **DOI/Crossref 真对接**：保留 schema/占位即可，不做真实注册与异步任务闭环。
- **查重**：默认关闭（`PLAGIARISM_CHECK_ENABLED=0`），不进入关键链路。
- **Finance 页面**：仅作 UI 演示/占位；MVP 的财务入口在 Editor Pipeline 的 `approved` 卡片（`Mark Paid` + Payment Gate）。Finance 页不与云端 `invoices` 同步。
- **通知群发**：MVP 禁止给所有 editor/admin 群发通知（会引发云端 mock 用户导致的 409 日志刷屏）；仅通知 `owner_id/editor_id` 或作者本人。
- **修订 Response Letter 图片上传**：MVP 不做上传到 Storage；改为前端压缩后以 Data URL 内嵌（有体积限制）。

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
- **Feature 024 迁移（可选）**：若要启用 Production Gate（强制 `final_pdf_path`），云端 `public.manuscripts` 需包含 `final_pdf_path`（建议执行 `supabase/migrations/20260203143000_post_acceptance_pipeline.sql`）；若不启用 Production Gate，可先不做该迁移，发布会自动降级为仅 Payment Gate。
- **单人开发提速（默认不走 PR）**：当前为“单人 + 单机 + 单目录”开发，默认不使用 PR / review / auto-merge。工作方式：**直接在 `main` 小步 `git commit` → `git push`**（把 GitHub 当作备份与回滚点）；仅在重大高风险改动或多人协作时才开短期 feature 分支并合回 `main`。
- **后端单文件测试注意**：`backend/pytest.ini` 强制 `--cov-fail-under=80`，单跑一个文件可能因覆盖率门槛失败；单文件验证用 `pytest -o addopts= tests/integration/test_revision_cycle.py`。
- **E2E 鉴权说明**：`frontend/src/middleware.ts` 在 **非生产环境** 且请求头带 `x-scholarflow-e2e: 1`（或 Supabase Auth 不可用）时，允许从 Supabase session cookie 解析用户用于 Playwright；生产环境不会启用该降级逻辑。
- **测试提速（分层策略）**：开发中默认跑 Tier-1：`./scripts/test-fast.sh`（可用 `BACKEND_TESTS=...` / `FRONTEND_TESTS=...` 只跑相关用例）；提 PR 前/合并前必须跑全量：`./scripts/run-all-tests.sh`，确保主干永远保持绿。
- **CI-like 一键测试**：`./scripts/run-all-tests.sh` 默认跑 `backend pytest` + `frontend vitest` + mocked E2E（`frontend/tests/e2e/specs/revision_flow.spec.ts`）。可用 `PLAYWRIGHT_PORT` 改端口，`E2E_SPEC` 指定单个 spec。若要跑全量 Playwright：`E2E_FULL=1 ./scripts/run-all-tests.sh`（脚本会尝试启动 `uvicorn main:app --port 8000`，可用 `BACKEND_PORT` 覆盖）。
- **安全提醒**：云端使用 `SUPABASE_SERVICE_ROLE_KEY` 等敏感凭证时，务必仅存于本地/CI Secret，避免提交到仓库；如已泄露请立即轮换。

## 近期关键修复快照（2026-02-03）
- **Analytics 登录态**：修复 `/editor/analytics` 误判“未登录”（API 统一使用 `createBrowserClient`，可读 cookie session）。
- **Analytics 导出按钮**：Excel/CSV 不再同时显示“导出中...”，改为“按格式单独 loading 文案 + 全局禁用避免并发导出”。
- **Reviewer 修回上下文**：审稿弹窗展示作者修回材料（Response Letter/内嵌图片），并补齐审稿附件下载入口。
- **权限收紧**：`GET /api/v1/manuscripts/{id}/versions` 对 reviewer 增加“必须被分配该稿件”的校验，避免越权读取版本历史。
- **Feature 024（录用后出版流水线）**：新增 Production Final PDF 上传、发布门禁（Payment；Production Gate 可选）、作者账单下载、首页 Latest Articles published-only。
<!-- MANUAL ADDITIONS END -->

## Recent Changes
- 026-automated-invoice-pdf: Added Python 3.14+ + FastAPI, Pydantic v2, Supabase-py v2.x, Jinja2, WeasyPrint

## Active Technologies
- Supabase (PostgreSQL + Storage) (026-automated-invoice-pdf)
