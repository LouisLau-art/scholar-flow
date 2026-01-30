# Quickstart: Academic Indexing & DOI Minting

**Feature**: 015-academic-indexing  
**Date**: 2026-01-30

## Prerequisites

### Environment Variables

```bash
# Crossref API 配置
CROSSREF_DEPOSITOR_EMAIL=your-email@example.com
CROSSREF_DEPOSITOR_PASSWORD=your-password
CROSSREF_DOI_PREFIX=10.12345
CROSSREF_API_URL=https://test.crossref.org/servlet/deposit  # 测试环境

# 期刊信息
JOURNAL_TITLE="Scholar Flow Journal"
JOURNAL_ISSN=1234-5678

# 邮件通知 (可选)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
ADMIN_EMAIL=admin@example.com
```

### Dependencies

```bash
# 后端
pip install httpx lxml

# 前端 (已有)
# Next.js 14.2 generateMetadata 内置支持
```

## Quick Verification

### 1. Database Migration

```bash
# 应用迁移
supabase migration new doi_registration
# 将 data-model.md 中的 SQL 复制到迁移文件
supabase db push
```

### 2. DOI Registration Test

```bash
# 1. 创建测试文章 (需要已发表状态)
curl -X POST http://localhost:8000/api/v1/doi/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"article_id": "your-article-uuid"}'

# 2. 查询注册状态
curl http://localhost:8000/api/v1/doi/your-article-uuid \
  -H "Authorization: Bearer $TOKEN"
```

### 3. OAI-PMH Interface Test

```bash
# Identify (仓库信息)
curl "http://localhost:8000/api/oai-pmh?verb=Identify"

# ListRecords (列出记录)
curl "http://localhost:8000/api/oai-pmh?verb=ListRecords&metadataPrefix=oai_dc"

# GetRecord (单条记录)
curl "http://localhost:8000/api/oai-pmh?verb=GetRecord&identifier=oai:scholarflow:article:123&metadataPrefix=oai_dc"
```

### 4. Google Scholar Meta Tags Test

```bash
# 访问已发表文章页面，检查 HTML head
curl http://localhost:3000/articles/your-article-id | grep "citation_"

# 应看到类似:
# <meta name="citation_title" content="...">
# <meta name="citation_author" content="...">
# <meta name="citation_doi" content="10.12345/sf.2026.00001">
```

## Development Workflow

### Backend

```bash
cd backend

# 运行测试
pytest tests/unit/test_crossref_xml.py -v
pytest tests/integration/test_doi_registration.py -v

# 启动开发服务器
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend

# 运行测试
npm run test -- citation.test.ts

# 启动开发服务器
pnpm dev
```

### DOI Worker (后台任务)

```bash
# 开发时可手动运行 worker
python -m app.core.doi_worker

# 生产环境使用 systemd 或 supervisor 管理
```

## Key Files

| 文件 | 用途 |
|-----|------|
| `backend/app/services/crossref_client.py` | Crossref API 客户端 |
| `backend/app/services/doi_service.py` | DOI 业务逻辑 |
| `backend/app/core/doi_worker.py` | 任务队列 Worker |
| `backend/app/api/v1/doi.py` | DOI API 端点 |
| `backend/app/api/v1/oaipmh.py` | OAI-PMH 端点 |
| `frontend/src/lib/metadata/citation.ts` | Meta Tags 生成 |
| `frontend/src/app/articles/[id]/page.tsx` | 文章详情页 (含 Meta) |

## Validation Checklist

- [ ] Crossref 测试环境账号已配置
- [ ] 数据库迁移已应用
- [ ] 后端单元测试通过
- [ ] OAI-PMH Identify 返回正确 XML
- [ ] 文章页面包含 citation_* 标签
- [ ] DOI 任务队列正常运行
