# Data Model: Academic Indexing & DOI Minting

**Feature**: 015-academic-indexing  
**Date**: 2026-01-30

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────────┐
│    articles     │       │   doi_registrations │
├─────────────────┤       ├─────────────────────┤
│ id (PK)         │◄──────│ article_id (FK)     │
│ title           │       │ id (PK)             │
│ doi             │       │ doi                 │
│ status          │       │ status              │
│ published_at    │       │ attempts            │
│ ...             │       │ error_message       │
└─────────────────┘       │ registered_at       │
                          └─────────────────────┘
                                    │
                                    │ 1:N
                                    ▼
                          ┌─────────────────────┐
                          │     doi_tasks       │
                          ├─────────────────────┤
                          │ id (PK)             │
                          │ registration_id (FK)│
                          │ task_type           │
                          │ status              │
                          │ run_at              │
                          │ attempts            │
                          └─────────────────────┘
```

## Entities

### 1. DOIRegistration

DOI 注册记录，关联到已发表文章。

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 主键 |
| article_id | UUID | FK → articles.id, NOT NULL, UNIQUE | 关联文章 |
| doi | VARCHAR(255) | UNIQUE | 注册的 DOI (如 10.12345/sf.2026.00001) |
| status | ENUM | NOT NULL, DEFAULT 'pending' | 注册状态 |
| attempts | INTEGER | NOT NULL, DEFAULT 0 | 尝试次数 |
| crossref_batch_id | VARCHAR(255) | | Crossref 批次 ID |
| error_message | TEXT | | 最后错误信息 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |
| registered_at | TIMESTAMPTZ | | 注册成功时间 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 更新时间 |

**Status Enum**: `pending`, `submitting`, `registered`, `failed`

**State Transitions**:
```
pending → submitting → registered
              ↓
           failed (if max attempts reached)
              ↓
           pending (if manually retried)
```

### 2. DOITask

DOI 任务队列项，用于异步处理和重试。

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 主键 |
| registration_id | UUID | FK → doi_registrations.id, NOT NULL | 关联注册记录 |
| task_type | VARCHAR(50) | NOT NULL | 任务类型: 'register', 'update' |
| status | ENUM | NOT NULL, DEFAULT 'pending' | 任务状态 |
| priority | INTEGER | NOT NULL, DEFAULT 0 | 优先级 (越高越先) |
| run_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 计划执行时间 |
| locked_at | TIMESTAMPTZ | | 锁定时间 |
| locked_by | VARCHAR(100) | | 锁定的 Worker ID |
| attempts | INTEGER | NOT NULL, DEFAULT 0 | 已尝试次数 |
| max_attempts | INTEGER | NOT NULL, DEFAULT 4 | 最大尝试次数 |
| last_error | TEXT | | 最后错误详情 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |
| completed_at | TIMESTAMPTZ | | 完成时间 |

**Status Enum**: `pending`, `processing`, `completed`, `failed`

**Task Types**:
- `register`: 首次 DOI 注册
- `update`: DOI 元数据更新

### 3. DOIAuditLog

DOI 操作审计日志。

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 主键 |
| registration_id | UUID | FK → doi_registrations.id | 关联注册记录 |
| action | VARCHAR(50) | NOT NULL | 操作类型 |
| request_payload | JSONB | | 请求参数 (脱敏) |
| response_status | INTEGER | | HTTP 状态码 |
| response_body | TEXT | | 响应内容 (截断) |
| error_details | TEXT | | 错误详情 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |
| created_by | UUID | FK → auth.users.id | 操作人 |

**Action Types**: `submit`, `query_status`, `retry`, `cancel`

## Existing Entity Updates

### articles (已存在)

添加字段:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| doi | VARCHAR(255) | UNIQUE | 文章 DOI |
| doi_registered_at | TIMESTAMPTZ | | DOI 注册时间 |

## Indexes

```sql
-- DOI 任务队列优化
CREATE INDEX idx_doi_tasks_pending ON doi_tasks (run_at ASC)
WHERE status = 'pending';

-- 卡死任务检测
CREATE INDEX idx_doi_tasks_stale ON doi_tasks (locked_at)
WHERE status = 'processing';

-- 按文章查询注册状态
CREATE INDEX idx_doi_registrations_article ON doi_registrations (article_id);

-- 审计日志查询
CREATE INDEX idx_doi_audit_log_registration ON doi_audit_log (registration_id, created_at DESC);
```

## Validation Rules

### DOIRegistration
- `article_id` 必须关联已发表文章 (status = 'published')
- `doi` 格式: `^10\.\d{4,9}/[-._;()/:A-Z0-9]+$` (不区分大小写)

### DOITask
- `run_at` 不能早于 `created_at`
- `attempts` 不能超过 `max_attempts`
- `locked_at` 存在时 `status` 必须为 `processing`

## Migration SQL Preview

```sql
-- 创建枚举类型
CREATE TYPE doi_registration_status AS ENUM ('pending', 'submitting', 'registered', 'failed');
CREATE TYPE doi_task_status AS ENUM ('pending', 'processing', 'completed', 'failed');

-- DOI 注册表
CREATE TABLE doi_registrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,
    doi VARCHAR(255) UNIQUE,
    status doi_registration_status NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    crossref_batch_id VARCHAR(255),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    registered_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- DOI 任务队列
CREATE TABLE doi_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_id UUID NOT NULL REFERENCES doi_registrations(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL,
    status doi_task_status NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 0,
    run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    locked_at TIMESTAMPTZ,
    locked_by VARCHAR(100),
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 4,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- 审计日志
CREATE TABLE doi_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_id UUID REFERENCES doi_registrations(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    request_payload JSONB,
    response_status INTEGER,
    response_body TEXT,
    error_details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id)
);

-- 更新 articles 表
ALTER TABLE articles ADD COLUMN IF NOT EXISTS doi VARCHAR(255) UNIQUE;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS doi_registered_at TIMESTAMPTZ;
```
