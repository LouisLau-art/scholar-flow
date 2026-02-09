# Tasks: GAP-P0-03 Internal Collaboration Enhancement

**Input**: Design documents from `/root/scholar-flow/specs/045-internal-collaboration-enhancement/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.yaml, quickstart.md

**Tests**: 本特性明确要求“可回归的协作闭环与逾期筛选准确性”，需要补齐后端单元/集成、前端单测与 mocked E2E。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All tasks include exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 建立 045 的迁移、类型与基础脚手架。

- [x] T001 新增迁移文件 `supabase/migrations/20260209190000_internal_collaboration_mentions_tasks.sql`，创建 mention/task/activity 三张表与必要索引
- [x] T002 在 `backend/app/models/internal_task.py` 新建内部任务状态与优先级枚举模型
- [x] T003 [P] 在 `frontend/src/types/internal-collaboration.ts` 定义 comment mention、task、activity 的前端类型
- [x] T004 [P] 在 `frontend/tests/e2e/specs/internal-collaboration-overdue.spec.ts` 创建 045 E2E 用例骨架与 mock 路由基线

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 所有故事共享的基础能力，完成前不得进入 US1/US2/US3。

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T005 在 `backend/app/services/internal_collaboration_service.py` 实现提及校验与去重通知的基础服务骨架
- [x] T006 [P] 在 `backend/app/services/internal_task_service.py` 实现任务 CRUD/状态流转/轨迹写入服务骨架
- [x] T007 [P] 在 `backend/app/api/v1/editor.py` 增加 045 所需 DTO（comment mention payload、task create/update payload）
- [x] T008 [P] 在 `backend/tests/contract/test_api_paths.py` 注册并校验 `/editor/manuscripts/{id}/tasks*` 新端点路径/方法
- [x] T009 在 `backend/app/services/editor_service.py` 为 Process 查询扩展 `overdue_only` 过滤参数与聚合占位字段
- [x] T010 在 `backend/app/api/v1/editor.py` 扩展 `/editor/manuscripts/process` 查询参数以接收 `overdue_only`
- [x] T011 [P] 在 `frontend/src/services/editorApi.ts` 与 `frontend/src/services/editorService.ts` 增加 045 的 API 方法签名与调用包装
- [x] T012 [P] 在 `frontend/src/components/editor/TaskStatusBadge.tsx` 新增任务状态展示组件（todo/in_progress/done）
- [x] T013 在 `backend/app/api/v1/editor.py` 增加 migration 缺失 fail-open/错误映射（mention/task 表缺失时返回可识别错误）

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Notebook @提及协作 (Priority: P1) 🎯 MVP

**Goal**: 在内部评论中实现可校验的 @提及并触发站内提醒。

**Independent Test**: 发布带 `mention_user_ids` 的内部评论后，被提及人收到一次提醒，评论可正确回显提及信息。

### Tests for User Story 1

- [x] T014 [P] [US1] 在 `backend/tests/integration/test_internal_collaboration_flow.py` 新增“评论提及->提醒写入->去重”集成测试
- [x] T015 [P] [US1] 在 `backend/tests/unit/test_internal_collaboration_service.py` 新增提及对象校验与重复提及去重单测
- [x] T016 [P] [US1] 在 `frontend/src/components/editor/__tests__/internal-notebook-mentions.test.tsx` 新增提及输入与提交行为单测

### Implementation for User Story 1

- [x] T017 [US1] 在 `backend/app/api/v1/editor.py` 改造 `POST /manuscripts/{id}/comments` 以接收 `mention_user_ids`
- [x] T018 [US1] 在 `backend/app/services/internal_collaboration_service.py` 实现提及落库与通知派发逻辑
- [x] T019 [US1] 在 `backend/app/api/v1/editor.py` 改造 `GET /manuscripts/{id}/comments` 返回 `mention_user_ids`
- [x] T020 [US1] 在 `frontend/src/services/editorApi.ts` 改造 `postInternalComment` 支持提及对象数组
- [x] T021 [US1] 在 `frontend/src/components/editor/InternalNotebook.tsx` 实现提及对象选择与提交 payload 组装
- [x] T022 [US1] 在 `frontend/src/components/editor/InternalNotebook.tsx` 增加评论提及渲染（高亮/列表）
- [x] T023 [US1] 在 `frontend/src/components/editor/InternalNotebook.tsx` 增加无效提及与重复提及的错误提示
- [x] T024 [US1] 在 `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx` 接入 Notebook 提及使用说明与刷新联动

**Checkpoint**: User Story 1 should be fully functional and independently testable.

---

## Phase 4: User Story 2 - 内部任务化协作 (Priority: P1)

**Goal**: 支持稿件内部任务创建、分配、状态流转与活动轨迹可追踪。

**Independent Test**: 新建任务并更新状态（todo->in_progress->done），可在详情页看到状态变化和活动日志。

### Tests for User Story 2

- [x] T025 [P] [US2] 在 `backend/tests/unit/test_internal_task_service.py` 新增任务状态机与权限单测
- [x] T026 [P] [US2] 在 `backend/tests/integration/test_internal_collaboration_flow.py` 新增任务创建/更新/轨迹集成测试
- [x] T027 [P] [US2] 在 `frontend/src/components/editor/__tests__/internal-tasks-panel.test.tsx` 新增任务面板渲染与交互单测

### Implementation for User Story 2

- [x] T028 [US2] 在 `backend/app/services/internal_task_service.py` 实现任务创建、列表、更新与活动日志写入
- [x] T029 [US2] 在 `backend/app/api/v1/editor.py` 新增 `POST /manuscripts/{id}/tasks`
- [x] T030 [US2] 在 `backend/app/api/v1/editor.py` 新增 `GET /manuscripts/{id}/tasks`
- [x] T031 [US2] 在 `backend/app/api/v1/editor.py` 新增 `PATCH /manuscripts/{id}/tasks/{task_id}`
- [x] T032 [US2] 在 `backend/app/api/v1/editor.py` 新增 `GET /manuscripts/{id}/tasks/{task_id}/activity`
- [x] T033 [US2] 在 `frontend/src/services/editorApi.ts` 增加任务 CRUD 与 activity API 方法
- [x] T034 [US2] 在 `frontend/src/services/editorService.ts` 增加任务操作封装与错误映射
- [x] T035 [US2] 新建 `frontend/src/components/editor/InternalTasksPanel.tsx` 实现任务列表、创建与状态变更 UI
- [x] T036 [US2] 在 `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx` 集成 `InternalTasksPanel`
- [x] T037 [US2] 在 `frontend/src/components/editor/InternalTasksPanel.tsx` 展示任务活动轨迹与操作者时间戳
- [x] T038 [US2] 在 `frontend/src/components/editor/InternalTasksPanel.tsx` 实现非授权编辑的禁用态与提示文案

**Checkpoint**: User Stories 1 and 2 should both work independently.

---

## Phase 5: User Story 3 - 逾期风险可视化与筛选 (Priority: P2)

**Goal**: Process 列表支持逾期标识和“仅看逾期”筛选。

**Independent Test**: 构造逾期/未逾期任务数据后，Process 列表显示准确逾期标识，并且筛选结果正确。

### Tests for User Story 3

- [x] T039 [P] [US3] 在 `backend/tests/integration/test_editor_service.py` 新增 `overdue_only` 聚合与筛选集成测试
- [x] T040 [P] [US3] 在 `frontend/src/components/editor/__tests__/manuscript-table.overdue.test.tsx` 新增逾期标识渲染测试
- [x] T041 [P] [US3] 在 `frontend/tests/e2e/specs/internal-collaboration-overdue.spec.ts` 完成 mocked 逾期筛选回归场景

### Implementation for User Story 3

- [x] T042 [US3] 在 `backend/app/services/editor_service.py` 实现 Process 读时聚合 `is_overdue`/`overdue_tasks_count`
- [x] T043 [US3] 在 `backend/app/api/v1/editor.py` 完成 `overdue_only` 查询参数接线与返回字段透传
- [x] T044 [US3] 在 `frontend/src/services/editorApi.ts` 扩展 `ManuscriptsProcessFilters` 支持 `overdueOnly`
- [x] T045 [US3] 在 `frontend/src/components/editor/ProcessFilterBar.tsx` 增加“仅看逾期”筛选开关并写入 URL
- [x] T046 [US3] 在 `frontend/src/components/editor/ManuscriptTable.tsx` 增加逾期标识与逾期任务计数展示
- [x] T047 [US3] 在 `frontend/src/components/editor/ManuscriptsProcessPanel.tsx` 接入 overdue 过滤参数并回刷数据
- [x] T048 [US3] 在 `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx` 增加稿件级逾期摘要展示

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 收尾验证、文档同步、发布前检查。

- [x] T049 [P] 按最终实现回写 `specs/045-internal-collaboration-enhancement/contracts/api.yaml`（错误码、示例、字段约束）
- [x] T050 [P] 按最终命令与回归结果回写 `specs/045-internal-collaboration-enhancement/quickstart.md`
- [x] T051 执行后端 045 相关测试并记录结果到 `specs/045-internal-collaboration-enhancement/quickstart.md`
- [x] T052 执行前端 Vitest + E2E 并记录结果到 `specs/045-internal-collaboration-enhancement/quickstart.md`
- [x] T053 更新 `docs/GAP_ANALYSIS_AND_ACTION_PLAN.md` 中 GAP-P0-03 的进度与剩余事项
- [x] T054 同步上下文快照到 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`（Feature 045 实施结果）
- [x] T055 在 `frontend/package.json` 与 `backend/pyproject.toml` 对应命令下完成 lint/快速检查并修复阻塞问题

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies, can start immediately.
- **Phase 2 (Foundational)**: depends on Phase 1 and blocks all user stories.
- **Phase 3-5 (User Stories)**: all depend on Phase 2 completion.
- **Phase 6 (Polish)**: depends on completed user stories.

### User Story Dependencies

- **US1 (P1)**: 可在 Foundation 后独立交付（提及协作闭环）。
- **US2 (P1)**: 可在 Foundation 后独立推进，但与 US1 联合可形成完整协作体验。
- **US3 (P2)**: 依赖 US2 的任务数据模型与状态字段，建议在 US2 完成后执行。

### Within Each User Story

- 测试任务先于实现任务。
- 后端服务实现先于 API 路由接线。
- API 层完成后再接前端 UI。
- 每个故事完成后执行其独立验收标准。

### Parallel Opportunities

- Phase 1: T003/T004 可并行。
- Phase 2: T006/T007/T008/T011/T012 可并行。
- US1: T014/T015/T016 可并行。
- US2: T025/T026/T027 可并行。
- US3: T039/T040/T041 可并行。
- Phase 6: T049/T050 可并行。

---

## Parallel Example: User Story 1

```bash
Task: "T014 [US1] 提及通知集成测试 in backend/tests/integration/test_internal_collaboration_flow.py"
Task: "T015 [US1] 提及去重单测 in backend/tests/unit/test_internal_collaboration_service.py"
Task: "T016 [US1] Notebook 提及单测 in frontend/src/components/editor/__tests__/internal-notebook-mentions.test.tsx"
```

## Parallel Example: User Story 2

```bash
Task: "T025 [US2] 任务状态机单测 in backend/tests/unit/test_internal_task_service.py"
Task: "T026 [US2] 任务 CRUD 集成测试 in backend/tests/integration/test_internal_collaboration_flow.py"
Task: "T027 [US2] 任务面板前端单测 in frontend/src/components/editor/__tests__/internal-tasks-panel.test.tsx"
```

## Parallel Example: User Story 3

```bash
Task: "T039 [US3] overdue 聚合集成测试 in backend/tests/integration/test_editor_service.py"
Task: "T040 [US3] Process 逾期渲染测试 in frontend/src/components/editor/__tests__/manuscript-table.overdue.test.tsx"
Task: "T041 [US3] overdue 筛选 E2E in frontend/tests/e2e/specs/internal-collaboration-overdue.spec.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. 完成 Phase 1 与 Phase 2。
2. 完成 US1（Notebook 提及与触达）。
3. 先做独立验收并可演示，再推进后续故事。

### Incremental Delivery

1. Setup + Foundational 完成后，先交付 US1（可触达协作）。
2. 再交付 US2（任务化协作与轨迹）。
3. 最后交付 US3（逾期风控可视化），完成上线前验证。

### Parallel Team Strategy

1. 开发者 A：后端 service + API（T017-T019, T028-T032, T042-T043）。
2. 开发者 B：前端 API + UI（T020-T024, T033-T038, T044-T048）。
3. 开发者 C：测试与验收（T014-T016, T025-T027, T039-T041, T051-T052）。
