# Data Model: GAP-P1-01 Finance Real Invoices Sync

## Overview

本特性不新增核心业务表，重点是把现有账单数据转成可筛选、可导出的 Finance 读模型，并补齐并发与审计规则。

核心思路：
- `public.invoices` 作为唯一支付事实源；
- 通过读模型 `effective_status` 兼容历史 `waived` 数据；
- 支付确认继续写 `invoices`，并同步写 `status_transition_logs.payload` 做审计留痕。

## Entities

### 1. InvoiceRecord（已有）

**Table**: `public.invoices`

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | 账单主键 |
| `manuscript_id` | UUID | Yes | 关联稿件（唯一） |
| `amount` | NUMERIC(10,2) | Yes | APC 金额 |
| `status` | TEXT | Yes | 原始支付状态（`unpaid/paid/waived` 或历史值） |
| `confirmed_at` | TIMESTAMPTZ | No | 确认支付时间 |
| `invoice_number` | TEXT | No | 账单编号（Feature 026） |
| `pdf_path` | TEXT | No | PDF 存储路径 |
| `pdf_generated_at` | TIMESTAMPTZ | No | PDF 生成时间 |
| `pdf_error` | TEXT | No | PDF 生成错误信息 |
| `created_at` | TIMESTAMPTZ | Yes | 创建时间 |
| `deleted_at` | TIMESTAMPTZ | No | 软删时间（保留字段） |

**Validation Rules**
- `amount >= 0`（业务约束）。
- `status` 读写时统一小写处理。
- `manuscript_id` 全局唯一（保证“一个稿件一个账单”幂等）。

### 2. FinanceInvoiceRow（读模型，新增）

**Source**: `invoices` + `manuscripts` + `user_profiles`（仅展示所需字段）

| Field | Type | Description |
|---|---|---|
| `invoice_id` | UUID | 对应 `invoices.id` |
| `manuscript_id` | UUID | 对应 `invoices.manuscript_id` |
| `invoice_number` | string/null | 账单编号 |
| `manuscript_title` | string | 稿件标题（缺失时展示占位） |
| `authors` | string/null | 作者展示文本（优先 `invoice_metadata.authors`） |
| `amount` | number | APC 金额 |
| `currency` | string | 当前固定 `USD` |
| `raw_status` | string | 原始 `invoices.status` |
| `effective_status` | enum | 归一化状态：`unpaid/paid/waived` |
| `confirmed_at` | datetime/null | 支付确认时间 |
| `updated_at` | datetime | 列表展示“最近更新时间”（优先 confirmed_at，否则稿件/账单更新时间） |
| `payment_gate_blocked` | boolean | 是否阻塞发布（`amount>0 && effective_status not in paid/waived`） |

**Derived Rule: effective_status**
- 若 `amount <= 0` 或 `raw_status == 'waived'` -> `waived`
- 若 `raw_status == 'paid'` -> `paid`
- 其他情况 -> `unpaid`

### 3. FinanceListQuery（请求模型，新增）

**Transport**: Query Params (`GET /api/v1/editor/finance/invoices`)

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | enum(`all`,`unpaid`,`paid`,`waived`) | No | 默认 `all` |
| `q` | string | No | 搜索关键词（账单号/稿件标题） |
| `page` | integer | No | 默认 1，最小 1 |
| `page_size` | integer | No | 默认 20，范围 1..100 |
| `sort_by` | enum(`updated_at`,`amount`,`status`) | No | 默认 `updated_at` |
| `sort_order` | enum(`asc`,`desc`) | No | 默认 `desc` |

### 4. ReconciliationExportBatch（导出快照，读模型，新增）

**Transport**: `GET /api/v1/editor/finance/invoices/export`（CSV）

| Field | Type | Description |
|---|---|---|
| `snapshot_at` | datetime | 导出快照时间（响应头） |
| `status_filter` | string | 当前筛选 |
| `row_count` | integer | 导出记录数 |
| `empty` | boolean | 是否空结果导出 |

说明：MVP 不强制新增导出批次持久化表，导出批次为“请求期瞬时模型”。

### 5. PaymentStatusAuditEntry（复用表）

**Table**: `public.status_transition_logs`（已有）

| Field | Type | Description |
|---|---|---|
| `manuscript_id` | UUID | 关联稿件 |
| `from_status` | TEXT | 本次可写 `invoice:{before}` |
| `to_status` | TEXT | 本次可写 `invoice:{after}` |
| `changed_by` | UUID | 操作人 |
| `comment` | TEXT | 可读动作摘要 |
| `payload` | JSONB | `action`, `invoice_id`, `before_status`, `after_status`, `source` |
| `created_at` | TIMESTAMPTZ | 变更时间 |

## State Transitions

### Invoice Payment Transition (MVP)

1. `unpaid -> paid`  
   - 触发：`POST /api/v1/editor/invoices/confirm`
2. `paid -> paid`（幂等）  
   - 触发：重复确认支付，返回 `already_paid=true`
3. `waived -> waived`（默认不允许通过“确认支付”修改）  
   - Finance UI 仅做筛选展示，不对 waived 执行 Mark Paid

### Concurrent Update Handling

- 客户端可携带 `expected_status`。
- 后端执行条件更新：`UPDATE ... WHERE manuscript_id=? AND status=?`。
- 若命中 0 行，返回 `409 Conflict`（表示状态已被其他入口更新）。

## Relationships

- `InvoiceRecord (1) <-> (1) Manuscript`：通过 `manuscript_id` 唯一关联。
- `Manuscript (1) <-> (N) PaymentStatusAuditEntry`：同一稿件可有多次财务变更审计。
- `ReconciliationExportBatch` 来源于 `FinanceListQuery` + `FinanceInvoiceRow[]`。

## Access Rules

- `editor/admin`：可读 Finance 列表、导出、确认支付。
- 其他角色：统一拒绝（403）。
- 未登录：统一拒绝（401）。

## Indexing Suggestions

- `public.invoices(status, confirmed_at desc)`：加速状态筛选和最近支付排序。
- `public.invoices(created_at desc)`：加速默认列表回退排序。
- 复用已有 `public.invoices(manuscript_id)` 索引支持跨入口状态一致性查询。

## Migration Impact

- 可选新增索引迁移：`20260209xxxxxx_finance_invoices_indexes.sql`。
- 不新增业务表，不要求历史数据强制回填。
