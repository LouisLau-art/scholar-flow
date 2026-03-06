# Reviewer Invitation State Machine Notes

## 目标

把 reviewer 流程拆成三个明确阶段，避免“选中 reviewer = 已发邀请 = 已进入外审”的错误耦合。

## Canonical State Model

### Invite Status

- `selected`
  - 编辑已将 reviewer 放入拟邀请名单
  - 还没有发出邮件
  - `invited_at = null`
- `invited`
  - 已发送邀请邮件
  - magic link 已生成并出站
- `opened`
  - reviewer 已打开邀请页
  - 仅表示看过邀请，不等于同意
- `accepted`
  - reviewer 明确点击接受邀请
- `declined`
  - reviewer 明确拒绝邀请

### Review Status

- `not_started`
  - 尚未开始审稿
- `in_progress`
  - 已接受，尚未提交审稿意见
- `submitted`
  - 已提交审稿意见

## 当前 MVP 兼容策略

数据库当前仍主要复用 `review_assignments.status` 单列，因此本轮先采用兼容映射：

- `selected` -> `invite_status=selected`, `review_status=not_started`
- `invited` -> `invite_status=invited`, `review_status=not_started`
- `opened` -> `invite_status=opened`, `review_status=not_started`
- `accepted` -> `invite_status=accepted`, `review_status=in_progress`
- `pending` + `accepted_at` -> 视作 `accepted`
- `pending` + `opened_at` -> 视作 `opened`
- `pending` + `invited_at` -> 视作 `invited`
- `pending` + 无邀请证据 -> 视作 `selected`
- `completed` / `submitted` -> `review_status=submitted`
- `declined` -> `invite_status=declined`

## 第一批行为约束

1. `POST /api/v1/reviews/assign`
   - 只创建 `selected`
   - 不发送邮件
   - 不写 `invited_at`
   - 不推进 manuscript 到 `under_review`

2. `POST /api/v1/reviews/assignments/{assignment_id}/send-email`
   - invitation 模板才会把 assignment 推到 `invited`
   - invitation 模板才会写 `invited_at`
   - invitation 模板才会把 manuscript 推到 `under_review`

3. reviewer workspace / session
   - 这批不再继续放大范围修改
   - 下一批单独移除 implicit accept

## 暂存技术债

- cooldown override 目前仍在“选择 reviewer”阶段触发，语义上偏早；后续应下沉到真正发送 invitation 的动作。
- decline 后 re-invite 仍需新建 invitation attempt，而不是重用旧 declined assignment；此项留到下一批。
- email delivery evidence 目前以“已入队”近似，尚未形成完整 queued/sent/failed 审计链。
