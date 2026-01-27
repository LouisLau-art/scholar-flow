# API Contracts: Content Ecosystem

## 公开查询接口 (Public API)

### 1. 搜索文章
- **Endpoint**: `GET /api/v1/search`
- **Params**: 
  - `q`: string (关键词)
  - `mode`: 'articles' | 'journals'
- **Response**:
```json
{
  "results": [
    {
      "id": "uuid",
      "title": "...",
      "abstract": "...",
      "doi": "...",
      "journal_name": "..."
    }
  ]
}
```

### 2. 获取文章详情
- **Endpoint**: `GET /api/v1/articles/{id}`
- **Response**: 返回完整的稿件元数据及 PDF 签名链接。

### 3. 获取期刊详情
- **Endpoint**: `GET /api/v1/journals/{slug}`
- **Response**: 返回期刊基本信息及旗下 `published` 状态的文章列表。
