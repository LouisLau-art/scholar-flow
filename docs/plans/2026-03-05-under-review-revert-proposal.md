# 稿件状态回退方案（已实施）

日期：2026-03-05  
范围：仅讨论 **`under_review -> pre_check(technical)`** 的“误触回退”能力

## 1. 背景

当前 AE 在 `pre_check(technical)` 点了 `Submit Technical Check(pass)` 后，稿件会进入 `under_review`。  
现实场景中可能出现误触，需要撤回到“刚分配给 AE、尚未送外审”的状态。

## 2. 目标与非目标

目标：
- 支持受控回退：`under_review -> pre_check + pre_check_status=technical`
- 审计可追溯（谁在何时为何回退）
- 不破坏已开始的外审流程

非目标：
- 不开放“任意状态任意回退”
- 不修改全局状态机 `allowed_next()` 规则

## 3. 推荐方案（专用动作，不改通用状态机）

新增专用接口（命令型）：
- `POST /api/v1/editor/manuscripts/{id}/revert-technical-check`

请求体建议：
```json
{
  "reason": "误触提交，需回到技术检查阶段",
  "idempotency_key": "optional-string"
}
```

返回：
- `message`
- `data`（最新 manuscript 快照）

## 4. 安全约束（必须全部满足）

1. 当前状态必须是 `under_review`。  
2. 最近一次进入 `under_review` 的来源必须是 `precheck_technical_to_under_review`（来自 AE 技术通过动作）。  
3. 外审尚未实质开始：  
   - `review_assignments` 不存在有效进行中的记录（建议仅允许空集，或只允许 `cancelled/declined`）。  
   - 若已存在 `accepted/submitted/completed/pending`，禁止回退。  
4. `reason` 必填（最小长度建议 10）。  
5. 权限：`assistant_editor`（仅限该稿件 `assistant_editor_id`）、`managing_editor`、`admin`。

## 5. 状态与字段更新

执行成功时更新：
- `status = pre_check`
- `pre_check_status = technical`
- `updated_at = now`
- `assistant_editor_id` 保持不变（仍归当前 AE）

## 6. 审计与可观测性

写入 `status_transition_logs`：
- `from_status = under_review`
- `to_status = pre_check`
- `comment = reason`
- `payload.action = precheck_technical_revert_from_under_review`
- `payload.reason = ...`
- `payload.source = ae_workspace`（或具体页面来源）

## 7. 前端交互建议

入口：
- AE Workspace 中 `under_review` 行增加按钮：`Undo Submit Check`（中文可用“撤回外审发起”）

交互：
- 二次确认弹窗 + 必填 reason
- 提交后刷新 workspace + 成功 toast
- 后端返回 409 时显示明确提示（例如“已有审稿指派/已有人接受，不可回退”）

## 8. 错误码建议

- `422`：参数非法（reason 缺失/过短）  
- `403`：无权限  
- `404`：稿件不存在  
- `409`：状态冲突或不满足回退前置条件（最常见）

## 9. 测试建议（实现时）

后端单测：
- 成功回退（满足全部条件）
- 非 under_review 拒绝
- 已有 review_assignments 拒绝
- 最近来源不是 `precheck_technical_to_under_review` 拒绝
- 非 owner AE 拒绝

前端测试：
- 按钮显示条件
- 弹窗必填校验
- 409 错误展示

---

## 10. 实施结果（2026-03-05）

已落地：
- 后端新增接口：`POST /api/v1/editor/manuscripts/{id}/revert-technical-check`
- 受控校验：状态、来源 action、review_assignments、权限（AE/ME/Admin）
- 审计日志：`payload.action = precheck_technical_revert_from_under_review`
- 前端 AE Workspace：`under_review` 行新增 `Undo Submit Check` + 原因必填弹窗
- 测试：后端单测/集成测 + 前端弹窗与状态判定测试
