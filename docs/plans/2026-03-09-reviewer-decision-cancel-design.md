# Reviewer Decision / Cancel 设计说明

日期：2026-03-09  
范围：reviewer 审稿页面可用性、AE 提前进入决策、reviewer cancel 生命周期  
相关技能：`brainstorming`、`api-design-principles`、`postgresql-table-design`、`context7`

## 背景

当前 reviewer 主链路已经基本打通：

- reviewer 可通过邮件 magic link 进入 invite 页
- reviewer 明确 `Accept / Decline` 后进入后续流程
- reviewer 可提交公开评论、私密评论和附件
- AE 稿件详情页可看到 reviewer 管理区和 reviewer feedback

但仍有三个明显缺口：

1. reviewer 审稿表单可用性不足  
   现有两个评论框高度偏小，不适合长篇详细审稿意见。

2. `under_review` 阶段的决策权模型不符合真实业务  
   当前实现更接近“等所有 assignment 完成后再自动推进到 `decision`”，而业务上 AE 应该可以在收到部分高质量审稿意见后提前推进。

3. reviewer 生命周期缺少正式的 `cancel` 语义  
   当前系统已有 `cancelled` 状态，但编辑侧早期操作更接近 `unassign/delete`，无法满足“保留历史、发取消邮件、彻底回收访问权限”的要求。

## 现状审计

### reviewer 表单

- reviewer workspace 评论表单位于：
  - `frontend/src/app/(reviewer)/reviewer/workspace/[id]/action-panel.tsx`
- 当前高度：
  - `comments_for_author`: `rows={10}`
  - `confidential_comments_to_editor`: `rows={6}`

### score

- reviewer 提交时，后端会写死：
  - `backend/app/services/reviewer_workspace_service.py`
  - `report_payload["score"] = 5`
- AE 稿件详情页当前会展示：
  - `frontend/src/app/(admin)/editor/manuscript/[id]/detail-sections.tsx`
  - `Score 5`

该字段不是业务真实评分，应视为历史占位值。

### 当前 reviewer 状态

当前 reviewer 侧真实可见的生命周期状态可整理为：

- `selected`
  - AE 内部 shortlist，尚未真正发邮件
- `invited`
  - 邀请邮件已发出
- `opened`
  - reviewer 已点开邀请链接，已查看邀请页，但未表态
- `accepted`
  - reviewer 已接受邀请，进入可审稿状态
- `submitted`
  - reviewer 已提交审稿报告（底层常见为 `completed`）
- `declined`
  - reviewer 拒绝邀请
- `cancelled`
  - 编辑部终止该 assignment，后续不得再访问该稿件

其中 `opened` 的感知不是靠前端猜测，而是服务端在 reviewer 首次成功打开 invite 页时写入 `opened_at`。

### 决策阶段现状

- 当前 `DecisionEditor` 同时承载 first/final decision UI：
  - `frontend/src/components/editor/decision/DecisionEditor.tsx`
- 但现有决策选择仍包含：
  - `accept`
  - `minor_revision`
  - `major_revision`
  - `reject`

这与目标业务不一致：

- `first decision` 只允许：
  - `major_revision`
  - `minor_revision`
  - `reject`
- `accept` 只能出现在 `final decision`

### 自动推进 decision 的现状

- reviewer 提交后：
  - `backend/app/services/reviewer_workspace_service.py`
- 仅当该稿件所有 `review_assignments` 都变成 `completed` 时，才尝试把稿件推进到 `decision`

这不符合业务要求：

- AE 可能只收到 2 份高质量意见就已经足够，不应被第 3 位 reviewer 拖住

### cancel 现状

当前系统中已有若干“取消未完成 reviewer”的片段逻辑：

- `backend/app/api/v1/editor_decision.py`
- `backend/app/api/v1/editor_heavy_decision.py`
- `backend/app/services/revision_service.py`

但它们的特点是：

- 更像阶段收尾时把部分 `pending` assignment 直接标 `cancelled`
- 没有显式区分：
  - 未响应 reviewer
  - 已接受但未提交 reviewer
- 没有完整的 AE 人机协商流程
- 没有成体系的取消邮件模板和取消原因审计

## 目标

### 目标 1：reviewer 审稿页面更适合长评审

- 放大两个评论框
- 保留原有表单结构和提交流程
- 不引入复杂 autosize 依赖
- 允许 reviewer 自行纵向拉伸输入框

### 目标 2：AE 可在部分审稿完成后推进流程

在 `under_review` 阶段，AE 满足“已有至少一份有效 review”后，可以主动进入下一步，而不是被动等所有 reviewer 完成。

AE 下一步有三种业务出口：

1. 直接给 revision 建议
   - `major_revision`
   - `minor_revision`
2. 送 `first decision`
   - 交给学术委员会 / 主编判断
3. 在审稿意见极为明确且积极时，直接送 `final decision`

### 目标 3：离开 `under_review` 时终止上一个 reviewer 阶段

当 manuscript 从 `under_review` 进入下一阶段时，所有仍处于外审中的 reviewer assignment 必须被处理干净，不能让旧阶段继续悬挂。

## 非目标

本轮不做：

- reviewer 逐段 PDF 批注
- reviewer 结构化评分系统
- reviewer 服务端草稿系统
- 全面重构 reviewer assignment 为事件溯源模型

## 推荐方案

## 方案 A：一次性同时改 UI + 状态机 + cancel + 邮件

### 优点

- 一次收敛所有 reviewer / decision 规则

### 缺点

- 风险最大
- reviewer、decision、邮件、权限四条链同时改
- 回归成本高

## 方案 B：分两期实施（推荐）

### 第一期：低风险快改

- 放大 reviewer 评论框
- 去掉 `score`
- 不改 reviewer 状态机

### 第二期：流程改造

- AE 可在部分 review 完成后进入下一步
- first / final decision 选项收敛
- 自动 cancel 未响应 reviewer
- AE 显式处理已接受但未提交 reviewer
- cancel 后 reviewer 立即失效
- 发取消邮件并写审计

### 优点

- 先交付可见体验改进
- 状态机改造单独回归，风险更可控

### 缺点

- 需要两轮发布

## 方案 C：只改状态机，不先碰 reviewer 页面

### 优点

- 先解决业务规则问题

### 缺点

- reviewer 页面体验仍差
- 对业务方的感知改进不明显

## 推荐结论

采用 **方案 B**。

理由：

- 第一阶段是确定性、低风险改动，应先快速落地。
- 第二阶段是业务规则改造，必须独立设计、独立测试、独立上线。

## 目标状态机设计

### reviewer 主状态

- `selected`
- `invited`
- `opened`
- `accepted`
- `submitted`
- `declined`
- `cancelled`

### 业务含义

- `selected`
  - 内部 shortlist
- `invited`
  - 邮件已发
- `opened`
  - reviewer 已访问邀请页，未明确表态
- `accepted`
  - reviewer 已接受邀请，可进入 workspace
- `submitted`
  - reviewer 已提交报告
- `declined`
  - reviewer 明确拒绝
- `cancelled`
  - assignment 被编辑部终止，链接与访问权限立即失效

## `under_review` 离场规则

当 AE 准备将 manuscript 从 `under_review` 推到下一阶段时，reviewer assignment 按三类处理：

### 1. `selected / invited / opened`

系统自动 `cancel`。

原因：

- 这些 reviewer 尚未正式接下任务
- 离开 `under_review` 后不应再继续占用该稿件

动作：

- 写 `status = cancelled`
- 写取消审计信息
- 发送取消邮件
- 立即失效 reviewer magic link / workspace 访问

### 2. `accepted` 但未 `submitted`

不自动取消，必须由 AE 明确处理。

每位 reviewer 只能做两种选择：

- `continue_waiting`
- `cancel_after_contact`

只有当所有 `accepted` 且未提交 reviewer 都被明确处理后，才允许 manuscript 离开 `under_review`。

这与业务口径一致：

- 已接受 reviewer 需要先沟通，再决定是否取消

### 3. `submitted`

保留，继续参与后续 decision 汇总。

## `first decision` / `final decision` 规则

### first decision

允许：

- `major_revision`
- `minor_revision`
- `reject`

不允许：

- `accept`

定位：

- AE 不好把握时，把稿件交给学术委员会 / 主编判断

### final decision

允许：

- `accept`
- `major_revision`
- `minor_revision`
- `reject`

定位：

- 最终决策口

### 直接跳 final decision

当已有 reviewer 报告足够清晰、结论高度一致，AE 可以跳过 first decision，直接送 final decision。

## `cancel` 与 `unassign` 的区别

### `unassign`

仅用于非常早期的内部 shortlist 修正。

特点：

- 偏内部管理动作
- 更接近“撤销 selection”

### `cancel`

用于 invitation 发出后或 reviewer 已接受后的正式终止。

特点：

- 保留审计
- 保留历史
- 发取消邮件
- 立即回收访问权限

推荐做法：

- 保留 `unassign`
- 新增独立 `cancel` 动作，不混用

## 数据模型建议

当前数据库已有 `cancelled` 状态，但缺少完整 cancel 审计字段。第二期建议为 `review_assignments` 增加：

- `cancelled_at timestamptz null`
- `cancelled_by uuid null`
- `cancel_reason text null`
- `cancel_via text null`

其中：

- `cancel_via` 推荐受限值：
  - `auto_stage_exit`
  - `editor_manual_cancel`
  - `post_acceptance_cleanup`
  - `legacy`

同时建议保留并复用现有 invite 审计字段：

- `selected_by`
- `selected_via`
- `invited_by`
- `invited_via`

## API 设计建议

### 第一期

- 不新增接口
- 仅改 reviewer 提交写入和 reviewer summary 展示

### 第二期

新增两类接口：

1. `POST /api/v1/reviews/assignments/{assignment_id}/cancel`
   - 显式取消单个 reviewer assignment
   - 仅用于 invitation 已发或 reviewer 已接受后的终止

2. `POST /api/v1/editor/manuscripts/{id}/review-stage-exit`
   - AE 准备离开 `under_review` 时统一提交 reviewer 处置结果
   - body 应包含：
     - `target_stage`
     - `decision_path`
     - `pending_cancellations`
     - `accepted_reviewer_resolutions`

FastAPI 返回建议：

- 参数不完整或 reviewer 未处理完：`422`
- 状态冲突：`409`
- 权限不足：`403`

## 权限与访问回收

`cancelled` 后必须立即阻断：

- `/review/invite?...`
- `/reviewer/workspace/[id]`
- attachment signed URL
- review submit

当前系统已经在 magic link / session 校验里对 `cancelled` 做阻断，因此第二期主要工作是：

- 让业务入口正式使用 `cancelled`
- 不再只依赖隐式收尾逻辑

## UI 设计建议

### 第一期

- reviewer 评论框放大
- 保留当前表单结构
- `Comment to Authors` 优先更高、更明显
- `Private note to Editor` 也明显增高，但次一级

### 第二期

在稿件详情页新增一个 “结束外审 / 进入下一步” 流程面板：

- 展示已提交 reviewer
- 展示自动将被 cancel 的 `selected / invited / opened`
- 单列出 `accepted 但未提交` reviewer
- 要求 AE 对每位 reviewer 做明确处理：
  - `继续等待`
  - `取消并发邮件`

## 风险

1. 当前 reviewer 自动推进 `decision` 的逻辑需要回退
   - 不能再以“全部 completed”作为唯一推进条件

2. 现有 `pending` / `accepted` / `completed` 的兼容映射较多
   - 第二期要谨慎处理旧数据

3. `cancel` 不能重用当前 `unassign/delete` 逻辑
   - 否则会破坏审计和历史

## 测试策略

### 第一期

- 前端：
  - reviewer workspace 表单渲染测试
  - reviewer summary 不再显示 score
- 后端：
  - reviewer 提交后不再写 `score`

### 第二期

- 单元测试：
  - 状态流转
  - cancel 权限
  - first / final decision 选项限制
- 集成测试：
  - 部分 reviewer 完成后 AE 提前进入 decision
  - 自动 cancel 未响应 reviewer
  - AE 处理 accepted 未提交 reviewer
  - cancelled reviewer 无法继续访问
- E2E：
  - reviewer invite -> accept -> workspace
  - AE 收到部分报告 -> 进入下一步 -> 被 cancel reviewer 无法再进入

## Context7 依据

### React

基于 React 官方 `textarea` 文档：

- `rows` 是标准高度控制方式
- 用户默认可手动 resize
- 没必要为这轮快改引入复杂 autosize 依赖

### FastAPI

基于 FastAPI 官方错误处理文档：

- 用 `HTTPException`
- 状态冲突使用 `409`
- 校验失败使用 `422`
- 资源不存在使用 `404`

## 结论

本轮 reviewer / decision / cancel 需求应拆成两期：

### 第一期

- 放大 reviewer 评论框
- 去掉 score

### 第二期

- AE 在部分 review 完成后即可推进 decision
- first / final decision 口径收敛
- 自动 / 手动 cancel reviewer
- cancel 后立即回收 reviewer 访问权限

这条路径风险最小，也最符合当前代码基础。
