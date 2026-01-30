# Research: Academic Indexing & DOI Minting

**Feature**: 015-academic-indexing  
**Date**: 2026-01-30  
**Status**: Complete

## 1. Crossref Deposit API

### Decision
使用 Crossref Deposit API v5.4.0，通过 HTTP POST multipart/form-data 提交元数据 XML。

### Rationale
- 官方推荐的最新 Schema 版本
- 支持异步处理，适合后台任务队列模式
- 明确的错误处理和状态查询机制

### Key Details

| 项目 | 值 |
|-----|-----|
| **测试端点** | `https://test.crossref.org/servlet/deposit` |
| **生产端点** | `https://doi.crossref.org/servlet/deposit` |
| **Schema 版本** | 5.4.0 |
| **Schema URL** | `https://crossref.org/schemas/crossref5.4.0.xsd` |
| **命名空间** | `http://www.crossref.org/schema/5.4.0` |
| **认证方式** | HTTP POST with form fields: `login_id`, `login_passwd` |
| **文件字段** | `fname` (XML 文件内容) |
| **操作类型** | `operation=doMDUpload` |

### Journal Article XML 结构

```
doi_batch (根元素)
├── head
│   ├── doi_batch_id     # 唯一批次 ID
│   ├── timestamp        # 时间戳 (每次更新递增)
│   ├── depositor
│   │   ├── depositor_name
│   │   └── email_address
│   └── registrant
└── body
    └── journal
        ├── journal_metadata
        │   ├── full_title     # 期刊全名 (必需)
        │   └── issn           # ISSN
        ├── journal_issue (可选)
        └── journal_article
            ├── titles/title   # 文章标题 (必需)
            ├── contributors   # 作者
            ├── publication_date
            └── doi_data
                ├── doi        # DOI (必需)
                └── resource   # 落地页 URL (必需)
```

### 响应处理
- HTTP 200: 文件已接收入队（不代表 DOI 已创建）
- HTTP 429: 队列已满，需等待后重试
- HTTP 503: 服务不可用
- 状态查询: 提交后 5-10 分钟再查询
- 队列限制: 每用户 10,000 待处理提交

### Alternatives Considered
- REST API: 不存在，仅支持 XML Deposit
- 第三方库: 无成熟的 Python 库，需自行实现

---

## 2. OAI-PMH v2.0 Protocol

### Decision
实现完整 OAI-PMH v2.0 协议，支持 Dublin Core (oai_dc) 格式，使用无状态 resumptionToken。

### Rationale
- 国际学术资源互操作标准
- Dublin Core 是必须支持的最小元数据格式
- 无状态 Token 简化实现，无需服务端会话存储

### 六个标准动词

| 动词 | 必需参数 | 可选参数 |
|-----|---------|---------|
| Identify | 无 | 无 |
| ListMetadataFormats | 无 | identifier |
| ListSets | 无 | resumptionToken |
| GetRecord | identifier, metadataPrefix | 无 |
| ListIdentifiers | metadataPrefix | from, until, set, resumptionToken |
| ListRecords | metadataPrefix | from, until, set, resumptionToken |

### Dublin Core 映射

| DC 元素 | 论文字段 |
|---------|---------|
| dc:title | 标题 |
| dc:creator | 作者（可重复）|
| dc:subject | 关键词 |
| dc:description | 摘要 |
| dc:publisher | 期刊名 |
| dc:date | 发表日期 |
| dc:type | "Article" |
| dc:identifier | DOI URL |
| dc:language | 语言代码 |

### resumptionToken 编码 (Base64)

```
m=oai_dc           # metadataPrefix
f=2024-01-01       # from (可选)
u=2024-12-31       # until (可选)
t=2024-06-15T10:30:00Z  # 最后记录时间戳
i=oai:repo:12345   # 最后记录标识符
c=100              # 当前游标位置
```

### XML 命名空间

```xml
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

<oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
           xmlns:dc="http://purl.org/dc/elements/1.1/">
```

### 错误代码

| 代码 | 含义 |
|-----|------|
| badVerb | 无效动词 |
| badArgument | 参数错误 |
| cannotDisseminateFormat | 不支持的格式 |
| idDoesNotExist | 标识符不存在 |
| noRecordsMatch | 无匹配记录 |
| badResumptionToken | Token 无效 |

---

## 3. Database Job Queue

### Decision
使用 PostgreSQL 实现轻量级任务队列，通过 `SELECT FOR UPDATE SKIP LOCKED` 实现原子任务认领。

### Rationale
- 避免引入 Celery/Redis 依赖
- 充分利用现有 Supabase PostgreSQL
- 对于中小规模（<10000 文章）足够高效
- 简化部署和运维

### 表结构

```sql
CREATE TYPE doi_task_status AS ENUM ('pending', 'processing', 'completed', 'failed');

CREATE TABLE doi_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES articles(id),
    task_type VARCHAR(50) NOT NULL,  -- 'register', 'update'
    status doi_task_status DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 4,
    run_at TIMESTAMPTZ DEFAULT NOW(),
    locked_at TIMESTAMPTZ,
    locked_by VARCHAR(100),
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_doi_tasks_pending ON doi_tasks (run_at ASC)
WHERE status = 'pending';
```

### 原子任务认领 SQL

```sql
WITH next_task AS (
    SELECT id FROM doi_tasks
    WHERE status = 'pending' AND run_at <= NOW()
    ORDER BY run_at ASC
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
UPDATE doi_tasks SET
    status = 'processing',
    locked_at = NOW(),
    locked_by = :worker_id,
    attempts = attempts + 1
FROM next_task
WHERE doi_tasks.id = next_task.id
RETURNING doi_tasks.*;
```

### 指数退避间隔

| 重试次数 | 延迟 |
|---------|------|
| 1 | 1 分钟 |
| 2 | 5 分钟 |
| 3 | 30 分钟 |
| 4 | 2 小时 |
| >4 | 标记为 failed |

### Worker 轮询策略
- 有任务时: 立即继续
- 无任务时: sleep 5 秒
- 使用 asyncio 实现非阻塞轮询

### 状态转换

```
pending → processing → completed
              ↓
         (failure)
              ↓
    attempts < max: pending (scheduled retry)
    attempts >= max: failed
```

---

## 4. Google Scholar Meta Tags

### Decision
使用 Next.js `generateMetadata` SSR 渲染 Highwire Press Meta Tags。

### Rationale
- Google Scholar 官方推荐格式
- SSR 确保爬虫可见
- Next.js 14 内置支持

### 必需标签

```html
<meta name="citation_title" content="...">
<meta name="citation_author" content="...">  <!-- 每位作者一个 -->
<meta name="citation_publication_date" content="YYYY/MM/DD">
<meta name="citation_journal_title" content="...">
<meta name="citation_doi" content="10.xxxx/...">
```

### 可选标签

```html
<meta name="citation_pdf_url" content="...">
<meta name="citation_abstract" content="...">
<meta name="citation_volume" content="...">
<meta name="citation_issue" content="...">
<meta name="citation_firstpage" content="...">
<meta name="citation_lastpage" content="...">
```

---

## Summary

| 技术决策 | 选择 | 状态 |
|---------|------|------|
| Crossref API | v5.4.0 XML Deposit | ✅ 已确定 |
| OAI-PMH | v2.0 + Dublin Core | ✅ 已确定 |
| 任务队列 | PostgreSQL SKIP LOCKED | ✅ 已确定 |
| Meta Tags | Highwire Press (SSR) | ✅ 已确定 |
| 退避策略 | 1m, 5m, 30m, 2h | ✅ 已确定 |
| 速率限制 | 60 req/min/IP | ✅ 已确定 |
