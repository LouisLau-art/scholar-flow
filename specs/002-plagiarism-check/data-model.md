# Data Model: Manuscript Plagiarism Check

## 实体定义 (PlagiarismReports)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid (PK) | 查重报告唯一标识 |
| manuscript_id | uuid (FK, Unique) | 关联稿件，确保 1:1 关系 |
| external_id | text | 外部 API (iThenticate) 的任务 ID |
| similarity_score | float4 | 查重率 (0.0 - 1.0) |
| report_url | text | Supabase Storage 路径 |
| status | text | 枚举: `pending`, `running`, `completed`, `failed` |
| retry_count | int2 | 自动重试计数 |
| error_log | text | 记录 API 报错信息，方便 Debug |
| created_at | timestamptz | 任务发起时间 |
| updated_at | timestamptz | 状态更新时间 |

## 状态联动逻辑
1. **触发**: `Manuscripts` 状态变更为 `submitted` 时，系统自动向 `PlagiarismReports` 插入 `pending` 记录。
2. **拦截**: 
   - 如果 `similarity_score > 0.3`，系统自动更新 `Manuscripts.status = 'high_similarity'`。
   - 编辑收到通知后，可选择“维持现状”或“直接退回”。
3. **重试**: `status = 'failed'` 且 `retry_count >= 3` 时，显示手动重试入口。
