# Spec: 008 Editor Command Center

**Feature Branch**: `008-editor-command-center`
**Status**: Draft

## 背景
系统目前缺乏一个全局视角。编辑需要一个地方来管理所有处于不同生命周期的稿件，并协调审稿人。

## 用户故事 (User Stories)
- **US1 (Manuscript Pipeline)**: 作为编辑，我可以查看全站所有稿件的看板（看板分栏：待质检、评审中、待录用、已发布）。
- **US2 (Reviewer Assignment)**: 作为编辑，我可以针对特定稿件选择并指派审稿人（完善 007 中留下的后端能力）。
- **US3 (Decision Gate)**: 作为编辑，我可以查看所有审稿人的多维度打分汇总，并做出“录用”或“退回”的最终决定。

## 技术约束 (v1.9.0)
- **API**: 必须使用显性路由 `/api/v1/editor/...`。
- **QA**: 必须编写针对编辑决策逻辑的单元测试。
- **UI**: 使用 Shadcn/UI 的 `Tabs` 和 `ScrollArea` 构建高效看板。
