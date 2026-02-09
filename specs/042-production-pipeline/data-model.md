# Data Model: Production Pipeline Workspace (Feature 042)

## Entities

### 1. Production Cycle (`public.production_cycles`)

表示稿件录用后的单次生产轮次。

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID | 主键 |
| `manuscript_id` | UUID | 关联稿件 |
| `cycle_no` | INT | 轮次编号（同稿件内递增） |
| `status` | TEXT | `draft` / `awaiting_author` / `author_confirmed` / `author_corrections_submitted` / `in_layout_revision` / `approved_for_publish` / `cancelled` |
| `layout_editor_id` | UUID | 负责排版的内部用户 |
| `proofreader_author_id` | UUID | 本轮校对责任作者 |
| `galley_bucket` | TEXT | 清样所在 bucket（默认 `production-proofs`） |
| `galley_path` | TEXT | 清样对象路径 |
| `version_note` | TEXT | 排版版本说明 |
| `proof_due_at` | TIMESTAMPTZ | 校对截止时间 |
| `approved_by` | UUID | 核准发布的编辑 |
| `approved_at` | TIMESTAMPTZ | 核准时间 |
| `created_at` | TIMESTAMPTZ | 创建时间 |
| `updated_at` | TIMESTAMPTZ | 最后更新时间（用于并发控制） |

### 2. Proofreading Response (`public.production_proofreading_responses`)

表示作者对某轮清样提交的校对反馈。

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID | 主键 |
| `cycle_id` | UUID | 关联 `production_cycles.id` |
| `manuscript_id` | UUID | 冗余稿件 ID，便于审计查询 |
| `author_id` | UUID | 实际提交反馈的作者 |
| `decision` | TEXT | `confirm_clean` / `submit_corrections` |
| `summary` | TEXT | 反馈摘要（可选） |
| `submitted_at` | TIMESTAMPTZ | 提交时间 |
| `is_late` | BOOLEAN | 是否逾期提交 |
| `created_at` | TIMESTAMPTZ | 创建时间 |

### 3. Proofreading Correction Item (`public.production_correction_items`)

当 `decision=submit_corrections` 时的逐条修正条目。

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID | 主键 |
| `response_id` | UUID | 关联 `production_proofreading_responses.id` |
| `line_ref` | TEXT | 页码/段落/行号参考 |
| `original_text` | TEXT | 原文片段 |
| `suggested_text` | TEXT | 建议修正文本 |
| `reason` | TEXT | 修正理由 |
| `sort_order` | INT | 展示顺序 |
| `created_at` | TIMESTAMPTZ | 创建时间 |

### 4. Production Audit Payload (reuse `public.status_transition_logs.payload`)

复用现有审计表，不新增独立日志表；`payload` 扩展记录生产事件。

| Field | Type | Description |
| :--- | :--- | :--- |
| `event_type` | TEXT | `production_cycle_created` / `galley_uploaded` / `proofreading_submitted` / `production_approved` |
| `cycle_id` | UUID | 对应轮次 |
| `actor_id` | UUID | 操作人 |
| `metadata` | JSONB | 关键上下文（deadline、decision、file path 等） |

## Validation Rules

- 同一稿件同一时刻最多允许 1 个活跃轮次（`draft/awaiting_author/in_layout_revision/author_corrections_submitted`）。
- `cycle_no` 在同一 `manuscript_id` 下必须唯一且递增。
- 创建轮次时稿件状态必须属于 post-acceptance 区间（`approved/layout/english_editing/proofreading`）。
- `galley_path` 必须是 PDF 文件路径，且上传成功后才能进入 `awaiting_author`。
- `proof_due_at` 必须晚于轮次创建时间。
- `decision=confirm_clean` 时不允许提交 correction items。
- `decision=submit_corrections` 时必须至少包含 1 条 correction item。
- 仅 `proofreader_author_id` 可提交该轮次作者反馈。
- 仅编辑权限用户可执行 `approved_for_publish`，且前置条件为 `author_confirmed`。

## State Transitions

### Production Cycle State Machine

- `draft -> awaiting_author`（排版编辑提交清样）
- `awaiting_author -> author_confirmed`（作者确认无误）
- `awaiting_author -> author_corrections_submitted`（作者提交修正清单）
- `author_corrections_submitted -> in_layout_revision`（排版接收修正并处理中）
- `in_layout_revision -> awaiting_author`（新清样回传作者）
- `author_confirmed -> approved_for_publish`（编辑核准发布依据）
- `draft/awaiting_author/in_layout_revision -> cancelled`（流程终止）

## Relationships

- `manuscripts (1) -> (N) production_cycles`
- `production_cycles (1) -> (N) production_proofreading_responses`
- `production_proofreading_responses (1) -> (N) production_correction_items`
- `manuscripts (1) -> (N) status_transition_logs`（通过 `payload.event_type` 识别生产事件）

## Access Rules

- 写操作（创建轮次、上传清样、核准发布）：`editor/admin` + 稿件归属校验。
- 作者反馈提交：仅轮次指定责任作者。
- 文件读取：统一后端签名 URL；草稿/处理中版本不对无关角色暴露。

## Compatibility Notes

- 与现有 `ProductionService` 的状态推进并存：轮次核准产出“可发布依据”，最终发布仍走既有门禁逻辑。
- 若部署环境启用了 `PRODUCTION_GATE_ENABLED=1`，需确保核准轮次同步更新 `final_pdf_path`。
