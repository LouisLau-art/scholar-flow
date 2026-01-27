# Data Model: Content Ecosystem

## 实体定义

### 1. Journals (期刊表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid (PK) | 期刊唯一标识 |
| title | text | 期刊名称 (如: Frontiers in AI) |
| slug | text (Unique) | URL 友好名 (如: ai-ethics) |
| description | text | 期刊简介 |
| issn | text | 国际标准期刊号 |
| impact_factor | float4 | 影响因子 |
| cover_url | text | 封面图存储路径 |
| created_at | timestamptz | 创建时间 |

### 2. Manuscripts (稿件表扩展)
在 001 基础上补齐以下发布相关字段：
| 字段 | 类型 | 说明 |
|------|------|------|
| journal_id | uuid (FK) | 关联的期刊 ID |
| doi | text (Unique) | 数字对象标识符 (如: 10.1234/sf.2026.001) |
| published_at | timestamptz | 正式上线时间 |
| version | int2 | 版本号 (默认 1) |

## 关系
- **Journal : Manuscript** = 1 : N (一个期刊包含多篇文章)
- **Manuscript : PlagiarismReport** = 1 : 1
