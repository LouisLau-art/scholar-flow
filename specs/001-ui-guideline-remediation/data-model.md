# Phase 1 Data Model - UI Guideline Remediation

## 1. UIFinding
- **Purpose**: 表示 `problem.md` 中可追踪的问题条目。
- **Fields**:
  - `id` (string): 唯一标识（建议 `WG-001` 等）
  - `source` (enum): `tailwind|shadcn|web-guidelines`
  - `severity` (enum): `high|medium|low`
  - `file_path` (string)
  - `line` (number)
  - `description` (string)
  - `acceptance_rule` (string)
  - `status` (enum): `identified|planned|in_progress|resolved|verified`
  - `owner` (string, optional)
- **Validation Rules**:
  - `severity` 必填且只能为预定义枚举。
  - `file_path + line + description` 组合应能唯一定位一个问题点。

## 2. AccessibilityContract
- **Purpose**: 约束关键表单与弹窗的可访问行为。
- **Fields**:
  - `surface_id` (string): 交互面唯一标识（如 `login-form`、`site-search-dialog`）
  - `control_id` (string)
  - `has_accessible_name` (boolean)
  - `label_mode` (enum): `visible|sr_only|aria_label`
  - `focus_visible` (boolean)
  - `keyboard_reachable` (boolean)
  - `dialog_close_path` (enum): `default_close|dialog_close_as_child|custom_accessible_close`
- **Validation Rules**:
  - `has_accessible_name=true` 是关键路径控件的硬约束。
  - 弹窗类交互必须具备 `dialog_close_path`。

## 3. InteractionItem
- **Purpose**: 标识页面上的可点击交互项，并确保语义正确。
- **Fields**:
  - `surface_id` (string)
  - `element_kind` (enum): `link|button|input|select|other`
  - `semantic_valid` (boolean)
  - `target_type` (enum): `route|action|none`
  - `target_value` (string, optional)
  - `is_placeholder_target` (boolean)
- **Validation Rules**:
  - 当交互可点击时，`semantic_valid` 必须为 `true`。
  - `is_placeholder_target=true` 视为待修复状态。

## 4. CopyStyleRule
- **Purpose**: 统一加载文案与标点风格。
- **Fields**:
  - `rule_id` (string)
  - `domain` (enum): `loading|processing|error|empty`
  - `ellipsis_style` (enum): `unicode_ellipsis|three_dots`
  - `locale` (string): `zh-CN|en-US|...`
- **Validation Rules**:
  - 本特性目标为 `ellipsis_style=unicode_ellipsis`。

## 5. DateDisplayRule
- **Purpose**: 统一终端展示时间格式。
- **Fields**:
  - `rule_id` (string)
  - `use_locale_aware_format` (boolean)
  - `display_granularity` (enum): `date|datetime`
  - `fallback_text` (string): 通常为 `—`
- **Validation Rules**:
  - 用户可见时间字段默认 `use_locale_aware_format=true`。

## Relationships

- `UIFinding` 1..n -> 1 `AccessibilityContract`（当问题属于表单/弹窗可访问性）
- `UIFinding` 1..n -> 1 `InteractionItem`（当问题属于交互语义）
- `UIFinding` 1..n -> 1 `CopyStyleRule`（当问题属于文案一致性）
- `UIFinding` 1..n -> 1 `DateDisplayRule`（当问题属于时间展示一致性）

## State Transitions

`UIFinding.status`:

`identified -> planned -> in_progress -> resolved -> verified`

允许回退：

`resolved -> in_progress`（回归失败）  
`verified -> in_progress`（线上问题复现）
