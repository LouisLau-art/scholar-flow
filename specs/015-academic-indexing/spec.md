# Feature Specification: Academic Indexing & DOI Minting

**Feature Branch**: `015-academic-indexing`  
**Created**: 2026-01-30  
**Status**: Draft  
**Input**: User description: "学术标准化与索引集成 - DOI注册、OAI-PMH接口、Google Scholar适配"

## Clarifications

### Session 2026-01-30

- Q: OAI-PMH 接口是否需要认证？ → A: 完全公开（无需认证，仅限已发表文章）
- Q: 异步任务队列使用什么实现？ → A: 数据库队列（避免 Celery/Redis 依赖）
- Q: DOI 后缀格式如何生成？ → A: sf.{year}.{sequence} 格式（如 10.12345/sf.2026.00001）
- Q: 作者姓名格式如何处理？ → A: 按原始输入保留，不做自动转换
- Q: OAI-PMH 速率限制阈值？ → A: 60 请求/分钟/IP

## User Scenarios & Testing *(mandatory)*

<!--
  本功能实现学术期刊的标准化索引集成，包括：
  1. DOI 自动注册 (Crossref API)
  2. OAI-PMH v2.0 元数据收割接口
  3. Google Scholar 适配 (Highwire Press Meta Tags)
  4. 容错机制与失败重试
-->

### User Story 1 - DOI 自动注册 (Priority: P1)

作为期刊编辑，当我将稿件状态更新为"已发表"时，系统应自动向 Crossref 注册 DOI，
使文章获得永久性学术标识符，便于被引用和追踪。

**Why this priority**: DOI 是学术出版的核心标识符，没有 DOI 的文章无法被正规索引系统收录，
这是学术期刊的基础设施需求，必须优先实现。

**Independent Test**: 可通过发表一篇测试文章，验证 DOI 是否成功注册到 Crossref 测试环境，
并能通过 https://doi.org/[DOI] 解析到文章页面。

**Acceptance Scenarios**:

1. **Given** 稿件已通过终审并准备发表, **When** 编辑点击"发表"按钮, **Then** 系统自动调用 Crossref API 注册 DOI，并在文章详情页显示 DOI 链接
2. **Given** 文章元数据（标题、作者、摘要）已完整, **When** DOI 注册成功, **Then** 系统记录 DOI 到数据库，状态更新为 `doi_registered`
3. **Given** Crossref API 返回错误（如网络超时）, **When** 注册失败, **Then** 系统将任务加入重试队列，并通知编辑注册状态

---

### User Story 2 - Google Scholar 适配 (Priority: P2)

作为作者，我希望我的文章能被 Google Scholar 正确索引和展示，
包括标题、作者、摘要、引用信息等，以提高文章的可见度和引用率。

**Why this priority**: Google Scholar 是学术界最广泛使用的搜索引擎，
正确的元数据标签是被索引的前提条件，直接影响文章的学术影响力。

**Independent Test**: 可通过访问已发表文章页面，使用浏览器开发者工具检查 `<meta>` 标签，
验证 Highwire Press 标签是否正确生成（citation_title, citation_author, citation_doi 等）。

**Acceptance Scenarios**:

1. **Given** 文章已发表并有 DOI, **When** 用户访问文章详情页, **Then** 页面 HTML `<head>` 中包含完整的 Highwire Press Meta Tags（SSR 渲染）
2. **Given** 文章有多位作者, **When** 渲染页面, **Then** 每位作者生成独立的 `citation_author` 标签，顺序与作者列表一致
3. **Given** 文章有 PDF 附件, **When** 渲染页面, **Then** 生成 `citation_pdf_url` 标签指向 PDF 文件

---

### User Story 3 - OAI-PMH 元数据收割接口 (Priority: P3)

作为图书馆或索引服务提供商，我希望通过标准的 OAI-PMH 协议收割期刊元数据，
以便将文章纳入机构知识库或学术数据库。

**Why this priority**: OAI-PMH 是学术资源互操作的国际标准，支持 CNKI、万方、
机构仓储等系统的自动收割，是期刊进入主流索引的必要条件。

**Independent Test**: 可使用 OAI-PMH 验证工具（如 BASE Validator）测试接口，
验证返回的 Dublin Core 元数据符合 OAI-PMH v2.0 规范。

**Acceptance Scenarios**:

1. **Given** 系统有已发表文章, **When** 收割器发送 `ListRecords` 请求, **Then** 返回 Dublin Core 格式的元数据 XML，包含所有已发表文章
2. **Given** 收割器需要增量更新, **When** 发送带 `from` 和 `until` 参数的请求, **Then** 仅返回指定日期范围内更新的记录
3. **Given** 记录数量超过单页限制, **When** 返回部分记录, **Then** 包含 `resumptionToken` 供分页获取剩余记录
4. **Given** 收割器请求单条记录, **When** 发送 `GetRecord` 请求并提供 `identifier`, **Then** 返回该记录的完整 Dublin Core 元数据

---

### User Story 4 - 失败处理与重试机制 (Priority: P4)

作为系统管理员，我希望 DOI 注册失败时系统能自动重试，
并提供详细的日志和通知，确保不会遗漏任何注册任务。

**Why this priority**: 外部 API 调用不可避免会遇到网络问题或服务中断，
健壮的重试机制是保证系统可靠性的基础。

**Independent Test**: 可通过模拟 Crossref API 超时，验证系统是否按指数退避策略重试，
并在最终失败后发送通知邮件给管理员。

**Acceptance Scenarios**:

1. **Given** DOI 注册请求失败（网络超时）, **When** 系统检测到失败, **Then** 将任务加入重试队列，按指数退避策略（1min, 5min, 30min, 2h）重试
2. **Given** 重试次数达到上限（4次）, **When** 仍然失败, **Then** 标记任务为 `failed`，发送邮件通知管理员
3. **Given** 管理员收到失败通知, **When** 访问管理后台, **Then** 可查看失败任务详情并手动触发重试
4. **Given** 任何 DOI 操作, **When** 操作完成, **Then** 系统记录详细日志（时间戳、请求参数、响应状态、错误信息）

---

### Edge Cases

- **元数据不完整**: 文章缺少必填字段（如作者信息）时，DOI 注册应提前校验并拒绝，提示编辑补充信息
- **DOI 冲突**: 尝试注册已存在的 DOI 时，系统应识别冲突并更新而非创建
- **OAI-PMH 恶意请求**: 大量快速请求应受速率限制保护（60 请求/分钟/IP），避免服务过载
- **作者姓名格式**: 按作者原始输入保留，不做中英文自动转换
- **特殊字符转义**: 标题或摘要中的 XML 特殊字符需正确转义

## Requirements *(mandatory)*

### Functional Requirements

#### DOI 注册
- **FR-001**: 系统 MUST 在文章发表时自动触发 DOI 注册流程
- **FR-002**: 系统 MUST 调用 Crossref Deposit API 提交元数据 XML
- **FR-003**: 系统 MUST 支持 DOI 前缀配置（期刊特定前缀，如 `10.12345`），后缀格式为 `sf.{year}.{sequence}`（如 `10.12345/sf.2026.00001`）
- **FR-004**: 系统 MUST 在注册成功后将 DOI 保存到文章记录
- **FR-005**: 系统 MUST 支持 DOI 元数据更新（文章信息修正时）

#### Google Scholar 适配
- **FR-006**: 系统 MUST 在文章详情页 SSR 渲染 Highwire Press Meta Tags
- **FR-007**: 系统 MUST 生成以下必需标签: `citation_title`, `citation_author`, `citation_publication_date`, `citation_journal_title`, `citation_doi`
- **FR-008**: 系统 MUST 生成以下可选标签（如有数据）: `citation_pdf_url`, `citation_abstract`, `citation_volume`, `citation_issue`, `citation_firstpage`, `citation_lastpage`
- **FR-009**: 系统 MUST 确保标签内容与页面可见内容一致

#### OAI-PMH 接口
- **FR-010**: 系统 MUST 实现 OAI-PMH v2.0 协议的 6 个标准动词: `Identify`, `ListMetadataFormats`, `ListSets`, `ListIdentifiers`, `ListRecords`, `GetRecord`（完全公开，无需认证）
- **FR-011**: 系统 MUST 支持 Dublin Core (`oai_dc`) 元数据格式
- **FR-012**: 系统 MUST 支持日期范围过滤 (`from`, `until` 参数)
- **FR-013**: 系统 MUST 实现分页机制 (`resumptionToken`)，每页最多 100 条记录
- **FR-014**: 系统 MUST 返回符合 OAI-PMH XML Schema 的响应
- **FR-014a**: 系统 MUST 实现速率限制（60 请求/分钟/IP）防止滥用

#### 失败处理
- **FR-015**: 系统 MUST 实现异步任务队列处理 DOI 注册（使用数据库队列，避免 Celery/Redis 依赖）
- **FR-016**: 系统 MUST 实现指数退避重试策略（最多 4 次重试）
- **FR-017**: 系统 MUST 在最终失败时发送邮件通知管理员
- **FR-018**: 系统 MUST 记录所有 DOI 操作的详细日志
- **FR-019**: 系统 MUST 提供管理界面查看和手动重试失败任务

### Key Entities

- **DOIRegistration**: DOI 注册记录，包含 article_id, doi, status (pending/registered/failed), attempts, created_at, registered_at, error_message
- **DOITask**: DOI 任务队列项，包含 registration_id, scheduled_at, retry_count, last_error
- **OAIRecord**: OAI-PMH 记录映射，包含 article_id, oai_identifier, datestamp, set_spec

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 已发表文章在 5 分钟内完成 DOI 注册（正常情况）
- **SC-002**: DOI 注册成功率 >= 99%（排除 Crossref 服务中断）
- **SC-003**: OAI-PMH 接口响应时间 < 2 秒（100 条记录以内）
- **SC-004**: Google Scholar 元数据标签通过 Structured Data Testing Tool 验证
- **SC-005**: 失败任务在 24 小时内完成重试或人工处理
- **SC-006**: 所有 DOI 操作有完整审计日志

## Technical Notes *(implementation guidance)*

### Crossref API 集成
- 使用 Crossref Deposit API v4.8+
- 测试环境: `https://test.crossref.org/servlet/deposit`
- 生产环境: `https://doi.crossref.org/servlet/deposit`
- 认证: HTTP Basic Auth (depositor credentials)
- 请求格式: `application/vnd.crossref.deposit+xml`

### Highwire Press Meta Tags 示例
```html
<meta name="citation_title" content="Article Title">
<meta name="citation_author" content="Author One">
<meta name="citation_author" content="Author Two">
<meta name="citation_publication_date" content="2026/01/30">
<meta name="citation_journal_title" content="Scholar Flow Journal">
<meta name="citation_doi" content="10.12345/sf.2026.001">
<meta name="citation_pdf_url" content="https://example.com/articles/001.pdf">
```

### OAI-PMH 端点
- Base URL: `/api/oai-pmh`
- 示例请求: `/api/oai-pmh?verb=ListRecords&metadataPrefix=oai_dc`

### 依赖项
- **后端**: `httpx` (HTTP 客户端), `lxml` (XML 处理), 数据库队列 (异步任务，基于 PostgreSQL)
- **前端**: Next.js `generateMetadata` (SSR Meta Tags)
