# Research: GAP-P1-01 Finance Real Invoices Sync

## Research Scope

围绕 GAP-P1-01，聚焦以下关键设计问题：
- Finance 数据读取放在哪个后端域，如何与现有 Mark Paid 保持一致；
- `waived` 状态在历史数据不完全规范时如何稳定识别；
- 导出采用前端本地生成还是后端快照导出；
- 并发确认支付如何避免静默覆盖；
- 审计日志是否复用现有 `status_transition_logs`。

## Decisions

### 1. Finance API 归属 `editor` 路由域，支付确认继续复用 `POST /api/v1/editor/invoices/confirm`

- **Decision**: 新增 `GET /api/v1/editor/finance/invoices` 与 `GET /api/v1/editor/finance/invoices/export`；支付确认不新开事实源，沿用 `POST /api/v1/editor/invoices/confirm`。
- **Rationale**:
  - Finance 页面是内部工作台，天然属于 `editor/admin` 权限边界。
  - 复用既有确认接口可保证与 Editor Pipeline 的状态一致性。
- **Alternatives considered**:
  - 走 `/api/v1/invoices/*` 独立域：可行，但会形成与 Editor 界面平行的业务入口，后续一致性更难维护。
  - 前端直连 Supabase：违反仓库“敏感读写走后端 API”的安全约束。

### 2. 采用“原始状态 + 有效状态”双轨模型处理 `waived`

- **Decision**: 保留 `invoices.status` 作为 `raw_status`，新增读模型字段 `effective_status`：
  - `amount <= 0` 或 `raw_status == 'waived'` -> `effective_status='waived'`
  - 其余按 `raw_status` 归类到 `paid/unpaid`
- **Rationale**:
  - 历史数据中 APC=0 可能被写成 `paid`，直接按 `status` 过滤会漏掉减免单。
  - 双轨模型兼容历史数据且不要求立即做全量数据回填。
- **Alternatives considered**:
  - 立即强制迁移全部 0 金额账单为 `waived`：改动面较大，计划阶段不做强制。
  - 只看 `status`：会导致 `waived` 筛选不准确。

### 3. 导出采用后端 CSV 快照流，不在前端本地拼接

- **Decision**: 使用后端 `text/csv` 流式导出当前筛选结果，并在响应头返回 `X-Export-Snapshot-At`。
- **Rationale**:
  - 后端单次查询具备语句级快照语义，可避免“半新半旧”数据。
  - 前端无需缓存全量记录，减少内存占用和浏览器格式兼容问题。
- **Alternatives considered**:
  - 前端本地 CSV：实现快，但快照一致性和大结果集稳定性差。
  - 后端 XLSX：对 MVP 仅对账场景收益有限，额外依赖和维护成本更高。

### 4. 并发冲突使用“期望状态 + 条件更新”乐观控制

- **Decision**: 扩展 `POST /api/v1/editor/invoices/confirm` 请求体，支持 `expected_status`（可选）；更新时加条件 `where status = expected_status`，未命中返回 `409`。
- **Rationale**:
  - 不新增版本列即可实现并发冲突检测。
  - 对旧调用方兼容：不传 `expected_status` 时保持当前行为。
- **Alternatives considered**:
  - 新增 `updated_at/version`：更标准，但需要额外迁移与回填，超出本次最小改动目标。
  - 纯“先查后改”无条件更新：并发下会发生静默覆盖。

### 5. 审计复用 `status_transition_logs.payload`，不新建财务日志表

- **Decision**: 在确认支付成功时插入 `status_transition_logs`，`payload.action='finance_invoice_confirm_paid'`，记录 `before_status/after_status/invoice_id/source`。
- **Rationale**:
  - 已有审计设施可复用，符合胶水编程原则。
  - 稿件详情审计时间线可直接扩展展示财务动作。
- **Alternatives considered**:
  - 新建 `invoice_status_logs`：可专用但增加迁移和维护成本。
  - 仅打印日志不入库：无法满足可追溯审计需求。

### 6. 访问控制采用“双层防护”：middleware 保护 + 后端 RBAC

- **Decision**: 将 `/finance` 纳入前端 middleware 受保护路径；后端 Finance API 继续要求 `editor/admin` 角色。
- **Rationale**:
  - 防止未登录直达页面；
  - 防止已登录但无内部角色用户越权获取财务数据。
- **Alternatives considered**:
  - 仅前端判断角色：可被绕过。
  - 仅后端拦截：用户体验上会先看到页面再报错，不够一致。

## Resolved Clarifications

- `waived` 采用读模型归一化，不要求本次立即全量改写历史数据。
- 导出格式在本特性固定为 CSV；XLSX 后续如有需求再单独立项。
- 并发冲突通过可选 `expected_status` 与条件更新实现，无需新增版本字段。
- Finance 与 Editor Pipeline 共享同一支付确认入口，避免双写分歧。
