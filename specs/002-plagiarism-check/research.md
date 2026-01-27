# Research: Manuscript Plagiarism Check

## 决策记录

### 1. 外部查重 API 选型
- **Decision**: 使用 **Crossref Similarity Check (iThenticate)**。
- **Rationale**: 学术界最权威的查重服务，提供结构化 API 访问。
- **Integration**: 后端通过异步 `httpx` 客户端封装 `CrossrefClient`。

### 2. 异步处理方案 (Async Workflow)
- **Decision**: 使用 **FastAPI BackgroundTasks**。
- **Rationale**: 符合“拒绝过度工程”原则。在日活未突破万级前，无需引入 Celery/Redis 等复杂组件。FastAPI 内置的后台任务足以处理分钟级的 API 轮询。
- **Fallback**: 如果 API 响应极慢，通过定时 Cron 任务（每 5 分钟）扫描 `pending` 状态的报告。

### 3. 幂等性与重试逻辑
- **Decision**: `manuscript_id` 在 `PlagiarismReports` 表中设置唯一索引。
- **Rationale**: 确保每份稿件同一版本只发起一次有效查重。
- **Retry**: 
  - 自动重试：基于指数退避算法（如 1min, 5min, 15min）。
  - 手动重试：仅当状态为 `failed` 时，API 允许编辑重新触发。

### 4. 查重报告安全性
- **Decision**: 报告 PDF 存储在 Supabase 私有 Bucket，前端通过带签名的临时 URL 下载。
- **Rationale**: 查重报告包含版权敏感信息，严禁公共访问。
