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
  - **匹配**：轻量 TF‑IDF（纯 Python，无 sklearn 依赖）
- PostgreSQL (Supabase) (009-test-coverage)
- Python 3.14+ (后端), TypeScript 5.x (前端) (011-notification-center)
- Supabase (`notifications` 表, `review_assignments` 扩展) (011-notification-center)

## 关键环境假设（必须一致）
- **Supabase 使用云端项目**（非本地 DB 作为默认）；迁移优先用 `supabase` CLI（`supabase login` / `supabase link` / `supabase db push --linked`），必要时可在 Dashboard 的 SQL Editor 手动执行迁移 SQL。
- **环境变量与密钥**：真实密钥只放本地/CI/平台 Secrets；仓库只保留模板（`.env.example` / `backend/.env.example` / `frontend/.env.local.example`），严禁提交 `SUPABASE_SERVICE_ROLE_KEY` 等敏感信息。
- **包管理器统一**：前端统一使用 `bun`（替代 `pnpm/npm`），后端统一使用 `uv`（替代 `pip`）；脚本与 CI 均以 `bun run` + `uv pip` 为准。
- **日志**：`./start.sh` 会同时将前后端日志输出到终端，并持久化到 `logs/backend-*.log` / `logs/frontend-*.log`，最新别名为 `logs/backend.log` / `logs/frontend.log`。
- **AI 推荐模型（本地 CPU，部署友好）**：Matchmaking 默认使用纯 Python 的 hash-embedding（`backend/app/core/ml.py`），避免 `sentence-transformers/torch` 导致部署构建过慢或失败；如需更智能的语义匹配，可在“本地/专用环境”额外安装 `sentence-transformers`，系统会自动启用并可配置缓存（`HF_HOME` / `SENTENCE_TRANSFORMERS_HOME`，配合 `MATCHMAKING_LOCAL_FILES_ONLY=1` 强制离线）。`./start.sh` 仍会默认设置 `HF_ENDPOINT=https://hf-mirror.com`（可覆盖）。
- **公开文章 PDF 预览**：`/articles/[id]` 不依赖前端直连 Storage（匿名会 400/权限不一致），统一走后端 `GET /api/v1/manuscripts/articles/{id}/pdf-signed` 返回 `signed_url`；同时 `GET /api/v1/manuscripts/articles/{id}` 仅返回 `status='published'` 的稿件。
- **CMS HTML 渲染（Vercel 约束）**：`isomorphic-dompurify/jsdom` 在 Vercel Node 运行时可能触发 ESM/CJS 兼容崩溃（`ERR_REQUIRE_ESM`）。MVP 约定：`/journal/[slug]` 不在服务端引入 DOMPurify/jsdom，直接渲染后端返回的 HTML（内容仅内部人员维护）；若未来开放用户生成内容，再改为后端做安全清洗。
- **部署架构（Vercel + Hugging Face Spaces）**：
  - **Frontend**: 部署于 **Vercel**。需设置 `NEXT_PUBLIC_API_URL` 指向 HF Space 地址（无尾部斜杠）。
  - **Backend**: 部署于 **Hugging Face Spaces (Docker)**。
    - **Docker策略**: 使用项目根目录 `Dockerfile`（基于 `python:3.12-slim`，更利于依赖 wheels；本地开发仍使用 Python 3.14；容器内强制使用非 root 用户 `user:1000`）。
    - **环境变量**: 在 HF Settings 填入 `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `FRONTEND_ORIGIN` (Vercel 域名)。
    - **CI/CD**: GitHub Actions (`.github/workflows/deploy-hf.yml`) 监听 `main` 分支，自动同步 `backend/` 和 `Dockerfile` 到 HF Space（需配置 GitHub Secret `HF_TOKEN`）。
  - **Legacy**: Render/Railway/Zeabur 方案已降级为备选，相关配置文件 (`deploy/*.env`) 仍保留供参考。
- **Sentry（Feature 027，全栈监控）**：
  - **Frontend**：`@sentry/nextjs`（`frontend/sentry.client.config.ts` / `frontend/sentry.server.config.ts` / `frontend/sentry.edge.config.ts`），UAT 阶段 `replaysSessionSampleRate=1.0`、`tracesSampleRate=1.0`。
  - **Sourcemaps**：`frontend/next.config.mjs` **始终**包裹 `withSentryConfig`（保证 config 注入与事件上报可用）；若 Vercel 未配置 `SENTRY_AUTH_TOKEN` / `SENTRY_ORG` / `SENTRY_PROJECT`，则自动禁用 sourcemaps 上传（但 DSN 上报仍可用）。
  - **Backend**：`sentry-sdk` 在 `backend/main.py` 初始化；`SqlalchemyIntegration` **可选**（仅当环境安装了 `sqlalchemy` 才会自动启用）。为兼容 HF Space 可能存在的旧版 `sentry-sdk`，初始化会在遇到 `Unknown option`（如 `with_locals`/`max_request_body_size`）时自动降级重试。隐私策略为“永不上传请求体”（PDF/密码）且初始化失败不阻塞启动（零崩溃原则）。
  - **自测入口**：后端 `GET /api/v1/internal/sentry/test-error`（需 `ADMIN_API_KEY`）；前端 `/admin/sentry-test`。
- **Reviewer Magic Link（Feature 039）**：
  - 入口：`/review/invite?token=...`（Next Middleware 交换 token → 设置 httpOnly cookie → 跳转 `/review/assignment/[id]`）。
  - Cookie：`sf_review_magic`（JWT，绑定 `assignment_id` + `reviewer_id` + `manuscript_id` + scope）。
  - 后端：`POST /api/v1/auth/magic-link/verify`；Reviewer 免登录接口 `GET/POST /api/v1/reviews/magic/assignments/...`。
  - 密钥：必须设置 `MAGIC_LINK_JWT_SECRET`（严禁复用 `SUPABASE_SERVICE_ROLE_KEY`）。
- **Reviewer Workspace（Feature 040）**：
  - 前端路由：`/reviewer/workspace/[id]`（沉浸式双栏，最小头部，无全站 footer）。
  - 后端接口：`GET /api/v1/reviewer/assignments/{id}/workspace`、`POST /api/v1/reviewer/assignments/{id}/attachments`、`POST /api/v1/reviewer/assignments/{id}/submit`。
  - 安全策略：所有接口必须通过 `sf_review_magic` scope 校验，并严格校验 `assignment_id` 与 `reviewer_id` 归属关系。
- **Invoice PDF（Feature 026）**：后端需配置 `INVOICE_PAYMENT_INSTRUCTIONS` / `INVOICE_SIGNED_URL_EXPIRES_IN`，并确保云端已应用 `supabase/migrations/20260204120000_invoice_pdf_fields.sql` 与 `supabase/migrations/20260204121000_invoices_bucket.sql`。
- **MVP 状态机与财务门禁（重要约定）**：
  - **Reject 终态**：拒稿使用 `status='rejected'`（不再使用历史遗留的 `revision_required`）。
  - **修回等待**：需要作者修回使用 `status='revision_requested'`（作者在 `/submit-revision/[id]` 提交后进入 `resubmitted`）。
  - **录用与门禁**：录用进入 `approved` 并创建/更新 `invoices`；**Publish 必须通过 Payment Gate**（`amount>0` 且 `status!=paid` 时禁止发布）。
  - **账单 PDF（Feature 026）**：录用后生成并持久化 Invoice PDF（WeasyPrint + Storage `invoices`），回填 `invoices.pdf_path` 供作者/编辑下载。
  - **Production Gate（可选）**：为提速 MVP，`final_pdf_path` 门禁默认关闭；如需强制 Production Final PDF，设置 `PRODUCTION_GATE_ENABLED=1`（启用后 `final_pdf_path` 为空将禁止发布；云端可执行 `supabase/migrations/20260203143000_post_acceptance_pipeline.sql` 补齐字段）。
  - **人工确认到账（MVP）**：Editor 在稿件详情页 `/editor/manuscript/[id]` 的 Production 卡片上可点 `Mark Paid`，调用 `POST /api/v1/editor/invoices/confirm` 把 invoice 标记为 `paid` 后才能发布。
  - **云端数据清理**：若云端存在 `status='revision_required'` 的旧数据，需要在 Supabase Dashboard 的 SQL Editor 执行 `supabase/migrations/20260203120000_status_cleanup.sql`（或直接跑其中的 `update public.manuscripts ...`）以迁移到 `rejected`。

## MVP 已砍/延期清单（提速约束，三份文档需一致）
- **Magic Link（Supabase Session 版，生产级）**：仍延期（本地/多环境下不稳定，排查成本高）。
- **Reviewer Magic Link（MVP 版）**：已实现 **JWT Magic Link**（无 Supabase session，走 httpOnly cookie + 后端 scope 校验），用于 UAT/MVP 的“免登录审稿”闭环。
- **全量 RLS**：MVP 主要靠后端鉴权 + `service_role`；不强制把 `manuscripts/review_assignments/review_reports` 的 RLS 全补齐（但前端严禁持有 `service_role key`）。
- **DOI/Crossref 真对接**：保留 schema/占位即可，不做真实注册与异步任务闭环。
- **查重**：默认关闭（`PLAGIARISM_CHECK_ENABLED=0`），不进入关键链路。
- **通知群发**：MVP 禁止给所有 editor/admin 群发通知（会引发云端 mock 用户导致的 409 日志刷屏）；仅通知 `owner_id/editor_id` 或作者本人。
- **修订 Response Letter 图片上传**：MVP 不做上传到 Storage；改为前端压缩后以 Data URL 内嵌（有体积限制）。

## 项目结构

```text
backend/
├── app/
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
│   ├── app/
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
bun run test                    # 运行单元测试 (Vitest)
bun run test:coverage           # 运行单元测试并生成覆盖率
bun run test:e2e                # 运行 E2E 测试 (Playwright)
bun run test:e2e:ui             # 在 UI 模式下运行 E2E 测试
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
- **包管理器统一**：前端统一使用 `bun`（替代 `pnpm/npm`），后端统一使用 `uv`（替代 `pip`）；脚本与 CI 均以 `bun run` + `uv pip` 为准。
- **编辑端列表限流参数（2026-02-25）**：新增 `EDITOR_PROCESS_QUERY_LIMIT`（默认 `300`，范围 `50-1000`）与 `EDITOR_PIPELINE_STAGE_LIMIT`（默认 `80`，范围 `10-300`）；用于限制 Process/Pipeline 单次查询规模，避免全量扫描导致高延迟。
- **Tailwind 设计系统化基线（2026-02-25）**：前端基线文档统一维护在 `docs/TAILWIND_V4_MIGRATION_BASELINE.md`；审计命令为 `cd frontend && bun run audit:tailwind-readiness`。当前基线：`w-[96vw]=0`、`hex=0`、`inline style=0`、`hard palette=0`、`magic width=0`（五项核心计数已全清零，且 `frontend-ci` 已对 `legacy motion/long duration` 增设门禁防回退）。
- **Tailwind v4 迁移 Phase 2（2026-02-25）**：前端已完成 CSS-first 迁移：`globals.css` 内新增 `@theme` 承载语义 token（颜色/字体/圆角/accordion 动画），并用 `@utility` 实现 `animate-in/out + fade/zoom/slide` 动画兼容层；已删除 `@config` 与 `tailwind.config.mjs`，`components.json` 的 `tailwind.config` 置空。
- **Tailwind v4 迁移 Phase 3（2026-02-25）**：已完成动画语义层收敛（`sf-motion-*`）并替换高频组件（`dialog/popover/select/dashboard/home/header/version`）中的长动画拼接 class；`motion budget` 门禁（`legacy motion=0`、`long duration=0`）已接入 `frontend-ci`，下一步聚焦真实页面数据下的动画进一步降载。
- **站点 Metadata 域名（2026-02-25）**：`frontend/src/app/layout.tsx` 已不再使用 `scholarflow.example.com` 占位域名；优先读取 `NEXT_PUBLIC_SITE_URL`，其次 `VERCEL_PROJECT_PRODUCTION_URL` / `VERCEL_URL`，用于 `metadataBase`、OpenGraph、Twitter 图片地址生成。生产环境建议显式配置 `NEXT_PUBLIC_SITE_URL`（含协议）。
- **App Router 规范收敛（2026-02-25）**：首页 `frontend/src/app/page.tsx` 已改为 Server Component 服务端取 `latest articles`（`revalidate=3600` + fallback 数据），不再在客户端 `useQuery` 拉取；`frontend/src/pages/editor/*` 已移除，`/editor/{workspace,intake,managing-workspace,academic}` 全部仅由 `app/(admin)/editor/*` 承载，避免 pages/app 混用导致 layout/metadata/cache 口径分裂。
- **Editor API 安全与解耦（2026-02-26）**：已移除 `GET /api/v1/editor/test/pipeline`、`GET /api/v1/editor/test/available-reviewers`、`POST /api/v1/editor/test/decision` 三个无鉴权测试端点；`/editor/rbac/context` 与 `/editor/manuscripts/process` 已拆分至 `backend/app/api/v1/editor_process.py`，降低 `editor.py` 路由耦合度。
- **Auth Token 硬化（2026-02-26）**：前端 `authService` 不再维护 `scholarflow:access_token` 的 localStorage 镜像，也不再从 localStorage 直读 token；统一通过 `supabase.auth.getSession()/refreshSession()` 获取会话，减少 token 暴露面。
- **Backend Origin 基础设施收敛（2026-02-26）**：新增 `frontend/src/lib/backend-origin.ts` 统一 `BACKEND_ORIGIN/NEXT_PUBLIC_API_URL` 解析，Server Component 页面不再重复定义 `getBackendOrigin()`，避免缓存策略与容错口径漂移。
- **Invoice PDF 中文字体（2026-02-24）**：HF Docker 镜像需安装 `fonts-noto-cjk`；`backend/app/core/templates/invoice_pdf.html` 字体栈已包含 `PingFang SC` / `Noto Sans CJK SC` 回退。若本地直接生成发票 PDF，也需在系统安装任一 CJK 字体以避免中文方块字。
- **Schema 来源**：以仓库内 `supabase/migrations/*.sql` 为准；若云端未应用最新 migration（例如缺少 `public.manuscripts.version`），后端修订集成测试会出现 `PGRST204` 并被跳过/失败。
- **Portal Latest Articles（公开接口兼容）**：`GET /api/v1/portal/articles/latest` **不得依赖** `public.manuscripts.authors`（云端历史 schema 可能不存在该列），作者展示字段由后端从 `public.user_profiles.full_name` 组装；如 profile 缺失则通过 Supabase Admin API 获取邮箱并**脱敏**（不泄露明文），最终兜底 `Author`。
- **Portal Citation/Topics（Feature 034）**：公开文章引用导出统一走后端 `GET /api/v1/manuscripts/articles/{id}/citation.bib|ris`；`/topics` 统一走 `GET /api/v1/public/topics` 动态聚合（基于已发表文章/期刊关键词推断，MVP 不依赖新增 subject 表字段）。
- **Reviewer Invite Policy（GAP-P1-04）**：`POST /api/v1/reviews/assign` 已支持 `override_cooldown` + `override_reason`；冷却期默认 `REVIEW_INVITE_COOLDOWN_DAYS=30`，高权限覆盖角色由 `REVIEW_INVITE_COOLDOWN_OVERRIDE_ROLES` 控制（默认 `admin,managing_editor`）；审稿人接受邀请 due 窗口使用 `REVIEW_INVITE_DUE_MIN_DAYS` / `REVIEW_INVITE_DUE_MAX_DAYS` / `REVIEW_INVITE_DUE_DEFAULT_DAYS`（默认 `7/21/10`）。
- **投稿上传超时策略（2026-02-09）**：`frontend/src/components/SubmissionForm.tsx` 对 Storage 上传增加 90s 超时、对元数据解析增加 25s 超时；解析请求优先直连 `NEXT_PUBLIC_API_URL`（HF Space），失败再回退 `/api/v1/manuscripts/upload` rewrite，降低 Vercel 代理链路卡住概率。
- **PDF 本地解析降级开关（2026-02-09）**：后端 `POST /api/v1/manuscripts/upload` 支持按文件体积跳过版面提取：`PDF_LAYOUT_SKIP_FILE_MB`（默认 `8`，超过后 `layout_max_pages=0`）；元数据提取增加 `PDF_METADATA_TIMEOUT_SEC`（默认 `4`）超时降级为手填，避免长时间转圈。
- **HF 日志可见性（2026-02-09）**：Docker 启用 `PYTHONUNBUFFERED=1` + `uvicorn --access-log --log-level info`，上传链路新增 trace 日志（`[UploadManuscript:<id>]`），便于在 Space Logs 定位卡点。
- **GAP-P2-01（DOI/Crossref 真对接）迁移与配置**：云端需执行 `supabase/migrations/20260210193000_doi_registration_manuscript_fk.sql`（修复 `doi_registrations.article_id` 到 `manuscripts` 的兼容约束 + 任务索引）；后端需配置 `CROSSREF_DEPOSITOR_EMAIL` / `CROSSREF_DEPOSITOR_PASSWORD` / `CROSSREF_DOI_PREFIX` / `CROSSREF_API_URL`，并通过 `POST /api/v1/internal/cron/doi-tasks`（`ADMIN_API_KEY`）消费队列。
- **GAP-P2-02（查重能力重启）开关约定**：默认仍可保持关闭（`PLAGIARISM_CHECK_ENABLED=0`）；启用时支持 `PLAGIARISM_SIMILARITY_THRESHOLD`、`PLAGIARISM_POLL_MAX_ATTEMPTS`、`PLAGIARISM_POLL_INTERVAL_SEC`、`PLAGIARISM_SUBMIT_DELAY_SEC` 调优。状态查询/重试/下载统一走 `/api/v1/plagiarism/status/{manuscript_id}`、`/api/v1/plagiarism/retry`、`/api/v1/plagiarism/report/{report_id}/download`。
- **Journal Management（2026-02-11）迁移与投稿绑定**：云端需执行 `supabase/migrations/20260210200000_add_journal_management_fields.sql`（`journals.is_active/updated_at` + trigger/index）；后台新增 `GET/POST/PUT/DELETE /api/v1/admin/journals` 与页面 `/admin/journals`；投稿页通过 `GET /api/v1/public/journals` 加载期刊并在 `POST /api/v1/manuscripts` 提交 `journal_id`（后端校验期刊存在且可用）。
- **决策口径对齐（2026-02-12）**：`AE Technical Check` 支持 `pass | academic | revision`（`academic` 为可选送审）；`First Decision` 草稿在 `under_review/resubmitted` 保存后会自动推进到 `decision`（用于 AE→EIC 交接）；`Final Decision` 仍强制要求作者至少一次修回提交（accept/reject 仅允许在 `resubmitted/decision/decision_done` 执行），否则返回 422。
- **Production Editor（2026-02-12）**：新增角色 `production_editor`（不强制绑定期刊）；生产工作台新增 `GET /api/v1/editor/production/queue` 与前端 `/editor/production`，仅展示 `production_cycles.layout_editor_id` 分配到自己的活跃轮次；上传清样/核准等生产动作在后端按 `layout_editor_id` 强校验；`assistant_editor` 不再访问 production workspace（录用后由 ME/PE 接管）。
- **作者侧稿件时间线（2026-02-12）**：作者稿件详情统一走 `GET /api/v1/manuscripts/{id}/author-context` 返回“对作者可见的全量时间线”（状态流转、ME 技术退回、作者修回、匿名审稿意见、Final decision）；审稿附件下载走 `GET /api/v1/manuscripts/{mid}/review-reports/{rid}/author-attachment` 由后端 proxy 转发，避免泄露 Storage object key；Reviewer 永远不返回身份字段，仅按 `审稿人 #n` 展示。
- **Workflow 审核约束（2026-02-06）**：拒稿只能在 `decision/decision_done` 阶段执行；`pre_check`、`under_review`、`resubmitted` 禁止直接流转到 `rejected`。外审中发现问题需先进入 `decision` 再做拒稿。Quick Pre-check 仅允许 `approve` / `revision`。
- **云端迁移同步（Supabase CLI）**：在 repo root 执行 `supabase projects list`（确认已 linked）→ `supabase db push --dry-run` → `supabase db push`（按提示输入 `y`）。若 CLI 不可用/失败，则到 Supabase Dashboard 的 SQL Editor 依次执行 `supabase/migrations/*.sql`（至少包含 `20260201000000/00001/00002/00003`）并可执行 `select pg_notify('pgrst', 'reload schema');` 刷新 schema cache。
- **Feature 030（Reviewer Library）迁移**：云端需执行 `supabase/migrations/20260204210000_reviewer_library_active_and_search.sql`（新增 `is_reviewer_active`、`reviewer_search_text` + `pg_trgm` GIN 索引），否则 `/api/v1/editor/reviewer-library` 会报列不存在。
- **Feature 033（Manuscript Files）迁移**：云端需执行 `supabase/migrations/20260205130000_create_manuscript_files.sql`（新增 `public.manuscript_files` 用于 editor 上传 peer review files），否则 `POST /api/v1/editor/manuscripts/{id}/files/review-attachment` 会返回 “DB not migrated”。
- **Feature 041（Final Decision Workspace）迁移**：云端需依次执行 `supabase/migrations/20260206160000_create_decision_letters.sql`、`supabase/migrations/20260206161000_decision_storage.sql`、`supabase/migrations/20260206162000_decision_letter_constraints.sql`（新增 `public.decision_letters` 与私有桶 `decision-attachments`），否则 `/api/v1/editor/manuscripts/{id}/decision-*` 接口会因 schema/storage 缺失失败。
- **Feature 043（Cloud Rollout Regression）迁移**：云端需执行 `supabase/migrations/20260209160000_release_validation_runs.sql`（新增 `release_validation_runs` / `release_validation_checks`）；发布前通过 `POST /api/v1/internal/release-validation/*` 或 `scripts/validate-production-rollout.sh` 执行 readiness + regression + finalize 放行门禁。
- **Feature 044（Pre-check Role Hardening）迁移**：云端需执行 `supabase/migrations/20260206150000_add_precheck_fields.sql`（新增 `assistant_editor_id`、`pre_check_status`）；若未迁移，`/api/v1/editor/manuscripts/process` 与相关集成测试可能出现 `PGRST204`（列缺失），测试会按约定 `skip`。
- **Feature 044 Intake Gate（2026-02-10）**：新增 `POST /api/v1/editor/manuscripts/{id}/intake-return`（ME 入口技术退回，`comment` 必填）；`/editor/intake` 必须提供“查看稿件包”（跳转 `/editor/manuscript/[id]`）后再执行退回或分配。
- **Feature 045（Internal Collaboration Enhancement）迁移**：云端需执行 `supabase/migrations/20260209190000_internal_collaboration_mentions_tasks.sql`（新增 `internal_comment_mentions`、`internal_tasks`、`internal_task_activity_logs`）；若未迁移，`/api/v1/editor/manuscripts/{id}/comments` 提及、`/api/v1/editor/manuscripts/{id}/tasks*` 与 Process `overdue_only` 聚合会返回 “DB not migrated: ... table missing”。
- **Feature 046（Finance Invoices Sync）迁移**：云端需执行 `supabase/migrations/20260209193000_finance_invoices_indexes.sql`（新增 `invoices.status/confirmed_at/created_at` 索引）；`/finance` 已改为真实数据接口 `GET /api/v1/editor/finance/invoices` 与 `GET /api/v1/editor/finance/invoices/export`，不再使用本地 demo 数据。
- **Feature 001（Editor Performance Indexes）迁移（2026-02-24）**：云端需执行 `supabase/migrations/20260224173000_editor_performance_indexes.sql`（新增 manuscripts 多组复合索引 + `title` trigram 索引）；完成后建议在 SQL Editor 运行 `supabase/maintenance/editor_performance_explain.sql` 对比 query plan（process/workspace/detail）。
- **Editor 性能基线脚本（2026-02-24）**：`scripts/perf/capture-editor-baseline.sh` 已支持 `--auto-url` 自动采样 API TTFB；可用 `scripts/perf/capture-editor-api-baselines.sh` 一次性采样 detail/process/workspace/pipeline 四条链路并输出标准 JSON 基线。
- **前端路由包体门禁（2026-02-26）**：新增 `cd frontend && bun run audit:route-budgets`（基于 `.next` manifest 统计关键路由 gzip JS 体积）；阈值配置位于 `frontend/scripts/route-budgets.json`，已接入 `.github/workflows/ci.yml` 在 build 后自动校验并超限失败。
- **公共期刊列表短缓存（2026-02-26）**：`GET /api/v1/public/journals` 新增进程内短 TTL 缓存；可通过 `PUBLIC_JOURNALS_CACHE_TTL_SEC`（默认 `60`）调优，降低公开页面高频刷新的数据库压力。
- **云端索引迁移状态（2026-02-26）**：远端 Supabase 已补齐执行 `supabase/migrations/20260224173000_editor_performance_indexes.sql`（此前 local/remote migration list 不一致）；可通过 `supabase migration list --linked` 与 `supabase inspect db index-stats --linked` 校验索引存在性。
- **部署拓扑延迟约束（2026-02-26）**：当前默认拓扑仍为 `Vercel(Frontend) + HuggingFace Spaces(Backend) + Supabase(DB)`；若出现首屏/接口高延迟，优先做“同区域部署”或“同云迁移”再评估代码瓶颈，避免跨区域 RTT 放大导致误判为纯代码问题。
- **GAP-P1-03（Analytics 管理视角增强）迁移**：云端需执行 `supabase/migrations/20260210150000_analytics_management_insights.sql`（新增 `get_editor_efficiency_ranking`、`get_stage_duration_breakdown`、`get_sla_overdue_manuscripts`）；若未迁移，`GET /api/v1/analytics/management` 将退化为空列表（并保持页面可用）。
- **GAP-P1-05（Role Matrix + Journal Scope RBAC）迁移前置**：进入实现阶段后，云端需执行 `supabase/migrations/20260210110000_create_journal_role_scopes.sql`（新增 `public.journal_role_scopes`）；未迁移前仅保持 legacy 角色校验，不启用强制跨期刊隔离写拦截。
- **GAP-P1-05 Scope 执行口径（2026-02-11 更新）**：`managing_editor` / `editor_in_chief` 始终按 `journal_role_scopes` 强制隔离（即使 `JOURNAL_SCOPE_ENFORCEMENT=0`；scope 为空时列表返回空、稿件级写操作返回 403）。`JOURNAL_SCOPE_ENFORCEMENT` 仅继续控制 assistant_editor 等非管理角色的灰度拦截。
- **Admin 角色编辑与 Scope 绑定（2026-02-11 更新）**：`PUT /api/v1/admin/users/{id}/role` 当目标角色包含 `managing_editor/editor_in_chief` 时，必须具备至少一个期刊绑定（可通过 `scope_journal_ids` 同步提交）；移除这两类角色会自动停用其对应 `journal_role_scopes`。`assistant_editor` 保持轻量策略：不强制绑定期刊，仅按分配稿件可见。
- **Legacy editor 角色清洗（2026-02-11）**：云端需执行 `supabase/migrations/20260211160000_cleanup_legacy_editor_role.sql`，将 `user_profiles.roles` 与 `journal_role_scopes.role` 中历史 `editor` 幂等迁移为 `managing_editor`，并收紧 `journal_role_scopes_role_check` 约束，避免后续新写入继续落 legacy 角色。
- **Feature 024 迁移（可选）**：若要启用 Production Gate（强制 `final_pdf_path`），云端 `public.manuscripts` 需包含 `final_pdf_path`（建议执行 `supabase/migrations/20260203143000_post_acceptance_pipeline.sql`）；若不启用 Production Gate，可先不做该迁移，发布会自动降级为仅 Payment Gate。
- **单人开发提速（默认不走 PR）**：当前为“单人 + 单机 + 单目录”开发，默认不使用 PR / review / auto-merge。工作方式：**直接在 `main` 小步 `git commit` → `git push`**（把 GitHub 当作备份与回滚点）；仅在重大高风险改动或多人协作时才开短期 feature 分支并合回 `main`。
- **分支发布约束（强制）**：GitHub 远端只保留 `main` 作为长期分支；功能开发可在本地短分支进行，但完成后必须合入 `main` 并删除本地/远端功能分支，禁止在 GitHub 长期保留 `0xx-*` 分支。
- **交付收尾（强约束）**：每个 Feature 完成后必须执行：`git push` → 合并到 `main`（`--no-ff`）→ `git push` → 删除除 `main` 之外所有本地/远端分支 → 用 `gh` 检查 GitHub Actions，确保主干始终为绿。
- **GitHub 分支发布策略（强约束）**：推送到 GitHub 的提交**只能进入 `main`**；禁止将 `0xx-*` 等 feature 分支推到远端长期保留。可在本地临时建分支开发，但发布时必须以 `main` 为唯一远端分支。
- **上下文同步（强约束）**：任何 Agent 在完成重大功能规划、实施环境变更（如新路由、新表字段、新环境变量）后，**必须立即同步更新** `GEMINI.md`、`CLAUDE.md` 和 `AGENTS.md` 的“近期关键修复快照”和“环境约定”部分，确保全系统 Agent 认知一致。
- **后端单文件测试注意**：`backend/pytest.ini` 强制 `--cov-fail-under=80`，单跑一个文件可能因覆盖率门槛失败；单文件验证用 `pytest -o addopts= tests/integration/test_revision_cycle.py`。
- **E2E 鉴权说明**：`frontend/src/middleware.ts` 在 **非生产环境** 且请求头带 `x-scholarflow-e2e: 1`（或 Supabase Auth 不可用）时，允许从 Supabase session cookie 解析用户用于 Playwright；生产环境不会启用该降级逻辑。
- **测试提速（分层策略）**：开发中默认跑 Tier-1：`./scripts/test-fast.sh`（可用 `BACKEND_TESTS=...` / `FRONTEND_TESTS=...` 只跑相关用例）；提 PR 前/合并前必须跑全量：`./scripts/run-all-tests.sh`，确保主干永远保持绿。
- **CI-like 一键测试**：`./scripts/run-all-tests.sh` 默认跑 `backend pytest` + `frontend vitest` + mocked E2E（`frontend/tests/e2e/specs/*.spec.ts`）。可用 `PLAYWRIGHT_PORT` 改端口，`E2E_SPEC` 指定单个 spec。若要跑全量 Playwright：`E2E_FULL=1 ./scripts/run-all-tests.sh`（脚本会尝试启动 `uvicorn main:app --port 8000`，可用 `BACKEND_PORT` 覆盖）。
- **Playwright WebServer 复用（重要）**：`frontend/playwright.config.ts` 默认 **不复用** 已存在的 dev server，避免误连到“端口上其他服务/残留进程”导致 404/空白页；如需复用以提速本地调试，显式设置 `PLAYWRIGHT_REUSE_EXISTING_SERVER=1`。
- **安全提醒**：云端使用 `SUPABASE_SERVICE_ROLE_KEY` 等敏感凭证时，务必仅存于本地/CI Secret，避免提交到仓库；如已泄露请立即轮换。

## 近期关键修复快照（2026-02-26）
- **后端大文件重构（2026-02-26）**：`EditorService` 财务能力已拆分到 `backend/app/services/editor_service_finance.py`（`editor_service.py` 从 1009 行降到 725 行）；`reviews.py` 公共能力抽到 `backend/app/api/v1/reviews_common.py`（主文件从 760 行降到 654 行），并保留原函数包装以兼容现有 monkeypatch 测试。
- **Decision Service 拆分（2026-02-26）**：`backend/app/services/decision_service.py` 已按职责拆分为 `decision_service_letters.py`（报告/草稿）与 `decision_service_transitions.py`（最终流转/通知），主文件从 896 行降到 518 行；`test_decision_*` 相关回归 `18 passed`。
- **Production Workflow 拆分（2026-02-26）**：`backend/app/services/production_workspace_service_workflow.py` 已按职责拆分为 `workflow_common.py`（常量/工具）、`workflow_cycle.py`（cycle 管理/上传/核准）、`workflow_author.py`（作者校对），主文件从 982 行降到 60 行；production/proofreading 回归 `20 passed`。
- **Editor 性能体检与索引补齐（2026-02-26）**：完成两轮 API 基线复采（`baseline-2026-02-26-post-backend-hardening-*`、`baseline-2026-02-26-post-index-push-*`），并在云端执行缺失 migration `20260224173000`；当前结论是数据库索引已补齐，编辑链路瓶颈更偏向跨区域网络/冷启动与后端聚合耗时。
- **后端最佳实践加固（2026-02-26）**：`GET /api/v1/manuscripts` 改为“必须认证 + 仅返回当前用户稿件”；`POST /api/v1/manuscripts` 与 `POST /api/v1/reviews/submit` 的异常语义改为真实 5xx（不再失败返回 200）；`GET /api/v1/stats/editor` 新增编辑角色门禁，避免普通用户读取编辑面聚合数据。
- **Analytics/Finance/Reviewer API 收口（2026-02-26）**：`/api/v1/analytics/{summary,trends,geo,export}` 全部接入 journal-scope 参数下传（ME/EIC 默认按 scope 裁剪）；Finance 列表改为数据库侧状态筛选 + 分页/计数（移除固定 5000 行拉取）；`/api/v1/editor/available-reviewers` 增加 `page/page_size/q` 并在无 `range/offset` 的测试桩环境自动降级兼容。
- **权限阻断清零收尾（2026-02-26）**：`assign_ae` 与 `intake-return` 补齐稿件级 scope 校验（`ensure_manuscript_scope_access`）；`First Decision` 草稿自动入队去除 `allow_skip=True` 兜底，状态机拦截时仅记审计 `first_decision_to_queue_blocked`，不再强行流转。
- **Editor API 基线复采（2026-02-26）**：执行 `scripts/perf/capture-editor-api-baselines.sh` 产出 post-fixes 基线（`baseline-2026-02-26-post-fixes-editor_{detail,process,workspace,pipeline}.json`）；当前采样 p95：detail `6535ms`、process `3187ms`、workspace `3646ms`、pipeline `5052ms`。
- **Tailwind v4 Phase 2 落地（2026-02-25）**：完成 CSS-first token 迁移并移除 `tailwindcss-animate` 插件依赖；动画类改为 `globals.css` 内建 `@utility`；`lint`、`vitest`、`build`、`tailwind audit(enforce)` 均通过，v4 迁移不再依赖 `@config` 兼容层。
- **前端样式 token 化推进（2026-02-25）**：完成第 5/6/7/8/9/10/11/12/13/14/15/16 批高频页面改造（workspace/production/admin/reviewer/auth/decision 链路），统一替换 `slate|blue` 硬编码为语义 token；`hard palette` 从 `973` 降至 `0`，并保持 `w-[96vw]=0`。
- **前端 token 化回归（2026-02-25）**：第 12/13/14/15 批提交 `6f56630`、`0804a9a`、`53ea5ba`、`1325373` 已合入 `main`；第 16 批收尾后 `bun run lint` 与 `bun run audit:tailwind-readiness` 通过，当前 `w-[96vw]/hex/inline/hard palette` 全部为 `0`，并在 `.github/workflows/ci.yml` 新增 Tailwind Readiness Gate（阈值默认 `0`）。
- **权限与状态机收敛（2026-02-25）**：内部协作接口新增稿件级访问校验（ME/EIC 强制 journal scope，AE 仅限分配稿件，PE 仅限分配 cycle）；`editor` 的手动改状态、review-attachment 上传、quick-precheck 与 production 管理动作补齐 scope 校验。
- **决策/审稿会话一致性修复（2026-02-25）**：`decision/decision_done -> major_revision/minor_revision` 已纳入显式状态机，Final Decision 的修回分支不再依赖 `allow_skip=True` 兜底；Reviewer 登录态进入 workspace 时会强制将 assignment 更新为 `accepted`，若数据库更新失败返回 500（不再吞异常）。
- **前后端渲染/请求限流（2026-02-25）**：Pipeline 各状态桶新增后端 per-stage limit，Process 查询新增后端硬上限；前端 `ManuscriptTable` 改为渐进加载（Load more），`EditorPipeline` 过滤态增加展示上限，避免大数据量时全量渲染卡顿；Reviewer 批量指派改为“部分成功/失败”汇总提示，减少重复指派回归。
- **Editor Process 链路降载（2026-02-25）**：`EditorService.list_manuscripts_process` 改为先做 scope 可见性过滤再执行 profile/overdue 聚合；Pre-check enrich 在 Process 列表里默认关闭 timeline 与 assignee profile 二次拉取，仅保留必要字段并复用一次性 profile 映射回填，减少无效扫描与重复查询。
- **AE/ME Workspace enrich 轻量化（2026-02-25）**：`get_ae_workspace` 与 `get_managing_workspace` 的 pre-check enrich 改为 `include_timeline=False` + `include_assignee_profiles=False`，并在 workspace 层按需补齐展示字段，进一步降低首屏链路成本。
- **Reviewer 指派弹窗按需加载（2026-02-25）**：`ReviewerAssignmentSearch` 改为动态加载 `ReviewerAssignModal`（`next/dynamic` + `ssr:false`），仅在用户点击 `Manage Reviewers` 时下载大组件，减少详情页首包体积。
- **Reviewer Feedback 权限短路（2026-02-25）**：稿件详情页新增 `canViewReviewerFeedback` 前置判定；无权限角色（如 `production_editor`）不再发起 `/api/v1/manuscripts/{id}/reviews` 请求，改为只读提示，消除 403 + retry 噪音。
- **审稿汇总请求短缓存（2026-02-25）**：`EditorApi.getManuscriptReviews` 接入短 TTL 缓存与 inflight dedupe，减少详情页与决策页重复拉取同一稿件审稿汇总。
- **ReviewerAssignModal 内部人员缓存复用（2026-02-25）**：弹窗内部人员列表统一走 `EditorApi.listInternalStaff(..., { ttlMs })`，避免每次打开弹窗重复请求 `/api/v1/editor/internal-staff`。
- **Invoice PDF 中文字体修复（2026-02-24）**：Docker 镜像新增 `fonts-noto-cjk`，发票模板字体链路补齐 `PingFang SC`/`Noto Sans CJK SC`，修复作者下载 invoice 时中文显示为方块的问题。
- **ME Workspace + Cover Letter 补传 + Production 权限收敛（2026-02-24）**：新增 `GET /api/v1/editor/managing-workspace` 与前端页面 `/editor/managing-workspace`（按状态分组展示 ME 跟进稿件）；编辑详情页 File Hub 新增 cover letter 补传入口（`POST /api/v1/editor/manuscripts/{id}/files/cover-letter`）；production workspace 权限收敛为 `admin/managing_editor/editor_in_chief/production_editor`，`assistant_editor` 不再可读访问录用后 production 流程。
- **Editor 详情页与时间线性能优化（2026-02-24）**：新增聚合接口 `GET /api/v1/editor/manuscripts/{id}/timeline-context`，将时间线组件从多请求收敛为单请求；`editor_detail` 新增 Auth profile fallback 的 5 分钟 TTL 缓存，避免 profile 缺失时每次详情页都串行调用最多 20 次 Auth Admin API。
- **Editor 详情页卡片延迟加载（2026-02-24）**：`GET /api/v1/editor/manuscripts/{id}` 新增 `skip_cards` 查询参数以跳过首屏统计计算；新增 `GET /api/v1/editor/manuscripts/{id}/cards-context` 独立返回 `task_summary + role_queue`，前端进入卡片区域后再加载，降低详情首屏阻塞。
- **Reviewer Feedback 视口惰性加载（2026-02-24）**：详情页审稿反馈卡片新增视口激活逻辑，默认不随 `refreshDetail` 自动请求；仅在卡片进入视口后加载，且 `pre_check` 阶段保持跳过，进一步减少首屏与高频刷新时的网络占用。
- **RBAC 上下文并发与短缓存（2026-02-24）**：`EditorApi.getRbacContext` 改为缓存 GET，请求与详情主数据并发启动（不再串行触发），减少编辑详情页初始化链路中的重复鉴权上下文请求。
- **内部协作回调去重（2026-02-24）**：`InternalNotebook` / `InternalTasksPanel` 的变更回调不再触发整页 `refreshDetail`，改为仅在卡片可见时刷新 `cards-context`，减少内部协作高频操作导致的详情重拉。
- **Reviewer 候选搜索稳态优化（2026-02-24）**：`ReviewerAssignModal` 改为“打开弹窗后加载 + 250ms 搜索防抖 + 20s scoped short cache + inflight dedupe”；缓存键绑定 `manuscript_id + query + role_scope + limit`，并提供 `EditorApi.invalidateReviewerSearchCache` 供上下文切换失效。
- **Workspace 请求防旧响应覆盖（2026-02-24）**：`/editor/workspace` 前端新增 `requestId` + `AbortController`，旧请求返回不再覆盖新数据；同时增加短缓存与增量刷新按钮（`workspace-refresh-btn`），提交技术检查后仅触发静默局部刷新。
- **性能基线与门禁脚本（2026-02-24）**：新增 `scripts/perf/capture-editor-baseline.sh`、`compare-editor-baseline.sh`、`write-regression-report.sh` 与 `scripts/validate-editor-performance.sh`，统一产出 `baseline-compare.json` + `regression-report.md` 并执行 GO/NO-GO 判定。
- **Process/Workspace 后端短缓存（2026-02-24）**：`GET /api/v1/editor/manuscripts/process`、`GET /api/v1/editor/workspace`、`GET /api/v1/editor/managing-workspace`、`GET /api/v1/editor/rbac/context` 增加秒级进程内短缓存；前端在 `forceRefresh` 场景透传 `x-sf-force-refresh: 1` 旁路缓存，避免操作后读到短暂旧数据。
- **Legacy editor 清理（Phase-1，2026-02-11）**：新增 `supabase/migrations/20260211160000_cleanup_legacy_editor_role.sql`，完成历史 `editor -> managing_editor` 的数据清洗（`user_profiles.roles` + `journal_role_scopes.role`）与约束收敛；为后续彻底移除后端兼容 alias 做前置准备。
- **鲁总三段决策口径落地（2026-02-11）**：后端 `submit_technical_check` 新增 `academic` 分支（AE 可选送 EIC Academic Queue），`submit_decision` 收紧为“Final 仅允许修回后执行”；前端 `/editor/workspace` 技术检查弹窗升级为三选一（发起外审/送 Academic/技术退回），并同步更新 `docs/upgrade_plan_v3.md + flow_lifecycle_v3.mmd + state_manuscript_v3.mmd` 与新版 PDF。
- **EIC 决策队列可见性修复（2026-02-12）**：`First Decision` 草稿保存后，稿件会从 `under_review/resubmitted` 自动进入 `decision`；`/api/v1/editor/final-decision` 同时纳入“已有 first draft 的稿件”，避免 AE 已提交草稿但 EIC 队列为空。
- **Production Editor 角色闭环（2026-02-12）**：新增 `production_editor` 角色、Dashboard tab、Production Queue 页面 `/editor/production` 与后端接口 `GET /api/v1/editor/production/queue`；production workspace 权限按 `production_cycles.layout_editor_id` 授权，生产动作从 ME/AE 解耦（AE 仅只读可见）。
- **作者侧统一时间线（2026-02-12）**：新增作者专用聚合接口 `GET /api/v1/manuscripts/{id}/author-context`，将投稿/退回/修回/审稿/最终决定统一到单一 timeline（Reviewer 严格匿名）；新增审稿附件 proxy 下载端点 `GET /api/v1/manuscripts/{mid}/review-reports/{rid}/author-attachment`，防止前端暴露 Storage path；前端 `/dashboard/author/manuscripts/[id]` 改为展示该 timeline。
- **Admin 用户管理（2026-02-11）**：角色编辑弹窗支持“角色 + 期刊范围”一次提交；后端新增 ME/EIC 角色与期刊绑定强校验（无 scope 拒绝变更），并在移除管理角色时自动清理对应 scope，避免跨刊越权残留。
- **ME Intake 决策闭环（2026-02-10）**：`/editor/intake` 新增“查看稿件包”与“技术退回作者（必填理由）”动作；后端新增 `POST /api/v1/editor/manuscripts/{id}/intake-return`，退回流转到 `minor_revision` 并写审计 `action=precheck_intake_revision`。
- **ME Intake 性能与可用性优化（2026-02-10）**：`GET /api/v1/editor/intake` 新增 `q` 与 `overdue_only` 过滤，服务层改为轻量查询（去除首屏时间线聚合），前端新增作者/期刊/优先级列、搜索与高优筛选，并将 AE 预取延后到首屏后以降低“刷新长时间转圈”问题。
- **Editor 详情页决策聚焦优化（2026-02-10）**：`/editor/manuscript/[id]` 新增 `Next Action` 决策条（阶段+阻塞条件）、按状态收紧 Reviewer/Decision/状态流转入口、以及高风险流转的二次确认+理由；作者展示改为 `invoice_metadata.authors -> owner.full_name/email` 回填，避免出现 `Unknown Authors`。
- **会话稳定性热修（2026-02-10）**：前端鉴权改为“先刷新再判死会话”（`authService.getSession/getAccessToken` + `useProfile` 401 retry once），降低发布后或 token 临界过期时被误踢回 `/login` 的概率。
- **Journal Management + 投稿期刊绑定（2026-02-11）**：补齐期刊管理闭环：后端新增 admin journals CRUD 与公开 `GET /api/v1/public/journals`；前端新增 `/admin/journals` 管理页和 Dashboard 入口；作者投稿表单新增 Target Journal 下拉，提交时携带 `journal_id` 并在后端做有效性校验，确保稿件从创建阶段绑定到具体期刊。
- **GAP-P2-01（DOI/Crossref 真对接）**：重构 `DOIService` 为真实落库链路（`doi_registrations` + `doi_tasks` + `doi_audit_log`），补齐注册/重试/任务列表 API 与 `POST /api/v1/internal/cron/doi-tasks` 队列消费入口；`register_doi` 现已执行 Crossref XML 生成、提交回执解析、状态更新与审计落库。
- **GAP-P2-02（查重能力重启）**：新增 `PlagiarismService`，实现 `plagiarism_reports` 全生命周期落库（pending/running/completed/failed）、高相似度预警审计与内部通知；补齐 `/api/v1/plagiarism/status/{manuscript_id}` 状态查询、`/retry` 幂等重试、`/report/{id}/download` 下载链路，并在投稿上传流程中先初始化 pending 报告再异步执行 Worker。
- **投稿上传卡住排障（Upload/AI Parse）**：修复作者端“Uploading and analyzing manuscript...”长时间转圈：前端增加双阶段超时（Storage 90s + Parse 25s）与直连 HF 优先策略；后端对大 PDF 自动跳过 layout 并为 metadata 提取加超时降级；同时补齐上传全链路 trace 日志，便于 HF 线上定位。
- **GAP-P1-03（Analytics 管理视角增强）**：新增 `GET /api/v1/analytics/management`，补齐管理下钻三件套：编辑效率排行（处理量/平均首次决定耗时）、阶段耗时分解（pre_check/under_review/decision/production）、超 SLA 稿件预警（逾期 internal tasks 聚合）；前端 `/editor/analytics` 新增管理洞察区块，后端补齐 RBAC（ME/EIC/Admin）+ journal-scope 裁剪。
- **GAP-P1-05（Role Matrix + Journal Scope RBAC）**：已完成整体验收：新增 `GET /api/v1/editor/rbac/context`、服务层/路由层双重动作门禁、journal-scope 隔离（跨刊读写 403）、first/final decision 语义分离、以及 APC/Owner/legacy-final 的统一审计 payload（before/after/reason/source）；前端完成 capability 显隐与 `rbac-journal-scope.spec.ts` mocked E2E 回归。`managing_editor/editor_in_chief` 已改为不受灰度开关影响的强制隔离（scope 为空即不可见）。
- **GAP-P1-04（Review Policy Hardening）**：实现同刊 30 天冷却期（候选灰显拦截）、高权限显式 override（`override_cooldown` + `override_reason` + `status_transition_logs` 审计）、邀请模板变量扩展（reviewer/journal/due date）、以及 Process/详情共用 `ReviewerAssignModal` 的命中原因展示（cooldown/conflict/overdue risk）。
- **Feature 034（Portal Scholar Toolbox）**：补齐公开文章结构化引用与学科聚合：新增 `GET /api/v1/manuscripts/articles/{id}/citation.bib|ris`，文章页新增 BibTeX/RIS 下载按钮；`GET /api/v1/public/topics` 从已发表文章/期刊动态聚合 Subject Collections；`frontend/src/app/articles/[id]/page.tsx` 补 `citation_pdf_url`（指向公开 `/pdf` 入口）以改进 Scholar/SEO 抓取。
- **Feature 046（Finance Invoices Sync）**：`/finance` 切换为真实账单读模型（`invoices + manuscripts + user_profiles`），支持 `all/unpaid/paid/waived` 筛选与 CSV 导出（`X-Export-Snapshot-At` / `X-Export-Empty`）；确认支付与 Editor Pipeline 共用 `POST /api/v1/editor/invoices/confirm`，支持 `expected_status` 并发冲突 409 和 `status_transition_logs.payload.action=finance_invoice_confirm_paid` 审计。
- **Feature 045（Internal Collaboration Enhancement）**：新增 Notebook `mention_user_ids` 校验与去重提醒、内部任务 CRUD + activity 轨迹、Process `overdue_only` + `is_overdue`/`overdue_tasks_count` 聚合；前端新增 `InternalTasksPanel`、Task SLA 摘要、Process 逾期开关与 mocked E2E 回归。
- **Feature 043（Cloud Rollout Regression）**：新增发布验收审计域（`release_validation_runs` + `release_validation_checks`）、internal 验收接口（create/list/readiness/regression/finalize/report）与一键脚本 `scripts/validate-production-rollout.sh`；强制关键 regression 场景 `skip=0` 才可放行，失败自动进入 no-go/rollback_required。
- **Feature 041（Final Decision Workspace）**：新增 `/editor/decision/[id]` 三栏沉浸式终审工作台（审稿对比 + Markdown 决策信 + PDF 预览）；后端新增 decision context/submit/attachment API，落地 `decision_letters` 表与 `decision-attachments` 私有桶，支持草稿保存、乐观锁冲突与作者端 final-only 附件可见性。
- **Feature 040（Reviewer Workspace）**：新增 `/reviewer/workspace/[id]` 沉浸式审稿界面（左侧 PDF + 右侧 Action Panel），支持双通道意见、附件上传、提交后只读与 `beforeunload` 脏表单保护；后端新增 `/api/v1/reviewer/assignments/{id}/workspace|attachments|submit`。
- **Feature 039（Reviewer Magic Link）**：实现 `/review/invite?token=...`（JWT + httpOnly cookie）免登录审稿闭环；补齐 reviewer workspace 页面与 cookie-scope 校验接口；修复 mocked E2E 因空数据触发 ErrorBoundary。
- **Feature 038/044（Pre-check 角色工作流落地）**：完成 ME → AE → EIC 三级预审闭环（Intake → Technical → Academic），后端实现幂等与冲突控制、拒稿门禁、Process/详情预审可视化；前端补齐 `/editor/intake|workspace|academic` 页面与 Pre-check 交互；测试覆盖 contract/integration/unit + mocked E2E（`precheck_workflow.spec.ts`）。
- **Feature 037（Reviewer Invite Response）**：已实现 Reviewer 邀请页 Accept/Decline（含截止日期窗口校验）、邀请时间线字段（invited/opened/accepted/declined/submitted）与 Editor 详情页可视化时间线；并补齐幂等与 E2E/后端测试。
- **Workflow（鲁总反馈）**：状态机已收紧：`pre_check/under_review/resubmitted` 不可直接拒稿，拒稿只能在 `decision/decision_done` 执行；Quick Pre-check 去掉 `reject` 选项并要求 `revision` 必填 comment。
- **Analytics 登录态**：修复 `/editor/analytics` 误判“未登录”（API 统一使用 `createBrowserClient`，可读 cookie session）。
- **Analytics 导出按钮**：Excel/CSV 不再同时显示“导出中...”，改为“按格式单独 loading 文案 + 全局禁用避免并发导出”。
- **Reviewer 修回上下文**：审稿弹窗展示作者修回材料（Response Letter/内嵌图片），并补齐审稿附件下载入口。
- **权限收紧**：`GET /api/v1/manuscripts/{id}/versions` 对 reviewer 增加“必须被分配该稿件”的校验，避免越权读取版本历史。
- **Feature 024（录用后出版流水线）**：新增 Production Final PDF 上传、发布门禁（Payment；Production Gate 可选）、作者账单下载、首页 Latest Articles published-only。
- **Feature 028（Workflow 状态机标准化）**：`manuscripts.status` 迁移到枚举 `public.manuscript_status`（见 `supabase/migrations/20260204000000_update_manuscript_status.sql`），新增审计表 `status_transition_logs`（见 `supabase/migrations/20260204000002_create_transition_logs.sql`）；Editor 新增 Process 列表 `/editor/process`（API：`GET /api/v1/editor/manuscripts/process`）与详情页 `/editor/manuscript/[id]`；稿件详情读取使用 `GET /api/v1/manuscripts/by-id/{id}` 以避免路由吞噬 `/upload`。
- **Feature 029（稿件详情页与 Invoice Info）**：完善 `/editor/manuscript/[id]`：页头展示 Title/Authors/Owner/APC 状态/Updated Time（YYYY-MM-DD HH:mm）；文档分组为 `Cover Letter`、`Original Manuscript`、`Peer Review Reports`（Editor-only，附件走后端 signed URL）；支持编辑 `invoice_metadata`（Authors/Affiliation/APC Amount/Funding Info）并在审计表写入 before/after（`status_transition_logs.payload`，见 `supabase/migrations/20260204193000_status_transition_logs_payload.sql`）。
- **Feature 030（Reviewer Library）**：新增 `/editor/reviewers` 管理页（Add/Search/Edit/Soft Delete），并在稿件详情页 `/editor/manuscript/[id]` 提供 `Manage Reviewers` 入口；指派弹窗改为只从 Reviewer Library 检索（不再“Invite New”直接发邮件），且选中时不触发列表重排（避免 UI 跳动）。
- **Feature 032（Process List 增强）**：Process API 支持 `q` 搜索 + 多条件过滤；前端过滤栏改为 URL 驱动（仅 `q` debounce 自动落地）；新增 Quick Pre-check（`pre_check` 一键：Under Review / Minor Revision）；CI-like E2E 默认端口选 3100+ 且 mocked 模式启动本地 `/api/v1/*` mock server；Production 卡片补齐 `Upload Final PDF` 与 `Mark Paid`。
- **Feature 033（详情页布局对齐）**：重构 `/editor/manuscript/[id]`：顶部 Header (Title/Authors/Funding/APC/Owner/Editor)、文件区三卡（Cover/Original/Peer Review + Upload）、Invoice Info 移到底部表格；新增 Editor-only 上传 peer review file 接口 `POST /api/v1/editor/manuscripts/{id}/files/review-attachment`，文件写入 `review-attachments` 私有桶并记录到 `public.manuscript_files`。
- **Feature 036 (内部协作与详情页升级)**：重构稿件详情页为双栏布局（左侧信息/文件/评论，右侧流程/审计）；新增 `internal_comments` 表用于内部沟通（Notebook）；集成 `status_transition_logs` 可视化审计时间轴；文件下载中心化管理。
- **Portal（UAT 线上稳定性）**：修复 `/api/v1/portal/articles/latest` 在 HF Space 上因 Supabase SDK 参数差异（`order(desc=...)`）与云端 schema 漂移（缺失 `authors`/`published_at`）导致的 500；作者显示不再返回 `Unknown`，且不会泄露明文邮箱。
<!-- MANUAL ADDITIONS END -->

## Recent Changes
- 001-editor-performance-refactor: Added Python 3.14+（backend）, TypeScript 5.x（frontend） + FastAPI, Pydantic v2, Supabase-py, Next.js 14 App Router, React 18, bun, uv
- 047-analytics-management-insights: Added analytics management drilldown (editor efficiency ranking, stage duration breakdown, SLA overdue alerts) with `/api/v1/analytics/management`, RBAC + journal-scope filtering, and dashboard UI integration.
- 048-role-matrix-journal-scope-rbac: Completed GAP-P1-05 end-to-end (role matrix + journal scope isolation + first/final decision semantics + high-risk audit payload + mocked E2E).

## Active Technologies
- Python 3.14+（backend）, TypeScript 5.x（frontend） + FastAPI, Pydantic v2, Supabase-py, Next.js 14 App Router, React 18, bun, uv (001-editor-performance-refactor)
- Supabase PostgreSQL（云端）+ 前端内存短缓存（会话级）+ 文档化基线产物（仓库 specs） (001-editor-performance-refactor)
