# Spec: 007 Reviewer Workspace

## 背景
目前评审系统仅有基础 API，前端缺乏分配界面，且评审维度过于单一，无法满足学术决策需求。

## 用户故事 (User Stories)
- **US1 (Editor Assignment)**: 作为编辑，我可以点击稿件并从审稿人列表中选择 2-3 名专家进行分配。
- **US2 (Reviewer Inbox)**: 作为审稿人，我在登录后能看到“待评审”任务列表，包含稿件标题和摘要。
- **US3 (Structured Review)**: 作为审稿人，我需要针对“创新性”、“技术严谨性”、“语言质量”进行 1-5 分的评分，并填写详细的评审意见。
- **US4 (Decision Logic)**: 当所有审稿人完成评审后，系统自动计算平均分，并标记该稿件为“待编辑终审”。

## 技术约束
- **数据库**: 新增 `review_assignments` 表，记录审稿人与稿件的绑定关系。
- **API**: 必须使用显性路由 `/api/v1/reviews/...`。
- **UI**: 使用 Shadcn/UI 的 `Form` 和 `DataTable` 组件。
- **DoD**: 包含后端对分配冲突（不能分配给自己）的校验测试。
