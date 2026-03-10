# UAT 最小人工手测清单

适用环境：UAT（Vercel + Hugging Face + Supabase Cloud）
面向对象：内部团队（开发 / 测试 / 编辑部）
目标：每次发版后，用 10-15 分钟验证最容易出阻断问题的关键链路。
原则：只测高价值链路；不追求全量；一旦发现阻断级问题立即停止后续步骤并记录。

## 使用方式

- 每次发版后至少执行 1 轮。
- 优先覆盖“这次改到的链路”；如果无特殊改动，按本文默认顺序执行。
- 所有步骤只要求验证“可达、可操作、结果正确”，不要求完整业务演示。

## 测前准备

- 使用 UAT 环境：
  - 前端：`https://scholar-flow-q1yw.vercel.app/`
  - 后端：`https://louisshawn-scholarflow-api.hf.space`
- 确认至少有 1 个可登录的编辑账号。
- 如需 reviewer 相关验证，准备 1 篇处于 `under_review` 或 `resubmitted` 的稿件，以及至少 1 条 reviewer assignment。
- 浏览器避免装强拦截插件；若出现异常，先关闭插件再复测一次。

## 10-15 分钟最小清单

### 1. 登录与基础壳层

步骤：
1. 用内部账号登录。
2. 打开 `/dashboard`。
3. 打开 `/settings`。

通过标准：
- 能登录成功。
- `Dashboard` 正常显示，不出现“当前账号未分配可访问的 Dashboard 角色”。
- `Settings` 页面正常加载，不是只剩 footer。

失败即阻断：
- 无法登录。
- Dashboard 误报无角色。
- Settings 白屏 / 只剩页脚 / 500。

### 2. Editor Process 列表

步骤：
1. 打开 `/editor/process`。
2. 等待列表加载完成。
3. 随便切一次筛选或搜索。

通过标准：
- 页面能进入。
- 表格或空状态能正常显示。
- 不出现“Failed to fetch manuscripts process”之类阻断提示。
- 点击任意稿件能进入详情页。

失败即阻断：
- 列表长期转圈。
- 点击稿件打不开详情。
- 页面报 403/500/白屏。

### 3. 稿件详情页 Reviewer Management

步骤：
1. 在一篇有 reviewer assignment 的稿件详情页，定位左侧 `Reviewer Management`。
2. 核对 reviewer 行是否存在。
3. 检查至少 1 位 reviewer 的状态与时间线。

通过标准：
- `Reviewer Management` 可见。
- 已选 reviewer 不会误显示为 `No reviewers selected yet.`
- 能看到 reviewer 的 `Invite Status / Review Status / Timeline / Outreach`。

失败即阻断：
- 明明有 reviewer，详情页却显示空。
- 状态明显错乱，例如已取消 reviewer 仍显示为 active。

### 4. Reviewer 邀请发送

步骤：
1. 对 1 位 `Selected` reviewer 点击 `Send Email`。
2. 观察 toast 与该 reviewer 行的 `Delivery`。

通过标准：
- 请求有结果，不是假成功。
- 成功时应看到 `Delivery: sent`。
- 失败时应直接显示真实失败原因，而不是停留在模糊的 `queued`。

失败即阻断：
- 点了没有反应。
- 行状态被推进，但 `Delivery` 无法判断。
- 明显是平台配置错误却被伪装成成功。

备注：
- `Delivery: sent` 只表示邮件供应商已接受，不代表 reviewer 一定已阅读。

### 5. Reviewer 邀请页 Accept / Continue

步骤：
1. 用 reviewer 邮件里的链接打开邀请页。
2. 点击 `Accept & Continue`。

通过标准：
- reviewer 能看到邀请页与稿件预览。
- 点击 `Accept & Continue` 后进入 reviewer workspace。
- 不会出现“接受后又跳回邀请页”。

失败即阻断：
- 邀请页打不开。
- Accept 后死循环跳回邀请页。
- reviewer 已 accept 但无法进入 workspace。

### 6. Reviewer Workspace 提交

步骤：
1. 在 reviewer workspace 填写两段评论：
   - `Comment to Authors`
   - `Private note to Editor`
2. 可选上传 1 个附件。
3. 点击 `Submit Review`。

通过标准：
- workspace 能正常加载。
- 评论框可输入，版面足够使用。
- 提交成功，不出现阻断报错。

失败即阻断：
- workspace 打不开。
- 提交失败。
- 提交后 assignment 状态没有变化。

### 7. AE 查看 Reviewer Feedback

步骤：
1. 回到同一篇稿件详情页。
2. 查看 `Reviewer Feedback Summary`。

通过标准：
- 能看到 reviewer 的公开评论与私密评论。
- 不再显示无业务意义的 `Score 5`。
- reviewer 状态已体现为已提交。

失败即阻断：
- 评论未回流到编辑端。
- 私密评论丢失或公开评论丢失。
- 仍显示历史占位评分。

### 8. Exit Review Stage -> Decision

步骤：
1. 在 `under_review` 或 `resubmitted` 的稿件详情页点击 `Exit Review Stage`。
2. 如存在 `accepted but not submitted` reviewer，按弹窗要求逐个选择处理动作。
3. 提交退出外审。

通过标准：
- 至少已有 1 份 submitted review 时，动作可用。
- `selected / invited / opened` reviewer 会被系统自动处理。
- `accepted but not submitted` reviewer 不处理干净时，不允许继续。
- 成功后稿件进入下一阶段（`decision` 或 `decision_done`）。

失败即阻断：
- 明明条件满足却不能退出外审。
- 未处理的 accepted reviewer 被系统悄悄跳过。
- 退出后状态没变，或 reviewer 仍保留旧阶段访问资格。

### 9. Decision Workspace 边界

步骤：
1. 在刚完成外审退出的稿件上打开决策工作台。
2. 检查决策选项。

通过标准：
- `under_review / resubmitted` 阶段不能直接绕过 `Exit Review Stage` 进入决策。
- `first decision` 不显示 `accept`，并允许 `add reviewer`。
- `final decision` 才允许 `accept`。

失败即阻断：
- 在错误阶段提前打开决策工作台。
- `first decision` 仍出现 `accept`。
- `first decision` 缺少 `add reviewer`。
- 终审阶段不该出现的选项仍可选。

## 建议记录格式

每次只记录最小必要信息：

- 时间：
- 环境：UAT
- 账号角色：
- 稿件 ID：
- 步骤编号：
- 结果：通过 / 失败
- 失败现象：
- 是否阻断：是 / 否

## 通过标准

满足以下条件即可认为“本轮最小人工回归通过”：

- 步骤 1-3 全通过。
- reviewer / decision 相关如果本轮有改动，则步骤 4-9 至少覆盖改动区域并通过。
- 没有出现白屏、死循环、权限绕过、状态机错跳、邮件假成功这类阻断级问题。

## 不在本清单内的内容

以下内容不属于发版后 10-15 分钟最小手测范围，另走专题回归：

- 全角色全链路验收
- 财务与发布全流程
- Analytics / Release Validation 全量验证
- 邮件可信度、DMARC、return-path 等投递质量专项
- 长时间性能压测与大数据量专项
