# Tasks: Academic Indexing & DOI Minting

**Input**: Design documents from `/specs/015-academic-indexing/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: 包含单元测试和集成测试（规格文档要求测试优先）

**Organization**: 按 User Story 组织，支持独立实现和测试

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 所属 User Story (US1, US2, US3, US4)

## Path Conventions

- **Backend**: `backend/app/`, `backend/tests/`
- **Frontend**: `frontend/src/`, `frontend/tests/`
- **Migrations**: `supabase/migrations/`

---

## Phase 1: Setup (共享基础设施)

**Purpose**: 项目初始化和基础结构

- [x] T001 创建数据库迁移文件 `supabase/migrations/20260130210000_doi_registration.sql`
- [x] T002 [P] 安装后端依赖 `httpx`, `lxml` 在 `backend/requirements.txt`
- [x] T003 [P] 创建 DOI Pydantic 模型 `backend/app/models/doi.py`
- [x] T004 [P] 创建 OAI-PMH Pydantic 模型 `backend/app/models/oaipmh.py`
- [x] T005 添加环境变量配置 (CROSSREF_*, JOURNAL_*) 在 `backend/app/core/config.py`

---

## Phase 2: Foundational (阻塞性前置任务)

**Purpose**: 所有 User Stories 依赖的核心基础设施

**⚠️ CRITICAL**: 此阶段完成前不能开始任何 User Story

- [x] T006 运行数据库迁移，创建 `doi_registrations`, `doi_tasks`, `doi_audit_log` 表
- [x] T007 [P] 创建 Crossref XML 生成器 `backend/app/services/crossref_client.py` (基础结构)
- [x] T008 [P] 创建 Dublin Core 映射器 `backend/app/services/oaipmh/dublin_core.py` (基础结构)
- [x] T009 注册 DOI API 路由 `backend/app/api/v1/doi.py` 在 `backend/app/api/v1/__init__.py`
- [x] T010 注册 OAI-PMH 路由 `backend/app/api/oaipmh.py` 在 `backend/app/main.py`（无版本前缀）

**Checkpoint**: 基础设施就绪 - 可以开始 User Story 实现

---

## Phase 3: User Story 1 - DOI 自动注册 (Priority: P1) 🎯 MVP

**Goal**: 文章发表时自动调用 Crossref API 注册 DOI

**Independent Test**: 发表测试文章，验证 DOI 注册到 Crossref 测试环境，通过 https://doi.org/[DOI] 解析到文章页面

### Tests for User Story 1

- [x] T011 [P] [US1] 单元测试 Crossref XML 生成 `backend/tests/unit/test_crossref_xml.py`
- [x] T012 [P] [US1] 集成测试 DOI 注册流程 `backend/tests/integration/test_doi_registration.py`

### Implementation for User Story 1

- [x] T013 [US1] 实现 Crossref XML 生成逻辑 `backend/app/services/crossref_client.py`
  - DOI 批次 XML 构建 (Schema 5.4.0)
  - journal_article 元素生成
  - 作者信息映射
- [x] T014 [US1] 实现 Crossref HTTP 客户端 `backend/app/services/crossref_client.py`
  - multipart/form-data 请求
  - HTTP Basic Auth
  - 响应解析
- [x] T015 [US1] 实现 DOI 服务层 `backend/app/services/doi_service.py`
  - `generate_doi()` - 生成 DOI 后缀 (sf.{year}.{sequence})
  - `create_registration()` - 创建注册记录
  - `submit_to_crossref()` - 提交到 Crossref
  - `update_registration_status()` - 更新状态
- [x] T016 [US1] 实现 DOI API 端点 `backend/app/api/v1/doi.py`
  - POST `/api/v1/doi/register` - 触发注册
  - GET `/api/v1/doi/{article_id}` - 查询状态
- [x] T017 [US1] 添加发表触发器 - 修改文章发表流程调用 DOI 注册
- [x] T018 [US1] 添加 DOI 显示 - 更新文章详情页显示 DOI 链接

**Checkpoint**: DOI 自动注册功能完整可测试

---

## Phase 4: User Story 2 - Google Scholar 适配 (Priority: P2)

**Goal**: 文章详情页 SSR 渲染 Highwire Press Meta Tags

**Independent Test**: 访问已发表文章页面，检查 HTML head 中的 citation_* 标签

### Tests for User Story 2

- [x] T019 [P] [US2] 单元测试 Meta Tags 生成 `frontend/tests/unit/citation.test.ts`

### Implementation for User Story 2

- [x] T020 [P] [US2] 创建 citation 标签生成函数 `frontend/src/lib/metadata/citation.ts`
  - `generateCitationMetadata()` - 生成 Highwire Press 标签
  - 必需标签: citation_title, citation_author, citation_publication_date, citation_journal_title, citation_doi
  - 可选标签: citation_pdf_url, citation_abstract, citation_volume, citation_issue
- [x] T021 [US2] 更新文章详情页 `frontend/src/app/articles/[id]/page.tsx`
  - 添加 `generateMetadata` 函数 (Next.js SSR)
  - 集成 citation 标签生成
- [x] T022 [US2] 处理多作者场景 - 每位作者生成独立 citation_author 标签
- [x] T023 [US2] 处理 PDF URL - 如有 PDF 附件生成 citation_pdf_url

**Checkpoint**: Google Scholar Meta Tags 功能完整可测试

---

## Phase 5: User Story 3 - OAI-PMH 元数据收割接口 (Priority: P3)

**Goal**: 实现 OAI-PMH v2.0 协议的 6 个标准动词，支持 Dublin Core 格式

**Independent Test**: 使用 OAI-PMH 验证工具（如 BASE Validator）测试接口

### Tests for User Story 3

- [x] T024 [P] [US3] 单元测试 Dublin Core 映射 `backend/tests/unit/test_dublin_core.py`
- [x] T025 [P] [US3] 集成测试 OAI-PMH 动词 `backend/tests/integration/test_oaipmh_verbs.py`

### Implementation for User Story 3

- [x] T026 [US3] 实现 Dublin Core 映射 `backend/app/services/oaipmh/dublin_core.py`
  - Article → Dublin Core 元素映射
  - XML 命名空间处理
  - 特殊字符转义
- [x] T027 [US3] 实现 OAI-PMH 协议处理 `backend/app/services/oaipmh/protocol.py`
  - 请求参数解析
  - 响应 XML 构建
  - 错误响应生成
- [x] T028 [US3] 实现 Identify 动词 `backend/app/services/oaipmh/protocol.py`
  - repositoryName, baseURL, protocolVersion
  - adminEmail, earliestDatestamp, granularity
- [x] T029 [US3] 实现 ListMetadataFormats 动词 `backend/app/services/oaipmh/protocol.py`
- [x] T030 [US3] 实现 ListSets 动词 `backend/app/services/oaipmh/protocol.py`
- [x] T031 [US3] 实现 GetRecord 动词 `backend/app/services/oaipmh/protocol.py`
- [x] T032 [US3] 实现 ListIdentifiers 动词 `backend/app/services/oaipmh/protocol.py`
  - 日期范围过滤 (from, until)
- [x] T033 [US3] 实现 ListRecords 动词 `backend/app/services/oaipmh/protocol.py`
  - 日期范围过滤
  - 完整元数据返回
- [x] T034 [US3] 实现 resumptionToken 分页 `backend/app/services/oaipmh/protocol.py`
  - Token 编码/解码 (Base64)
  - 游标分页 SQL
  - 每页 100 条限制
- [x] T035 [US3] 实现 OAI-PMH API 端点 `backend/app/api/oaipmh.py`
  - GET `/api/oai-pmh` - 统一入口（无版本前缀，符合 OAI-PMH 标准）
  - POST `/api/oai-pmh` - POST 方式支持
- [x] T036 [US3] 实现速率限制中间件 (60 req/min/IP) `backend/app/api/oaipmh.py`

**Checkpoint**: OAI-PMH 接口功能完整可测试

---

## Phase 6: User Story 4 - 失败处理与重试机制 (Priority: P4)

**Goal**: DOI 注册失败时自动重试，提供日志和通知

**Independent Test**: 模拟 Crossref API 超时，验证指数退避重试和失败通知

### Tests for User Story 4

- [ ] T037 [P] [US4] 单元测试重试逻辑 `backend/tests/unit/test_doi_worker.py`
- [ ] T038 [P] [US4] 集成测试任务队列 `backend/tests/integration/test_doi_task_queue.py`

### Implementation for User Story 4

- [x] T039 [US4] 实现数据库队列 Worker `backend/app/core/doi_worker.py`
  - 任务轮询 (SELECT FOR UPDATE SKIP LOCKED)
  - 任务执行和状态更新
  - asyncio 非阻塞轮询
- [x] T040 [US4] 实现指数退避重试 `backend/app/core/doi_worker.py`
  - 重试间隔: 1min, 5min, 30min, 2h
  - 最大重试次数: 4
  - 失败状态标记
- [x] T041 [US4] 实现审计日志记录 `backend/app/services/doi_service.py`
  - 请求参数记录 (脱敏)
  - 响应状态记录
  - 错误详情记录
- [x] T042 [US4] 实现失败通知邮件 `backend/app/core/doi_worker.py`
  - 邮件模板
  - 管理员邮箱配置
- [x] T043 [US4] 实现任务管理 API `backend/app/api/v1/doi.py`
  - GET `/api/v1/doi/tasks` - 任务列表
  - GET `/api/v1/doi/tasks/failed` - 失败任务
  - POST `/api/v1/doi/{article_id}/retry` - 手动重试
- [x] T044 [P] [US4] 创建 DOI API 客户端 `frontend/src/lib/api/doi.ts`
- [x] T045 [P] [US4] 创建 DOI 状态组件 `frontend/src/components/doi/DOIStatus.tsx`
- [x] T046 [P] [US4] 创建 DOI 任务列表组件 `frontend/src/components/doi/DOITaskList.tsx`
- [x] T047 [US4] 创建 DOI 任务管理页面 `frontend/src/app/(admin)/editor/doi-tasks/page.tsx`
- [x] T048 [US4] E2E 测试 DOI 任务管理 `frontend/tests/e2e/doi-tasks.spec.ts`

**Checkpoint**: 失败处理与管理界面功能完整可测试

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 跨 User Story 的改进

- [ ] T049 [P] 运行 quickstart.md 验证脚本
- [ ] T050 [P] 更新 API 文档 (OpenAPI)
- [ ] T051 [P] 代码清理和重构
- [ ] T052 安全加固 - 审核认证和授权
- [ ] T053 性能优化 - OAI-PMH 查询优化
- [ ] T054 添加系统健康检查端点

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 - 可立即开始
- **Foundational (Phase 2)**: 依赖 Setup 完成 - 阻塞所有 User Stories
- **User Stories (Phase 3-6)**: 依赖 Foundational 完成
  - US1 (P1): 可在 Foundational 后立即开始
  - US2 (P2): 可与 US1 并行，但独立测试
  - US3 (P3): 可与 US1/US2 并行
  - US4 (P4): 依赖 US1 (DOI 服务层)
- **Polish (Phase 7)**: 依赖所有所需 User Stories 完成

### User Story Dependencies

```
Foundational (Phase 2)
        │
        ├───────────────┬───────────────┐
        ▼               ▼               ▼
   US1 (P1)        US2 (P2)        US3 (P3)
   DOI 注册      Scholar Tags    OAI-PMH
        │               │               │
        └───────────────┼───────────────┘
                        │
                        ▼
                   US4 (P4)
                 失败处理 (依赖 US1)
```

### Parallel Opportunities

**Phase 1 Setup**:
```
T002 + T003 + T004 可并行
```

**Phase 2 Foundational**:
```
T007 + T008 可并行
T009 + T010 可并行
```

**Phase 3 US1**:
```
T011 + T012 测试可并行
```

**Phase 4 US2**:
```
T019 测试独立
T020 可在 T019 之后立即开始
```

**Phase 5 US3**:
```
T024 + T025 测试可并行
```

**Phase 6 US4**:
```
T037 + T038 测试可并行
T044 + T045 + T046 前端组件可并行
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational (CRITICAL)
3. 完成 Phase 3: User Story 1
4. **STOP and VALIDATE**: 测试 DOI 注册功能
5. 部署/演示 MVP

### Incremental Delivery

1. Setup + Foundational → 基础就绪
2. 添加 US1 → 测试 → 部署 (MVP!)
3. 添加 US2 → 测试 → 部署 (Google Scholar 适配)
4. 添加 US3 → 测试 → 部署 (OAI-PMH 接口)
5. 添加 US4 → 测试 → 部署 (完整功能)

---

## Summary

| Phase | User Story | 任务数 | 测试任务 | 实现任务 |
|-------|-----------|--------|---------|---------|
| 1 | Setup | 5 | 0 | 5 |
| 2 | Foundational | 5 | 0 | 5 |
| 3 | US1 DOI 注册 | 8 | 2 | 6 |
| 4 | US2 Scholar Tags | 5 | 1 | 4 |
| 5 | US3 OAI-PMH | 13 | 2 | 11 |
| 6 | US4 失败处理 | 12 | 2 | 10 |
| 7 | Polish | 6 | 0 | 6 |
| **Total** | | **54** | **7** | **47** |

---

## Notes

- [P] 任务 = 不同文件，无依赖
- [Story] 标签映射到具体 User Story
- 每个 User Story 应独立完成和测试
- 每个任务或逻辑组完成后提交
- 任何 Checkpoint 可停止验证
