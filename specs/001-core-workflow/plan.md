# Implementation Plan: ScholarFlow Core Workflow

**Branch**: `001-core-workflow` | **Date**: 2026-01-27 | **Spec**: [specs/001-core-workflow/spec.md]

## Summary
构建 ScholarFlow 的核心全链路流程。关键路径包括：PDF 投稿与 AI 辅助元数据提取（支持解析失败手动回退）、编辑质检与 KPI 绑定（支持不通过退回修改）、审稿人免登录 Token 预览（系统生成 14 天有效 Token）、自动生成账单及财务手动确认到账门控、以及编辑触发的审稿人推荐邀请。

## Technical Context

**Language/Version**: TypeScript (Next.js 14.2), Python 3.11+ (FastAPI)
**Primary Dependencies**: 
- Frontend: Tailwind CSS, Shadcn UI, React Hook Form, Zod
- Backend: pdfplumber, WeasyPrint, OpenAI SDK, Pydantic v2
**Storage**: Supabase (PostgreSQL), Supabase Storage (PDFs)
**Testing**: Pytest (Backend), Vitest (Frontend)
**Target Platform**: Vercel (Frontend), Docker/Railway (Backend), Supabase (Infrastructure)
**Environment**: 
- 开发平台锁定为 **Arch Linux**。
- 包安装遵循 `pacman` > `paru` (切换至用户 `louis` 执行) > `pip`/`pnpm` 优先级。
- Python 全局包安装必须包含 `--break-system-packages` 参数。
- Docker 必须配置国内镜像源。
**Performance Goals**: 
- AI 解析应在 10s 内完成。
- PDF 预览应在 3s 内加载（使用 Supabase CDN）。
**Constraints**: 
- 严格遵循技术栈锁定：Next.js 14.2, FastAPI 0.115+, Supabase。
- **架构规范**: 
  - 前端必须实现统一的 API 封装类 (Supabase Client/Fetch Utils)。
  - 优先使用 Server Components 进行数据获取，仅交互部分使用 'use client'。
- **容错与安全**: 
  - 财务未确认前禁止“上线”发布（后端门控）。
  - **幂等性**: “确认到账”操作必须在数据库层面实现唯一性校验。
  - 免登录 Token 需具备签名验证和时效性（14 天）。
- **视觉标准**: 
  - 锁定配色：`slate-900` 主色调。
  - 锁定字体：大标题衬线体 (Serif)，正文无衬线体 (Sans)。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **技术栈合规**: 是。严格使用推荐的 Next.js/FastAPI/Supabase。
2. **拒绝过度工程**: 是。不涉及复杂的自动对账或多级分布式架构。
3. **AI 友好性**: 是。所有 API 使用 Pydantic 模型，前端使用 TypeScript 接口。
4. **安全加固**: 是。财务上线门控和审稿人 Token 14 天失效策略确保了业务安全。
5. **效率评估**: 是。优先使用 pdfplumber, OpenAI, WeasyPrint 等库。

## Project Structure

### Documentation (this feature)

```text
specs/001-core-workflow/
├── plan.md              # 本文件
├── research.md          # 决策记录 (PDF 解析, 账单生成, Token 安全)
├── data-model.md        # 数据库模型 (Manuscripts, Invoices 等)
├── quickstart.md        # 环境设置与 MVP 验证步骤
├── contracts/           # API 规范 (OpenAPI)
└── tasks.md             # 任务列表 (由 /speckit.tasks 生成)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/             # FastAPI 路由
│   ├── core/            # AI 解析与 PDF 处理 (pdf_processor.py, ai_engine.py)
│   ├── models/          # Pydantic 核心定义
│   └── services/        # 业务逻辑 (财务确认, 审稿邀请)
└── tests/

frontend/
├── src/
│   ├── app/             # Next.js App Router (submit, admin, review, finance)
│   ├── components/      # UI 组件 (Shadcn UI)
│   ├── lib/             # Supabase 客户端与逻辑
│   └── types/           # 全局 TypeScript 接口
└── tests/
```

**Structure Decision**: 采用 Web application (frontend + backend) 结构，由于前后端跨技术栈，保持清晰的目录隔离。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | | |