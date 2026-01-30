# Tasks: Editor Command Center

## Phase 1: Backend API (Explicit Routes)
- [x] T001 [P] 实现 `GET /api/v1/editor/pipeline` 看板数据接口
- [x] T002 [P] 实现 `GET /api/v1/editor/available-reviewers` 专家池接口
- [x] T003 实现 `POST /api/v1/editor/decision` 终审决策逻辑
- [x] T004 [DoD] 编写 `test_editor_actions.py` 并全绿通过

## Phase 2: UI Implementation
- [x] T005 开发 `EditorPipeline` 状态看板组件
- [x] T006 开发 `ReviewerAssignModal` 分配专家弹出框
- [x] T007 开发 `DecisionPanel` 决策工作台 (聚合 007 的评审分)

## Phase 3: Integration & Polish
- [x] T008 将 `EditorDashboard` 挂载到 `/dashboard` 的相应 Tabs
- [x] T009 验证“分配 -> 审稿 -> 终审”全链路闭环
- [x] **CP01** [最终存档] 推送全量编辑中心代码
