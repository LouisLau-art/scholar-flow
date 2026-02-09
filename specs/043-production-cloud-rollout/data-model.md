# Data Model: Cloud Rollout Regression (GAP-P0-02)

## Entities

### 1. Release Validation Run (`public.release_validation_runs`)

表示一次完整的云端上线验收执行批次（就绪检查 + 回归 + 报告）。

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID | 主键 |
| `feature_key` | TEXT | 目标特性标识（例如 `042-production-pipeline`） |
| `environment` | TEXT | 验证环境（staging/production-like） |
| `triggered_by` | UUID/TEXT | 执行人标识 |
| `status` | TEXT | `running` / `passed` / `failed` / `blocked` |
| `blocking_count` | INT | 阻塞项数量 |
| `failed_count` | INT | 失败项数量 |
| `skipped_count` | INT | 跳过项数量 |
| `started_at` | TIMESTAMPTZ | 开始时间 |
| `finished_at` | TIMESTAMPTZ | 结束时间 |
| `summary` | TEXT | 结论摘要 |
| `rollback_required` | BOOLEAN | 是否触发回退 |
| `rollback_status` | TEXT | `not_required` / `pending` / `done` |
| `created_at` | TIMESTAMPTZ | 创建时间 |
| `updated_at` | TIMESTAMPTZ | 最后更新时间 |

### 2. Release Validation Check (`public.release_validation_checks`)

表示某次验收中的单个检查项或单个回归场景结果。

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID | 主键 |
| `run_id` | UUID | 关联 `release_validation_runs.id` |
| `phase` | TEXT | `readiness` / `regression` / `rollback` |
| `check_key` | TEXT | 检查项唯一键（如 `schema.production_cycles.exists`） |
| `title` | TEXT | 检查项标题 |
| `status` | TEXT | `passed` / `failed` / `blocked` / `skipped` |
| `is_blocking` | BOOLEAN | 是否为阻塞项 |
| `detail` | TEXT | 人类可读说明 |
| `evidence` | JSONB | 证据（输出摘要、断言结果、命令摘要） |
| `started_at` | TIMESTAMPTZ | 开始时间 |
| `finished_at` | TIMESTAMPTZ | 结束时间 |
| `created_at` | TIMESTAMPTZ | 创建时间 |

### 3. Release Validation Report (Derived View/Response)

面向放行决策的聚合结果对象，不单独建表。

| Field | Type | Description |
| :--- | :--- | :--- |
| `run` | Object | 当前批次元信息与总体结论 |
| `readiness_checks` | Array | 就绪检查结果清单 |
| `regression_checks` | Array | 回归场景结果清单 |
| `rollback_plan` | Object | 标准回退步骤与执行状态 |
| `release_decision` | TEXT | `go` / `no-go` |

## Validation Rules

- 同一时间仅允许 1 个 `status=running` 的同环境验收批次。
- 当任一 `is_blocking=true` 且 `status in (failed, blocked)` 时，`run.status` 必须为 `failed` 或 `blocked`。
- 若关键回归检查存在 `skipped`，则 `release_decision` 必须为 `no-go`。
- `finished_at` 必须晚于 `started_at`。
- `rollback_required=true` 时，`rollback_status` 不得为 `not_required`。

## State Transitions

### Validation Run State Machine

- `running -> passed`（全部阻塞项通过且 skip=0）
- `running -> failed`（存在失败阻塞项）
- `running -> blocked`（存在环境阻塞项或人工阻断）
- `failed/blocked -> running`（重新执行新批次，不复用旧 run）

### Rollback State Machine

- `not_required`（放行通过）
- `pending`（放行失败且需回退）
- `pending -> done`（回退执行完成并记录结果）

## Relationships

- `release_validation_runs (1) -> (N) release_validation_checks`
- 报告读取由 `run + checks` 聚合生成，不额外维护冗余关系表。

## Access Rules

- 仅内部受权用户可创建验收批次、执行检查、查看完整报告。
- 普通业务用户无权限触发验收流程或读取回退明细。
- 报告中不得输出敏感密钥、完整凭证、原始 token。
