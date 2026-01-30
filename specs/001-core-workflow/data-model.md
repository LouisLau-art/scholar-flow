# Data Model: ScholarFlow Core Workflow

## 核心实体 (Supabase / PostgreSQL)

### 1. Manuscripts (稿件)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid (PK) | |
| title | text | |
| abstract | text | |
| file_path | text | Supabase Storage 路径 |
| dataset_url | text | 外部数据集链接 (可选) |
| source_code_url | text | 代码仓库链接 (可选) |
| author_id | uuid (FK) | 关联 Users.id |
| editor_id | uuid (FK) | 关联 Users.id |
| status | text | 枚举: `draft`, `submitted`, `returned_for_revision`, `under_review`, `approved`, `pending_payment`, `published`, `rejected` |
| kpi_owner_id | uuid (FK) | 质检人/责任人 |
| created_at | timestamptz | |

### 2. ReviewReports (审稿报告)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid (PK) | |
| manuscript_id | uuid (FK) | |
| reviewer_id | uuid (FK) | |
| token | text | 随机高强度 Token |
| expiry_date | timestamptz | 默认创建时间 + 14 天 |
| status | text | 枚举: `invited`, `accepted`, `completed`, `expired` |
| content | text | 审稿评价 |
| score | int4 | 评分 (1-5) |

### 3. Invoices (财务账单)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid (PK) | |
| manuscript_id | uuid (FK) | |
| amount | numeric | |
| pdf_url | text | 自动生成的 PDF 文件路径 |
| status | text | 枚举: `unpaid`, `paid` |
| confirmed_at | timestamptz | 财务手动确认时间 |

## 状态流转 (State Machine)
1. **作者提交**: `draft` -> `submitted`
2. **编辑质检**: 
   - 合格 -> `under_review`
   - 不合格 -> `returned_for_revision` -> (作者修改) -> `submitted`
3. **审稿阶段**: `under_review` -> (终审通过) -> `pending_payment`
4. **上线控制**: `pending_payment` -> (财务确认 `paid`) -> `published`
