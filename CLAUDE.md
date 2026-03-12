# ScholarFlow 项目开发指南

**语言偏好**: 始终使用 **中文** 与我交流。
**Skills 使用**: 要积极地使用 skills，遇到可匹配场景优先调用对应 skill。
**Skills / Context7 约束**: 涉及库、框架、API、最佳实践时，优先用 Context7 查询最新官方文档；先走匹配 skill，再落地实现。

本文档根据所有功能计划自动生成与压缩。最后更新时间：2026-03-12

## 当前技术栈
- **前端**: TypeScript 5.x (Strict Mode), Next.js 16.1.6 (App Router), React 19.x, Tailwind CSS 4.2, Shadcn UI
- **后端**: Python 3.14+, FastAPI 0.115+, Pydantic v2, httpx
- **数据库与认证**: Supabase (PostgreSQL), Supabase Auth, Supabase Storage, Supabase-js v2.x, Supabase-py v2.x
- **测试**: pytest, pytest-cov, Playwright, Vitest
- **AI/ML**:
  - **文档提取（本地）**：PDF使用 `pdfplumber`，DOCX基于 `word/document.xml` 解析。
  - **元数据抽取**：DOCX优先，优先调用 Gemini Developer API 结构化抽取，失败回退到本地规则解析。
  - **匹配**：轻量 TF‑IDF（纯 Python，无 sklearn 依赖）。

## 关键环境假设（必须一致）
- **Supabase**：默认使用云端项目（project ref: `mmvulyrfsorqdpdrzbkd`）。迁移优先用 `supabase db push --linked`。
- **包管理器**：前端统一使用 `bun`，后端统一使用 `uv`。脚本与 CI 以 `bun run` + `uv pip` 为准。
- **环境变量**：真实密钥只放本地/CI/平台 Secrets，严禁提交敏感信息（如 `SUPABASE_SERVICE_ROLE_KEY`）。
- **AI 模型推荐**：默认使用纯 Python 的 hash-embedding，避免环境依赖导致部署失败。
- **存储访问**：统一走后端 Signed URL，禁止前端直连 Storage 导致权限不一致。
- **CMS 渲染**：MVP 期内部内容直接渲染后端 HTML（Vercel 环境下规避 ESM 冲突）。
- **部署架构**：Frontend 部署于 Vercel (`NEXT_PUBLIC_API_URL` 指向后端)，Backend 部署于 Hugging Face Spaces (Docker，基于 `python:3.12-slim`，非 root 用户)。
- **Sentry 监控**：前端开启 sourcemaps（需 Vercel 配置），后端初始化隐私策略（不传请求体，不阻塞启动）。
- **Magic Link**：Reviewer 免登录审稿采用基于 JWT 的 `sf_review_magic` Cookie + 后端 scope 校验。
- **状态机与财务门禁**：拒稿使用 `status='rejected'`，发布必须通过 Payment Gate（账单支付状态），录用后生成 Invoice PDF 落库。

## MVP 已砍/延期清单
- 暂缓 Supabase Session 版 Magic Link。
- 暂缓全量 RLS，主要依赖后端鉴权 + service_role。
- DOI/Crossref 仅保留 schema，不做真实注册闭环。
- 查重默认关闭。
- 禁止通知群发。
- 修订 Response Letter 图片改为 Data URL 内嵌，不传 Storage。

## 项目结构与常用命令
- **后端** (`backend/`): 包含 `app` (api/models/services) 和 `tests` (unit/integration)。
  - `pytest` (运行所有), `pytest -m unit` (单元), `pytest --cov=src` (覆盖率)。
- **前端** (`frontend/`): 包含 `src` (app/components/services) 和 `tests` (unit/e2e)。
  - `bun run test` (Vitest), `bun run test:e2e` (Playwright)。
- **综合** (`./scripts/`):
  - `run-all-tests.sh` (运行所有测试), `test-fast.sh` (快速验证)。

## 核心开发与测试原则
1. **测试分层与 TDD**：高风险改动（状态机、权限、认证、核心链路）必须 TDD（先失败测试，再实现，再回归）。普通改动允许最小验证后提交。禁止将 CI 当作本地调试环境。
2. **API 开发与验证**：API 优先设计，多层数据验证（前端体验+后端Pydantic+数据库约束）。一致的错误响应与日志。
3. **安全第一**：认证优先，JWT 强校验，真实用户上下文，设计安全，防止越权（跨期刊 scope 强制隔离）。
4. **单人开发流**：默认在 `main` 分支小步提交，重大改动开短分支后必须合入 `main` 并删除。保持 `main` 远端为绿。
5. **上下文同步**：核心环境/路由/表变更后，必须同步更新 `.md` 上下文指南文件，保证 Agent 认知一致。

## 环境约定与近期重构补充
- **限流与防护**：后端开启 `RateLimitMiddleware` (默认 60s/600req)，Editor Process/Pipeline 列表开启查询与展示规模硬上限 (`EDITOR_PROCESS_QUERY_LIMIT` / `EDITOR_PIPELINE_STAGE_LIMIT`)。
- **前端规范 (Tailwind v4 & App Router)**：
  - CSS-first 设计：`globals.css` 承载 `@theme` 与 `@utility`。全面清零 hard palette、hex与行内样式。禁止长动画拼接类。
  - 数据获取：首屏依赖 Server Component 服务端获取，避免客户端 `useQuery` 瀑布流。`/editor` 路由全量收敛至 App Router。
  - Token 安全：前端通过 `supabase.auth.getSession()` 获取会话，不再从 localStorage 裸读 token。
- **后端架构解耦**：庞大服务（如 EditorApi、Decision、Production、Reviews、DOIService 等）已完成按职责深层拆解，确保扩展性并避免单文件臃肿。
- **测试环境隔离**：UAT/Staging 具备独立数据库配置和防混淆横幅；本地 Playwright 测试默认不复用已存在 dev server (`PLAYWRIGHT_REUSE_EXISTING_SERVER=0`)。
- **数据库 Schema 同步**：以代码库 `supabase/migrations/*.sql` 为准，云端缺 migration 时相关后端测试会自动 skip 或报错。