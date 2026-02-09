# Quickstart: GAP-P1-01 Finance Real Invoices Sync

## 1. 前置条件

1. 当前分支：`046-finance-invoices-sync`
2. 已配置云端 Supabase（project ref: `mmvulyrfsorqdpdrzbkd`）
3. 本地依赖已安装：
   - Backend: `uv`
   - Frontend: `bun`
4. 准备至少 3 条账单数据：
   - `unpaid`（金额 > 0）
   - `paid`（金额 > 0）
   - `waived` 或金额为 0 的账单

## 2. 迁移与数据库校验

```bash
cd /root/scholar-flow
supabase projects list
supabase db push --linked --dry-run
```

若本特性引入索引迁移（可选）：

```bash
supabase db push --linked
```

最小校验 SQL：

```sql
select column_name
from information_schema.columns
where table_schema='public'
  and table_name='invoices'
  and column_name in (
    'id','manuscript_id','amount','status','confirmed_at',
    'invoice_number','pdf_path','created_at'
  );
```

## 3. 启动本地服务

```bash
# 终端 1：Backend
cd /root/scholar-flow/backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 终端 2：Frontend
cd /root/scholar-flow/frontend
bun run dev -- --port 3000
```

## 4. API 冒烟验证

```bash
BASE_URL="http://127.0.0.1:8000"
EDITOR_TOKEN="<EDITOR_OR_ADMIN_JWT>"
MANUSCRIPT_ID="<manuscript_uuid>"
```

### 4.1 获取真实账单列表（paid 筛选）

```bash
curl -X GET "$BASE_URL/api/v1/editor/finance/invoices?status=paid&page=1&page_size=20" \
  -H "Authorization: Bearer $EDITOR_TOKEN"
```

预期：
- `success=true`
- `data[*].effective_status` 全为 `paid`
- `meta.status_filter=paid`

### 4.2 导出当前筛选快照（CSV）

```bash
curl -X GET "$BASE_URL/api/v1/editor/finance/invoices/export?status=unpaid" \
  -H "Authorization: Bearer $EDITOR_TOKEN" \
  -D /tmp/finance_export_headers.txt \
  -o /tmp/finance_export.csv
```

预期：
- Header 含 `Content-Disposition`、`X-Export-Snapshot-At`
- CSV 内容与 `status=unpaid` 列表一致
- 空结果时仍返回带表头的 CSV，且 `X-Export-Empty: 1`

### 4.3 支付确认并发校验

```bash
curl -X POST "$BASE_URL/api/v1/editor/invoices/confirm" \
  -H "Authorization: Bearer $EDITOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"manuscript_id\":\"$MANUSCRIPT_ID\",\"expected_status\":\"unpaid\",\"source\":\"finance_page\"}"
```

预期：
- 首次成功返回 `current_status=paid`
- 若状态被其他入口提前修改，再次带旧 `expected_status` 应返回 `409`

## 5. 前端验收流程

1. 登录 editor/admin，访问 `/finance`。
2. 验证默认列表来自真实账单（刷新后稳定，不出现固定演示数据）。
3. 切换 `unpaid/paid/waived`，验证结果集变化正确。
4. 触发导出，检查 CSV 条目与当前筛选一致。
5. 在 `/editor` Pipeline 执行一次 `Mark Paid`，回到 `/finance` 刷新后状态应一致。

## 6. 自动化测试（实现后执行）

### Backend

```bash
cd /root/scholar-flow/backend
uv run pytest -o addopts= \
  tests/contract/test_api_paths.py \
  tests/integration/test_finance_invoices_sync.py \
  tests/integration/test_editor_apc.py \
  tests/unit/test_finance_invoice_mapping.py
```

### 2026-02-09 Backend 实测结果（本分支）

执行命令：

```bash
cd /root/scholar-flow/backend
uv run pytest -o addopts= \
  tests/contract/test_api_paths.py \
  tests/unit/test_finance_invoice_mapping.py \
  tests/integration/test_finance_invoices_sync.py
```

结果：`8 passed`。

### Frontend

```bash
cd /root/scholar-flow/frontend
bun run test:run \
  src/tests/finance-dashboard.test.tsx \
  src/tests/services/editor-api-finance.test.ts

bun run test:e2e tests/e2e/specs/finance-invoices-sync.spec.ts --project=chromium
```

### 2026-02-09 Frontend 实测结果（本分支）

执行命令：

```bash
cd /root/scholar-flow/frontend
bun run test:run src/tests/services/editor-api-finance.test.ts src/tests/finance-dashboard.test.tsx
bun run test:e2e tests/e2e/specs/finance-invoices-sync.spec.ts --project=chromium
bun run lint
```

结果：
- Vitest：`5 passed`
- Playwright：`1 passed`
- Lint：命令通过；存在仓库既有 `react-hooks/exhaustive-deps` warning（非本特性新增阻塞）

## 7. 审计验证 SQL

```sql
select manuscript_id, from_status, to_status, changed_by, payload, created_at
from public.status_transition_logs
where payload->>'action' = 'finance_invoice_confirm_paid'
order by created_at desc
limit 20;
```

预期：
- 每次确认支付都有审计记录；
- payload 含 `invoice_id`、`before_status`、`after_status`、`source`；
- `changed_by` 与实际操作者一致。
