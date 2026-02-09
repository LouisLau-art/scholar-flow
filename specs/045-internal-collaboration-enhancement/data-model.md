# Data Model: GAP-P0-03 Internal Collaboration Enhancement

## Overview

本特性在 Feature 036 的 `internal_comments` 基础上补齐“提及关系 + 内部任务 + 逾期聚合”三类数据模型。
核心思路是：
- 评论与提及分离建模，避免正文解析歧义；
- 任务当前态与任务轨迹分离建模，兼顾查询与审计；
- 逾期快照按读时聚合生成，不冗余持久化。

## Entities

### 1. InternalComment（已有）

**Table**: `public.internal_comments`

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | 评论主键 |
| `manuscript_id` | UUID | Yes | 关联稿件 |
| `user_id` | UUID | Yes | 评论作者 |
| `content` | TEXT | Yes | 评论正文 |
| `created_at` | TIMESTAMPTZ | Yes | 创建时间 |

### 2. InternalCommentMention（新增）

**Table**: `public.internal_comment_mentions`

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | 提及记录主键 |
| `comment_id` | UUID | Yes | 关联 `internal_comments.id` |
| `manuscript_id` | UUID | Yes | 冗余稿件 ID，便于检索 |
| `mentioned_user_id` | UUID | Yes | 被提及用户 |
| `mentioned_by_user_id` | UUID | Yes | 发起提及用户 |
| `created_at` | TIMESTAMPTZ | Yes | 提及时间 |

**Validation Rules**
- `mentioned_user_id` 必须是内部成员。
- 同一评论对同一 `mentioned_user_id` 唯一（建议唯一索引 `comment_id + mentioned_user_id`）。

### 3. InternalTask（新增）

**Table**: `public.internal_tasks`

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | 任务主键 |
| `manuscript_id` | UUID | Yes | 关联稿件 |
| `title` | TEXT | Yes | 任务标题 |
| `description` | TEXT | No | 任务说明 |
| `assignee_user_id` | UUID | Yes | 负责人 |
| `status` | TEXT | Yes | `todo` / `in_progress` / `done` |
| `priority` | TEXT | No | `low` / `medium` / `high` |
| `due_at` | TIMESTAMPTZ | Yes | 截止时间（UTC） |
| `created_by` | UUID | Yes | 创建者 |
| `created_at` | TIMESTAMPTZ | Yes | 创建时间 |
| `updated_at` | TIMESTAMPTZ | Yes | 最近更新时间 |
| `completed_at` | TIMESTAMPTZ | No | 完成时间 |

**Validation Rules**
- `title` 非空且长度受限（建议 <= 200）。
- `status='done'` 时可写入 `completed_at`；非 `done` 可为空。
- `due_at` 必填，可早于当前时间（将被判定逾期）。

### 4. InternalTaskActivityLog（新增）

**Table**: `public.internal_task_activity_logs`

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | Yes | 日志主键 |
| `task_id` | UUID | Yes | 关联任务 |
| `manuscript_id` | UUID | Yes | 冗余稿件 ID |
| `action` | TEXT | Yes | 如 `task_created` / `status_changed` / `assignee_changed` / `due_at_changed` |
| `actor_user_id` | UUID | Yes | 操作人 |
| `before_payload` | JSONB | No | 变更前快照 |
| `after_payload` | JSONB | No | 变更后快照 |
| `created_at` | TIMESTAMPTZ | Yes | 操作时间 |

### 5. ManuscriptSLASnapshot（读模型，不单独建表）

**Source**: `internal_tasks` 读时聚合

| Field | Type | Description |
|---|---|---|
| `is_overdue` | BOOLEAN | 稿件是否存在逾期未完成任务 |
| `overdue_tasks_count` | INTEGER | 逾期任务数量 |
| `nearest_due_at` | TIMESTAMPTZ/null | 最近一个未完成任务截止时间（用于排序/提示） |

## State Transitions

### Internal Task Status Flow

1. `todo -> in_progress`  
2. `in_progress -> done`  
3. `done -> in_progress`（任务重开）  
4. `todo -> done`（直接完成，允许）

### Overdue Determination

- 条件：`status != 'done' AND due_at < now()`  
- 当任务状态或 `due_at` 变化后，稿件级 `is_overdue` 与 `overdue_tasks_count` 需在下一次查询中反映最新结果。

## Access Rules

- `editor/admin`: 可创建任务、改负责人、改截止时间、改状态。
- `assignee_user_id`: 可改状态与执行相关字段。
- 其他内部成员：只读任务列表，不可修改受限字段。
- 提及只允许内部成员之间发生；外部用户不可被提及。

## Indexing Suggestions

- `internal_comment_mentions(comment_id, mentioned_user_id)` 唯一索引。
- `internal_tasks(manuscript_id, status, due_at)` 组合索引（支持详情查询和逾期聚合）。
- `internal_tasks(assignee_user_id, status)` 索引（支持个人任务视角）。
- `internal_task_activity_logs(task_id, created_at desc)` 索引（支持任务时间线）。

## Migration Impact

- 需要新增：
  - `public.internal_comment_mentions`
  - `public.internal_tasks`
  - `public.internal_task_activity_logs`
- 可选补强：
  - 为 `notifications` 增加协作通知类型枚举约束（若当前已使用文本类型可暂不强制）。
