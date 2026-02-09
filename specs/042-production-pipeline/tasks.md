# Tasks: Production Pipeline Workspace (录用后生产协作闭环)

**Input**: Design documents from `/root/scholar-flow/specs/042-production-pipeline/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.yaml, quickstart.md

**Tests**: 包含测试任务（后端单元/集成 + 前端单元 + E2E），因为规格明确了独立验收标准，且项目质量基线要求关键链路可回归。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- All tasks include exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 初始化 Feature 042 的迁移与模块骨架。

- [X] T001 创建生产协作迁移骨架 `supabase/migrations/20260209xxxxxx_production_pipeline_workspace.sql`
- [X] T002 创建生产协作后端模型骨架 `backend/app/models/production_workspace.py`
- [X] T003 [P] 创建生产协作后端服务骨架 `backend/app/services/production_workspace_service.py`
- [X] T004 [P] 创建编辑端生产工作间页面骨架 `frontend/src/app/(admin)/editor/production/[id]/page.tsx`
- [X] T005 [P] 创建作者校对页面骨架 `frontend/src/app/proofreading/[id]/page.tsx`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 所有用户故事共享的底层能力；完成前不进入 US 开发。

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 完成生产轮次/校对反馈/修正条目表与索引迁移 `supabase/migrations/20260209xxxxxx_production_pipeline_workspace.sql`
- [X] T007 [P] 在迁移中创建私有 bucket `production-proofs` 与最小访问策略 `supabase/migrations/20260209xxxxxx_production_pipeline_workspace.sql`
- [X] T008 [P] 定义 Pydantic 请求/响应模型与枚举 `backend/app/models/production_workspace.py`
- [X] T009 实现服务层基础读写与权限校验框架 `backend/app/services/production_workspace_service.py`
- [X] T010 在编辑端路由注册生产工作间基础端点 `backend/app/api/v1/editor.py`
- [X] T011 [P] 在作者端路由注册校对提交基础端点 `backend/app/api/v1/manuscripts.py`
- [X] T012 [P] 扩展编辑端 API 客户端基础方法 `frontend/src/services/editorApi.ts`
- [X] T013 [P] 扩展作者端 API 客户端基础方法 `frontend/src/services/manuscriptApi.ts`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - 排版编辑提交清样 (Priority: P1) 🎯 MVP

**Goal**: 编辑可创建生产轮次、上传清样并触发待作者校对。

**Independent Test**: 对录用稿件执行“创建轮次 + 上传清样”，系统应生成活跃轮次并进入 `awaiting_author`，重复创建被阻止。

### Tests for User Story 1

- [X] T014 [P] [US1] 新增轮次创建与活跃轮次冲突单测 `backend/tests/unit/test_production_workspace_service.py`
- [X] T015 [P] [US1] 新增工作间上下文与创建轮次集成测试 `backend/tests/integration/test_production_workspace_api.py`
- [X] T016 [P] [US1] 新增清样上传与文件类型校验集成测试 `backend/tests/integration/test_production_workspace_api.py`
- [X] T017 [P] [US1] 新增编辑端生产工作间状态单测 `frontend/tests/unit/production-workspace.test.tsx`

### Implementation for User Story 1

- [X] T018 [US1] 实现生产轮次创建与上下文查询逻辑 `backend/app/services/production_workspace_service.py`
- [X] T019 [US1] 实现编辑端工作间查询端点 `GET /api/v1/editor/manuscripts/{id}/production-workspace` 于 `backend/app/api/v1/editor.py`
- [X] T020 [US1] 实现编辑端创建轮次端点 `POST /api/v1/editor/manuscripts/{id}/production-cycles` 于 `backend/app/api/v1/editor.py`
- [X] T021 [US1] 实现清样上传端点 `POST /api/v1/editor/manuscripts/{id}/production-cycles/{cycle_id}/galley` 于 `backend/app/api/v1/editor.py`
- [X] T022 [US1] 实现编辑端清样签名下载端点 `backend/app/api/v1/editor.py`
- [X] T023 [US1] 实现编辑端生产工作间主页面交互 `frontend/src/app/(admin)/editor/production/[id]/page.tsx`
- [X] T024 [US1] 实现编辑端生产组件（轮次卡片/上传表单/状态视图）`frontend/src/components/editor/production/ProductionWorkspacePanel.tsx`
- [X] T025 [US1] 写入“新清样待校对”通知与审计事件 `backend/app/services/production_workspace_service.py`

**Checkpoint**: User Story 1 should be fully functional and independently testable.

---

## Phase 4: User Story 2 - 作者提交校对结论 (Priority: P1)

**Goal**: 作者可对清样执行“确认无误”或“提交修正清单”，并形成可追踪记录。

**Independent Test**: 作者访问待校对轮次并提交两种分支之一，系统应正确保存数据并更新轮次状态。

### Tests for User Story 2

- [X] T026 [P] [US2] 新增作者校对分支与校验规则单测 `backend/tests/unit/test_production_workspace_service.py`
- [X] T027 [P] [US2] 新增作者校对提交流程集成测试 `backend/tests/integration/test_proofreading_author_flow.py`
- [X] T028 [P] [US2] 新增作者校对表单分支单测 `frontend/tests/unit/author-proofreading.test.tsx`
- [X] T029 [P] [US2] 新增作者校对 E2E 场景（confirm/corrections）`frontend/tests/e2e/specs/production_pipeline.spec.ts`

### Implementation for User Story 2

- [X] T030 [US2] 实现作者端清样签名 URL 读取与归属校验 `backend/app/api/v1/manuscripts.py`
- [X] T031 [US2] 实现作者校对提交端点 `POST /api/v1/manuscripts/{id}/production-cycles/{cycle_id}/proofreading` 于 `backend/app/api/v1/manuscripts.py`
- [X] T032 [US2] 实现校对响应与修正条目持久化逻辑 `backend/app/services/production_workspace_service.py`
- [X] T033 [US2] 实现重复提交锁定与截止时间校验 `backend/app/services/production_workspace_service.py`
- [X] T034 [US2] 实现作者校对页面交互 `frontend/src/app/proofreading/[id]/page.tsx`
- [X] T035 [US2] 实现作者校对组件（决策切换/修正条目编辑/截止提示）`frontend/src/components/author/proofreading/ProofreadingForm.tsx`
- [X] T036 [US2] 对接作者端 API 与提交反馈状态管理 `frontend/src/services/manuscriptApi.ts`
- [X] T037 [US2] 写入“待排版修订/作者已确认”通知事件 `backend/app/services/production_workspace_service.py`

**Checkpoint**: User Stories 1 and 2 should both work independently.

---

## Phase 5: User Story 3 - 编辑完成发布前核准 (Priority: P2)

**Goal**: 编辑仅在作者确认后核准生产版本，并把该版本作为唯一可发布依据。

**Independent Test**: 对作者已确认轮次执行核准后，发布仅可使用该轮次版本；若未确认则核准失败。

### Tests for User Story 3

- [X] T038 [P] [US3] 新增核准前置条件单测（必须 author_confirmed）`backend/tests/unit/test_production_workspace_service.py`
- [X] T039 [P] [US3] 新增核准端点权限与状态冲突集成测试 `backend/tests/integration/test_production_workspace_api.py`
- [X] T040 [P] [US3] 新增发布门禁与核准轮次绑定集成测试 `backend/tests/integration/test_production_publish_gate.py`
- [X] T041 [P] [US3] 新增前端核准按钮可用性与提示单测 `frontend/tests/unit/production-approval.test.tsx`

### Implementation for User Story 3

- [X] T042 [US3] 实现轮次核准逻辑与核准字段落库 `backend/app/services/production_workspace_service.py`
- [X] T043 [US3] 实现编辑端核准端点 `POST /api/v1/editor/manuscripts/{id}/production-cycles/{cycle_id}/approve` 于 `backend/app/api/v1/editor.py`
- [X] T044 [US3] 将发布流程接入“已核准轮次”门禁校验 `backend/app/services/production_service.py`
- [X] T045 [US3] 在启用 Production Gate 时同步发布文件指针 `backend/app/services/production_workspace_service.py`
- [X] T046 [US3] 实现编辑端核准操作面板 `frontend/src/components/editor/production/ProductionActionPanel.tsx`
- [X] T047 [US3] 在生产工作间页面接入核准操作与状态刷新 `frontend/src/app/(admin)/editor/production/[id]/page.tsx`

**Checkpoint**: User Stories 1-3 should remain independently testable and publish-safe.

---

## Phase 6: User Story 4 - 生产过程可审计回溯 (Priority: P3)

**Goal**: 编辑与管理层可按时间线回看生产流程关键事件和操作者。

**Independent Test**: 对完成至少一轮流程的稿件，工作间可显示完整且按时间排序的生产历史。

### Tests for User Story 4

- [X] T048 [P] [US4] 新增生产审计事件完整性与排序集成测试 `backend/tests/integration/test_production_workspace_audit.py`
- [X] T049 [P] [US4] 新增前端时间线渲染与空状态单测 `frontend/tests/unit/production-timeline.test.tsx`

### Implementation for User Story 4

- [X] T050 [US4] 实现生产审计事件写入与统一 payload 构建 `backend/app/services/production_workspace_service.py`
- [X] T051 [US4] 扩展工作间上下文返回轮次历史与审计时间线 `backend/app/api/v1/editor.py`
- [X] T052 [US4] 实现生产时间线组件 `frontend/src/components/editor/production/ProductionTimeline.tsx`
- [X] T053 [US4] 在编辑端工作间集成时间线展示面板 `frontend/src/app/(admin)/editor/production/[id]/page.tsx`

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 全局收尾、文档同步与回归稳定性。

- [X] T054 [P] 根据落地实现回写契约细节 `specs/042-production-pipeline/contracts/api.yaml`
- [X] T055 [P] 更新快速验收步骤与真实命令 `specs/042-production-pipeline/quickstart.md`
- [X] T056 同步 Feature 042 关键约定到上下文文件 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`
- [X] T057 [P] 补齐 E2E mock 数据以稳定 CI-like 场景 `frontend/tests/e2e/specs/production_pipeline.spec.ts`
- [X] T058 清理生产链路冗余逻辑并保持行为一致 `backend/app/services/production_service.py` 与 `frontend/src/services/editorApi.ts`
- [X] T059 执行 quickstart 全链路验收并记录结论 `specs/042-production-pipeline/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: 可立即开始。
- **Phase 2 (Foundational)**: 依赖 Phase 1，且阻塞所有用户故事。
- **Phase 3-6 (User Stories)**: 依赖 Phase 2 完成。
- **Phase 7 (Polish)**: 依赖目标用户故事完成。

### User Story Dependencies

- **US1 (P1)**: 无业务前置，Foundational 后优先实现（MVP 核心）。
- **US2 (P1)**: 依赖 US1 提供活跃轮次与清样上传基础。
- **US3 (P2)**: 依赖 US1 + US2（需要作者确认后的轮次）。
- **US4 (P3)**: 依赖 US1-3 产生完整审计事件流。

### Within Each User Story

- 测试任务先行（至少先写出会失败的关键断言）。
- 服务与数据层先于路由层。
- 路由/API 完成后再接前端交互。
- 每个故事完成后必须独立回归。

### Parallel Opportunities

- Setup 中 T003/T004/T005 可并行。
- Foundational 中 T007/T008/T011/T012/T013 可并行。
- US1 测试任务 T014-T017 可并行。
- US2 测试任务 T026-T029 可并行。
- US3 测试任务 T038-T041 可并行。
- US4 测试任务 T048-T049 可并行。
- Polish 中 T054/T055/T057 可并行。

---

## Parallel Example: User Story 1

```bash
# US1 tests in parallel
Task: "T014 [US1] backend unit tests in backend/tests/unit/test_production_workspace_service.py"
Task: "T015 [US1] backend integration tests in backend/tests/integration/test_production_workspace_api.py"
Task: "T017 [US1] frontend unit tests in frontend/tests/unit/production-workspace.test.tsx"

# US1 implementation parallel slice (different files)
Task: "T021 [US1] galley upload endpoint in backend/app/api/v1/editor.py"
Task: "T024 [US1] editor UI panel in frontend/src/components/editor/production/ProductionWorkspacePanel.tsx"
```

## Parallel Example: User Story 2

```bash
Task: "T027 [US2] backend integration tests in backend/tests/integration/test_proofreading_author_flow.py"
Task: "T028 [US2] frontend unit tests in frontend/tests/unit/author-proofreading.test.tsx"
Task: "T029 [US2] e2e scenario in frontend/tests/e2e/specs/production_pipeline.spec.ts"
```

## Parallel Example: User Story 3

```bash
Task: "T039 [US3] approve endpoint integration tests in backend/tests/integration/test_production_workspace_api.py"
Task: "T041 [US3] frontend approval tests in frontend/tests/unit/production-approval.test.tsx"
Task: "T044 [US3] publish gate integration in backend/app/services/production_service.py"
```

## Parallel Example: User Story 4

```bash
Task: "T048 [US4] audit integration tests in backend/tests/integration/test_production_workspace_audit.py"
Task: "T049 [US4] timeline component tests in frontend/tests/unit/production-timeline.test.tsx"
Task: "T052 [US4] timeline component in frontend/src/components/editor/production/ProductionTimeline.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. 完成 Phase 1 + Phase 2。
2. 完成 Phase 3 (US1)。
3. 执行 US1 独立验收（创建轮次 + 上传清样 + 重复创建拦截）。
4. 通过后再进入作者校对链路。

### Incremental Delivery

1. US1 上线后交付“排版提交清样”能力。
2. US2 增量交付“作者校对反馈”能力。
3. US3 增量交付“发布前核准门禁”能力。
4. US4 增量交付“管理审计回溯”能力。

### Parallel Team Strategy

1. 一人先完成 Foundational。
2. 并行分工：
   - 开发 A：后端服务与 API（US1-3）
   - 开发 B：前端工作间与作者页面（US1-3）
   - 开发 C：审计与测试体系（US4 + cross-cutting）

---

## Notes

- 所有任务遵循严格格式：`- [ ] Txxx [P] [USx] 描述 + 文件路径`。
- `[USx]` 仅用于用户故事阶段；Setup/Foundational/Polish 不打 `[USx]`。
- 每个故事必须可独立实现、独立测试、独立演示。
- 任务冲突优先通过拆分文件边界解决，避免同文件并发改动。
