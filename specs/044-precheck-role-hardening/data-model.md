# Data Model: GAP-P0-01 Pre-check Role Hardening

## Overview

本特性以“已有表增强 + 审计 payload 规范化”为主，不引入新核心业务表。  
核心目标是把 ME->AE->EIC 预审链路映射为可验证、可追责、可展示的数据结构。

## Entities

### 1. Manuscript（已有，增强使用）

**Table**: `public.manuscripts`

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | 稿件主键 |
| `status` | manuscript_status/text | Yes | 主状态机状态（`pre_check`/`under_review`/...） |
| `pre_check_status` | TEXT | No (default `intake`) | 预审子阶段：`intake`/`technical`/`academic` |
| `assistant_editor_id` | UUID | No | 当前负责技术质检的 AE |
| `owner_id` | UUID | No | 业务负责人（既有字段） |
| `editor_id` | UUID | No | 编辑负责人（既有字段） |
| `updated_at` | TIMESTAMPTZ | Yes | 最近更新时间 |

**Validation/Usage Rules**
- 当 `status='pre_check'` 时，`pre_check_status` 应为 `intake|technical|academic` 之一。
- 当 `pre_check_status='technical'` 时，`assistant_editor_id` 不能为空。
- AE 提交技术质检时，必须满足 `assistant_editor_id == current_user.id`。
- EIC 学术初审只允许在 `status='pre_check' AND pre_check_status='academic'` 下执行。

### 2. Status Transition Log（已有，扩展 payload 约定）

**Table**: `public.status_transition_logs`

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | 审计事件主键 |
| `manuscript_id` | UUID | Yes | 关联稿件 |
| `from_status` | TEXT | No | 流转前主状态 |
| `to_status` | TEXT | Yes | 流转后主状态 |
| `comment` | TEXT | No | 操作备注 |
| `changed_by` | UUID | No | 操作人 |
| `payload` | JSONB | No | 预审动作细节（本特性重点） |
| `created_at` | TIMESTAMPTZ | Yes | 事件时间 |

**Pre-check Payload Contract（新增约定）**

```json
{
  "action": "precheck_assign_ae | precheck_reassign_ae | precheck_technical_pass | precheck_technical_revision | precheck_academic_to_review | precheck_academic_to_decision",
  "pre_check_from": "intake|technical|academic|null",
  "pre_check_to": "intake|technical|academic|null",
  "assistant_editor_before": "uuid|null",
  "assistant_editor_after": "uuid|null",
  "decision": "pass|revision|review|decision_phase|null",
  "idempotency_key": "string|null"
}
```

### 3. Precheck Queue Item（读模型，API 聚合对象）

**Source**: `manuscripts` + `user_profiles` + `status_transition_logs`

| Field | Type | Description |
|---|---|---|
| `id` | UUID | 稿件 ID |
| `title` | TEXT | 题目 |
| `status` | TEXT | 主状态 |
| `pre_check_status` | TEXT | 子阶段 |
| `current_role` | TEXT | 当前责任角色（`managing_editor`/`assistant_editor`/`editor_in_chief`） |
| `current_assignee` | Object/null | 当前责任人（id/full_name/email） |
| `assigned_at` | TIMESTAMPTZ/null | 最近一次 AE 分派时间 |
| `technical_completed_at` | TIMESTAMPTZ/null | 技术质检完成时间 |
| `academic_completed_at` | TIMESTAMPTZ/null | 学术初审完成时间 |
| `updated_at` | TIMESTAMPTZ | 最近更新时间 |

## State Transitions

### Pre-check Main Path

1. **ME 分派 AE**  
   `status=pre_check, pre_check_status=intake`  
   -> `status=pre_check, pre_check_status=technical, assistant_editor_id=<ae>`

2. **AE 技术通过**  
   `status=pre_check, pre_check_status=technical`  
   -> `status=pre_check, pre_check_status=academic`

3. **EIC 学术放行外审**  
   `status=pre_check, pre_check_status=academic`  
   -> `status=under_review`

4. **EIC 学术送决策**  
   `status=pre_check, pre_check_status=academic`  
   -> `status=decision`

### Pre-check Revision Path

5. **AE 技术修回（comment 必填）**  
   `status=pre_check, pre_check_status=technical`  
   -> `status=minor_revision`

### Guardrails

- 禁止 `pre_check` / `under_review` / `resubmitted` 直接到 `rejected`。
- 拒稿仅允许在 `decision/decision_done` 路径完成。

## Idempotency and Concurrency Rules

- `assign-ae`、`submit-check`、`academic-check` 使用“条件更新 + 结果回读”实现幂等：
  - 条件满足且更新成功 -> 正常成功；
  - 条件不满足但目标状态已达成且 payload 等价 -> 返回幂等成功；
  - 条件不满足且状态已被他人推进 -> 返回 `409 Conflict`。
- 并发操作必须以数据库当前状态为准，不允许仅依赖前端缓存状态。

## Access Rules

- `managing_editor`/`admin`: 可执行 AE 分派（含重分派）。
- `assistant_editor`/`admin`: 可执行技术质检；非分配 AE 不可提交。
- `editor_in_chief`/`admin`: 可执行学术初审决策。
- `editor`/`admin`: 可查看 process 与详情中的预审可视化信息（遵循现有编辑权限模型）。

## Migration Impact

- 基线迁移：`supabase/migrations/20260206150000_add_precheck_fields.sql`（必须已应用）。
- 本特性优先不新建业务表；如发现线上数据污染风险，可在实现阶段追加轻量约束迁移（例如 `pre_check_status` CHECK）。
