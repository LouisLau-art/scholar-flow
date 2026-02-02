# Implementation Plan: Academic Indexing & DOI Minting

**Branch**: `015-academic-indexing` | **Date**: 2026-01-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/015-academic-indexing/spec.md`

## Summary

实现学术期刊标准化索引集成功能，包括：
1. **DOI 自动注册** - 文章发表时调用 Crossref Deposit API 注册 DOI，使用数据库队列实现异步处理和指数退避重试
2. **Google Scholar 适配** - 在文章详情页 SSR 渲染 Highwire Press Meta Tags
3. **OAI-PMH 元数据收割接口** - 实现 v2.0 协议的 6 个标准动词，支持 Dublin Core 格式
4. **失败处理机制** - 数据库队列 + 邮件通知 + 管理界面

## Technical Context

**Language/Version**: Python 3.14+ (Backend), TypeScript 5.x (Frontend)  
**Primary Dependencies**: FastAPI 0.115+, Pydantic v2, httpx, lxml (Backend); Next.js 14.2, React 18.x (Frontend)  
**Storage**: PostgreSQL (Supabase) - 新增 `doi_registrations` 和 `doi_tasks` 表  
**Testing**: pytest, pytest-cov (Backend); Vitest, Playwright (Frontend)  
**Target Platform**: Linux server (Docker), Web browser  
**Project Type**: Web application (frontend + backend)  
**Performance Goals**: DOI 注册 < 5 分钟，OAI-PMH 响应 < 2 秒 (100 条记录)  
**Constraints**: 速率限制 60 req/min/IP (OAI-PMH)，重试上限 4 次  
**Scale/Scope**: 预计 < 10000 篇文章，中小型学术期刊

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| 测试优先 | ✅ PASS | 所有新功能需编写单元测试和集成测试 |
| 认证安全 | ✅ PASS | OAI-PMH 公开访问（仅已发表文章），DOI 管理需编辑权限 |
| 类型安全 | ✅ PASS | Pydantic v2 (后端) + TypeScript (前端) |
| API 版本化 | ✅ PASS | 使用 `/api/v1/` 前缀 |
| 简单优先 | ✅ PASS | 使用数据库队列而非 Celery/Redis |

**Gate Result**: PASS - 可进入 Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/015-academic-indexing/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── doi-api.yaml     # DOI 注册 API
│   └── oaipmh-api.yaml  # OAI-PMH 接口
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   └── doi.py           # DOI 注册 API 端点
│   │   └── oaipmh.py            # OAI-PMH 接口端点 (无版本前缀)
│   ├── core/
│   │   └── doi_worker.py    # 数据库队列 Worker
│   ├── models/
│   │   ├── doi.py           # DOI Pydantic 模型
│   │   └── oaipmh.py        # OAI-PMH 模型
│   └── services/
│       ├── crossref_client.py   # Crossref API 客户端
│       ├── doi_service.py       # DOI 业务逻辑
│       └── oaipmh/
│           ├── protocol.py      # OAI-PMH 协议处理
│           └── dublin_core.py   # Dublin Core 映射
└── tests/
    ├── unit/
    │   ├── test_crossref_xml.py
    │   └── test_dublin_core.py
    └── integration/
        ├── test_doi_registration.py
        └── test_oaipmh_verbs.py

frontend/
├── src/
│   ├── app/
│   │   ├── articles/[id]/
│   │   │   └── page.tsx     # 文章详情页 (含 Meta Tags)
│   │   └── (admin)/editor/
│   │       └── doi-tasks/
│   │           └── page.tsx # DOI 任务管理页
│   ├── lib/
│   │   ├── api/doi.ts       # DOI API 客户端
│   │   └── metadata/
│   │       └── citation.ts  # Highwire Press 标签生成
│   └── components/
│       └── doi/
│           ├── DOITaskList.tsx
│           └── DOIStatus.tsx
└── tests/
    ├── unit/
    │   └── citation.test.ts
    └── e2e/
        └── doi-tasks.spec.ts

supabase/migrations/
└── 20260130210000_doi_registration.sql  # 数据库迁移
```

**Structure Decision**: 遵循现有项目结构，后端使用 FastAPI 分层架构，前端使用 Next.js App Router。

## Complexity Tracking

> 无违规项，无需记录。
