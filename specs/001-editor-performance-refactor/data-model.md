# Data Model: Editor Performance Refactor

## 1. PerformanceBaselineRecord

**Purpose**: 记录某次改前/改后采样的汇总指标，作为对比基线。

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `baseline_id` | string | Yes | 基线记录唯一标识 |
| `environment` | enum(`staging`,`local-ci`) | Yes | 采样环境 |
| `scenario` | enum(`editor_detail`,`editor_process`,`editor_workspace`,`reviewer_search_repeat`) | Yes | 场景类型 |
| `sample_set_id` | string | Yes | 样本集标识（固定稿件集合版本） |
| `p50_interactive_ms` | integer | Yes | 首屏可操作 p50 |
| `p95_interactive_ms` | integer | Yes | 首屏可操作 p95 |
| `first_screen_request_count` | integer | Yes | 首屏请求数量 |
| `captured_at` | datetime | Yes | 采样时间 |
| `captured_by` | string | Yes | 执行者 |
| `notes` | string | No | 补充说明 |

### Validation Rules

- `p50_interactive_ms`、`p95_interactive_ms`、`first_screen_request_count` 必须大于 0。
- 同一 `environment + scenario + sample_set_id` 在同一天允许多条记录，但必须按 `captured_at` 可排序。

## 2. LoadStageSnapshot

**Purpose**: 描述一次页面进入过程中的阶段性状态，用于定位瓶颈在首屏还是延迟区块。

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `snapshot_id` | string | Yes | 快照唯一标识 |
| `scenario` | enum | Yes | 页面场景 |
| `manuscript_id` | string | No | 若为稿件相关页面则记录 |
| `core_ready_ms` | integer | Yes | 核心区块可操作耗时 |
| `deferred_ready_ms` | integer | No | 延迟区块完成耗时 |
| `core_requests` | integer | Yes | 核心阶段请求数 |
| `deferred_requests` | integer | No | 延迟阶段请求数 |
| `error_count` | integer | Yes | 采样期间错误数 |

### Validation Rules

- `deferred_ready_ms` 必须大于等于 `core_ready_ms`（若存在）。
- `error_count` 不能为负值。

## 3. CandidateSearchContext

**Purpose**: 用于判定审稿候选搜索结果是否可复用的上下文键。

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `manuscript_id` | string | Yes | 稿件标识 |
| `normalized_query` | string | Yes | 标准化关键词（trim/lowercase） |
| `role_scope_key` | string | Yes | 当前角色与作用域摘要 |
| `limit` | integer | Yes | 查询上限 |
| `cache_ttl_sec` | integer | Yes | 缓存有效时长 |

### Validation Rules

- `normalized_query` 允许空字符串（表示默认候选），但必须存在字段。
- `cache_ttl_sec` 默认 20，范围 5-60 秒。

## 4. CandidateSearchCacheEntry

**Purpose**: 审稿候选搜索短缓存条目。

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `context` | CandidateSearchContext | Yes | 缓存键上下文 |
| `result_count` | integer | Yes | 命中数量 |
| `stored_at` | datetime | Yes | 写入时间 |
| `expires_at` | datetime | Yes | 过期时间 |
| `source` | enum(`network`,`cache`) | Yes | 结果来源 |

### State Transitions

- `fresh` -> `expired`: 当前时间超过 `expires_at`。
- `fresh` -> `invalidated`: 稿件切换/角色变更/显式刷新。
- `expired|invalidated` -> `fresh`: 新网络请求成功并重建条目。

## 5. RegressionGateResult

**Purpose**: 汇总发布前性能与测试门禁结果。

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `gate_run_id` | string | Yes | 门禁运行 ID |
| `baseline_ref` | string | Yes | 对比基线 ID |
| `regression_ratio` | number | Yes | 最差链路劣化比例 |
| `threshold_ratio` | number | Yes | 阈值（默认 0.10） |
| `functional_tests_passed` | boolean | Yes | 功能回归是否通过 |
| `performance_checks_passed` | boolean | Yes | 性能对比是否通过 |
| `status` | enum(`passed`,`failed`) | Yes | 门禁结论 |
| `report_path` | string | Yes | 报告路径 |

### Validation Rules

- `status=passed` 必须满足：`regression_ratio <= threshold_ratio` 且 `functional_tests_passed=true` 且 `performance_checks_passed=true`。

## Relationships

- `PerformanceBaselineRecord` 与 `LoadStageSnapshot`：一对多（一个基线可包含多个阶段快照）。
- `CandidateSearchContext` 与 `CandidateSearchCacheEntry`：一对多（同上下文可有多次写入，但仅最新 `fresh` 有效）。
- `RegressionGateResult` 关联 `PerformanceBaselineRecord`（通过 `baseline_ref`）。
