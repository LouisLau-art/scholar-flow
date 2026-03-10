# ScholarFlow 工作流断言

更新时间：2026-03-10

目的：
- 把当前系统已经落代码的业务规则写死。
- 让测试、文档、开发实现使用同一套口径。
- 后续若业务规则变更，必须同步改代码、测试、本文档。

## 1. Reviewer Assignment 生命周期

### 1.1 状态定义

- `selected`
  - 仅表示编辑把 reviewer 加入拟邀请名单
  - 还没有真正发邮件

- `invited`
  - invitation 邮件已成功发送
  - reviewer 还没点开链接

- `opened`
  - reviewer 已成功打开邀请页
  - 但还未明确 `accept / decline`

- `accepted`
  - reviewer 已接受邀请
  - 可以进入 reviewer workspace

- `submitted`
  - reviewer 已提交审稿意见
  - 底层常对应 `completed`

- `declined`
  - reviewer 明确拒绝邀请

- `cancelled`
  - 编辑部主动终止该 reviewer assignment
  - 被取消后 reviewer 不能继续访问稿件

### 1.2 允许的主路径

- `selected -> invited -> opened -> accepted -> submitted`
- `selected -> invited -> declined`
- `selected -> invited -> opened -> declined`
- `selected -> invited/opened -> cancelled`
- `selected -> invited/opened/accepted -> cancelled`

### 1.3 明确禁止

- `selected` 不等于已邀请
- `invited/opened` 不等于已接受
- reviewer 不能在未接受邀请时进入 workspace
- `cancelled` reviewer 不能再访问 invitation / workspace / submit / attachment upload

## 2. Reviewer Invitation 与邮件规则

### 2.1 邮件成功才推进状态

- 只有邮件真正发送成功，assignment 才能从 `selected` 进入 `invited`
- 如果发送失败：
  - assignment 不应误推进到 `invited`
  - manuscript 不应误推进到 `under_review`

### 2.2 Delivery 状态含义

- `queued`
  - 应用侧已接单，准备发信
- `sent`
  - provider 已接受该邮件
- `failed`
  - provider 或配置导致发送失败
- `pending_retry`
  - 已记录待重试

### 2.3 幂等口径

- 首次 invitation 使用稳定 idempotency key，防双击重复发送
- 对已 `invited/opened/pending` assignment 的合法重发，必须使用新 resend key
- 否则会触发 provider `idempotency key body mismatch`

## 3. Reviewer Cancel / Unassign

### 3.1 `unassign`

- 只允许用于 `selected`
- 本质上是把“还没真正联系 reviewer”的 shortlist 移除

### 3.2 `cancel`

- 用于 `invited / opened / accepted`
- 必须保留 assignment 历史
- 必须保留审计字段
- 可附带 cancellation email

### 3.3 阶段退出时的处理

当 AE 准备离开 `under_review`：

- `selected / invited / opened`
  - 系统自动 `cancel`
- `accepted but not submitted`
  - 不能自动跳过
  - AE 必须逐个明确处理：
    - `cancel`
    - 或 `wait`
- 只要还有 `wait` 或未处理 reviewer，就不能退出外审阶段

## 4. Review Stage Exit 规则

### 4.1 外审退出前提

- 只允许从：
  - `under_review`
  - `resubmitted`
  离开外审阶段

- 至少已有 `1` 份有效 review 提交

### 4.2 退出结果

- `target_stage=first`
  - manuscript 进入 `decision`
- `target_stage=final`
  - manuscript 进入 `decision_done`

### 4.3 UI 规则

- 外审阶段详情页显示 `Exit Review Stage`
- 成功退出后，`Open Decision Workspace` 才应开放

## 5. Decision 边界

### 5.1 first decision

- first decision 不允许 `accept`
- 仅允许：
  - `minor_revision`
  - `major_revision`
  - `reject`

### 5.2 final decision

- `accept` 只允许出现在 final decision 阶段
- 当前系统口径：
  - `decision_done` 可以执行 `accept`

注意：
- 如果后续业务确认“必须作者修回后才能 accept”，则需要同时修改：
  - 后端 decision service
  - 前端 decision editor
  - 测试断言
  - 本文档

### 5.3 决策工作台可见性

- `Decision Workspace` 当前只允许在：
  - `decision`
  - `decision_done`
  打开
- `under_review / resubmitted` 不允许直接进入 decision workspace

## 6. Reviewer Workspace 规则

### 6.1 当前 reviewer 能力

- reviewer 可通过 magic link 免登录完成：
  - 查看 invitation
  - accept / decline
  - 进入 workspace
  - 提交 review

### 6.2 保存草稿

- 当前已移除显式 `Save Draft` 按钮
- 原因：
  - 之前只是浏览器 `localStorage` 本地缓存
  - 容易误导成“服务端草稿”

### 6.3 当前 review 提交口径

- 已去掉默认 `score 5`
- reviewer 当前提交的是：
  - `comments_for_author`
  - `confidential_comments_to_editor`
  - `attachment`

## 7. 对自动化测试的要求

以下规则必须由自动化守住：

- deploy 后 HF runtime 收敛成功
- Supabase migration parity 为 up-to-date
- 平台 readiness 不允许：
  - `FRONTEND_BASE_URL=localhost`
  - `FRONTEND_ORIGIN=localhost`
  - 在使用 Resend 时继续落到 `resend.dev` 开发发件人
  - 未配置任何邮件 provider（Resend / SMTP）
  - 缺失 `ADMIN_API_KEY`
  - 缺失显式 `MAGIC_LINK_JWT_SECRET`（`SECRET_KEY` 兜底不算通过）
- UAT canonical smoke 必须额外校验：
  - HF 运行中的 `DEPLOY_SHA` 与本次触发 SHA 一致
  - 前端 smoke 只验证稳定 UAT URL 的壳层与关键入口，不宣称 Vercel commit 级绑定
- deployed smoke 必须覆盖：
  - 登录
  - dashboard
  - settings
  - `/editor/process`
  - `/admin/users`

以下规则必须继续由人工 UAT 补：

- reviewer 真邮件收发
- accept/decline 后的真实角色体验
- AE `Exit Review Stage` 的完整业务判断
- decision 文案与编辑部使用体验

## 8. 改规则时的同步约束

任何工作流规则变更，都不能只改一处。

必须同步检查：
- 后端状态机
- 前端入口与禁用态
- 单测 / 集成测试 / E2E
- `docs/WORKFLOW_ASSERTIONS.md`
- `docs/UAT_MINIMAL_CHECKLIST.md`
