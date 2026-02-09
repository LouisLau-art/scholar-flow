# Tasks: GAP-P0-01 Pre-check Role Hardening

**Input**: Design documents from `/root/scholar-flow/specs/044-precheck-role-hardening/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.yaml, quickstart.md

**Tests**: 本特性包含测试任务。规格明确要求“标准回归场景可重复执行（ME->AE->EIC）”与越权拦截，因此必须补齐后端自动化测试与前端 E2E 回归。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All tasks include exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 为 044 预审闭环建立统一的请求/响应类型与任务脚手架。

- [x] T001 在 `backend/app/api/v1/editor.py` 补充 044 所需 DTO 草案（`AssignAERequest`、`TechnicalCheckRequest`、`AcademicCheckRequest`、`ActionAck`）
- [x] T002 [P] 在 `frontend/src/services/editorApi.ts` 增加 pre-check API 类型定义（queue item、action ack、timeline event）
- [x] T003 [P] 新建 `frontend/src/types/precheck.ts`，集中声明 pre-check 阶段与角色类型
- [x] T004 在 `specs/044-precheck-role-hardening/contracts/api.yaml` 对齐初版实现任务所需字段（decision/comment/idempotency_key）

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 所有用户故事共用的核心基础能力；未完成前禁止进入 US1/US2/US3 开发。

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T005 在 `backend/app/services/editor_service.py` 抽取 pre-check 通用辅助函数（稿件读取、阶段断言、统一时间戳、审计写入）
- [x] T006 [P] 在 `backend/app/services/editor_service.py` 实现 pre-check 操作的幂等/并发冲突框架（条件更新 + 409 冲突返回）
- [x] T007 [P] 在 `backend/app/services/editorial_service.py` 增加 pre-check 拒稿门禁单点断言（`pre_check/under_review/resubmitted` 不可直接到 `rejected`）
- [x] T008 在 `backend/app/api/v1/editor.py` 统一 pre-check 端点错误码映射（400/403/404/409/422）
- [x] T009 [P] 在 `backend/tests/contract/test_api_paths.py` 增加 pre-check 相关端点路径/方法契约检查
- [x] T010 [P] 在 `backend/tests/integration/test_editor_http_methods.py` 增加 pre-check 权限与非法流转基础回归用例
- [x] T011 在 `frontend/src/services/editorService.ts` 移除 pre-check mock/stub，改为调用 `EditorApi`
- [x] T012 [P] 在 `frontend/src/components/AssignAEModal.tsx`、`frontend/src/components/AcademicCheckModal.tsx` 接入统一 loading/error 状态和 API 错误提示骨架

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - 预审分派与角色流转闭环 (Priority: P1) 🎯 MVP

**Goal**: 让 ME 分派与 AE 技术质检形成完整、可审计、可拦截越权的闭环。

**Independent Test**: 准备 `pre_check/intake` 稿件后完成“ME 分派 AE -> AE pass/revision”，验证角色限制、修回必填、状态变更和审计日志均正确。

### Tests for User Story 1

- [x] T013 [P] [US1] 在 `backend/tests/unit/test_precheck_role_service.py` 新增 `assign_ae` 与 `submit_technical_check` 服务层单测（含幂等与冲突）
- [x] T014 [P] [US1] 在 `backend/tests/integration/test_precheck_flow.py` 新增 ME/AE 主路径集成测试（分派成功、非 ME 拒绝、非归属 AE 拒绝）
- [x] T015 [P] [US1] 在 `frontend/src/tests/services/editor/precheck.api.test.ts` 新增 pre-check API 调用参数与错误处理单测

### Implementation for User Story 1

- [x] T016 [US1] 在 `backend/app/services/editor_service.py` 实现 `get_intake_queue` 的字段扩展（`current_role/current_assignee/assigned_at`）
- [x] T017 [US1] 在 `backend/app/services/editor_service.py` 实现 `assign_ae` 的阶段校验、重分派审计 payload 与幂等处理
- [x] T018 [US1] 在 `backend/app/services/editor_service.py` 实现 `get_ae_workspace` 的归属过滤、分页排序与安全校验
- [x] T019 [US1] 在 `backend/app/services/editor_service.py` 实现 `submit_technical_check` 的 `decision=pass|revision` 及 `revision` comment 必填
- [x] T020 [US1] 在 `backend/app/api/v1/editor.py` 接入 `TechnicalCheckRequest` 并返回统一 action ack
- [x] T021 [US1] 在 `frontend/src/services/editorApi.ts` 实现 `getIntakeQueue`、`assignAE`、`getAEWorkspace`、`submitTechnicalCheck`
- [x] T022 [US1] 在 `frontend/src/pages/editor/intake/page.tsx` 与 `frontend/src/components/AssignAEModal.tsx` 完成真实分派流程（AE 列表加载 + 成功回刷）
- [x] T023 [US1] 在 `frontend/src/pages/editor/workspace/page.tsx` 增加技术质检决策 UI（pass/revision/comment）并调用新接口
- [x] T024 [US1] 在 `frontend/src/services/editorService.ts` 删除 pre-check mock 返回值并补齐类型安全返回

**Checkpoint**: User Story 1 should be fully functional and independently testable.

---

## Phase 4: User Story 2 - 学术初审与决策入口规范化 (Priority: P1)

**Goal**: 让 EIC 学术初审只能在 Academic 阶段执行，并稳定流转到外审或决策链路。

**Independent Test**: 准备 `pre_check/academic` 稿件，执行 `review` 与 `decision_phase` 两条路径，并验证预审中直接拒稿被拦截。

### Tests for User Story 2

- [x] T025 [P] [US2] 在 `backend/tests/unit/test_precheck_role_service.py` 增加 `submit_academic_check` 单测（合法 decision、非法阶段、重复提交）
- [x] T026 [P] [US2] 在 `backend/tests/integration/test_precheck_flow.py` 增加 EIC 学术初审集成测试（to review / to decision）
- [x] T027 [P] [US2] 在 `backend/tests/integration/test_editor_http_methods.py` 增加 pre-check 直接 `rejected` 的拒绝回归测试

### Implementation for User Story 2

- [x] T028 [US2] 在 `backend/app/services/editor_service.py` 实现 `get_academic_queue` 的阶段过滤与责任字段补齐
- [x] T029 [US2] 在 `backend/app/services/editor_service.py` 实现 `submit_academic_check` 的前置校验、decision 映射、审计 payload
- [x] T030 [US2] 在 `backend/app/api/v1/editor.py` 强化 `AcademicCheckRequest` 校验（decision 枚举、comment 长度、错误码）
- [x] T031 [US2] 在 `frontend/src/services/editorApi.ts` 实现 `getAcademicQueue` 与 `submitAcademicCheck`
- [x] T032 [US2] 在 `frontend/src/pages/editor/academic/page.tsx` 与 `frontend/src/components/AcademicCheckModal.tsx` 接入真实提交与结果回刷
- [x] T033 [US2] 在 `frontend/src/components/editor/QuickPrecheckModal.tsx` 兼容后端 409/422 错误文案并保持交互一致

**Checkpoint**: User Stories 1 and 2 should both work independently.

---

## Phase 5: User Story 3 - 过程可视化与验收可回归 (Priority: P2)

**Goal**: 在 Process/详情展示完整预审角色队列和关键时间戳，并提供可执行 E2E 回归脚本。

**Independent Test**: 完整跑一轮 ME->AE->EIC 后，Process 与详情页展示正确队列/时间线，`precheck_workflow.spec.ts` 稳定通过。

### Tests for User Story 3

- [x] T034 [P] [US3] 在 `backend/tests/integration/test_editor_service.py` 新增 process/detail 预审可视化字段集成测试
- [x] T035 [P] [US3] 在 `frontend/src/components/editor/__tests__/manuscript-table.precheck.test.tsx` 新增预审字段渲染测试
- [x] T036 [P] [US3] 在 `frontend/tests/e2e/specs/precheck_workflow.spec.ts` 重写可执行 mocked 回归（ME->AE->EIC）

### Implementation for User Story 3

- [x] T037 [US3] 在 `backend/app/services/editor_service.py` 为 process 列表组装 `pre_check_status/current_role/current_assignee/assigned_at/technical_completed_at/academic_completed_at`
- [x] T038 [US3] 在 `backend/app/api/v1/editor.py` 的详情接口新增 `role_queue` 与 `precheck_timeline`
- [x] T039 [US3] 在 `frontend/src/components/editor/ManuscriptTable.tsx` 增加 Pre-check Stage/Assignee 列并保持移动端可读性
- [x] T040 [US3] 在 `frontend/src/components/editor/ManuscriptsProcessPanel.tsx` 与 `frontend/src/services/editorApi.ts` 对齐新字段映射
- [x] T041 [US3] 在 `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx` 新增 Pre-check Role Queue 卡片与关键时间戳展示
- [x] T042 [US3] 在 `frontend/src/components/editor/AuditLogTimeline.tsx` 解析并高亮 pre-check payload action
- [x] T043 [US3] 在 `frontend/tests/e2e/pages/editor.page.ts` 增加 pre-check 流程 Page Object helper

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 收尾验证、文档更新与上下文同步。

- [x] T044 [P] 按最终实现回写 `specs/044-precheck-role-hardening/contracts/api.yaml`（字段、错误码、示例）
- [x] T045 [P] 按最终命令与验收结果回写 `specs/044-precheck-role-hardening/quickstart.md`
- [x] T046 执行后端预审相关测试并记录结果到 `specs/044-precheck-role-hardening/quickstart.md`
- [x] T047 执行前端 mocked E2E（`precheck_workflow.spec.ts`）并记录结果到 `specs/044-precheck-role-hardening/quickstart.md`
- [x] T048 更新 `docs/GAP_ANALYSIS_AND_ACTION_PLAN.md` 中 GAP-P0-01 的完成勾选与剩余事项
- [x] T049 同步上下文快照 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`（Feature 044 实施结果）

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies, can start immediately.
- **Phase 2 (Foundational)**: depends on Phase 1 and blocks all user stories.
- **Phase 3-5 (User Stories)**: all depend on Phase 2 completion.
- **Phase 6 (Polish)**: depends on completed user stories.

### User Story Dependencies

- **US1 (P1)**: can start right after Foundational; delivers MVP for pre-check assignment + technical check.
- **US2 (P1)**: can start right after Foundational; does not require US1 if测试数据直接种到 `academic` 阶段。
- **US3 (P2)**: depends on US1/US2 提供的稳定字段和审计数据，建议在 US1+US2 后执行。

### Within Each User Story

- 测试任务先于实现任务。
- 服务层实现先于路由层。
- API 层完成后再接前端 UI。
- 每个故事完成后执行其独立验收标准。

### Parallel Opportunities

- Phase 1: T002/T003 可并行。
- Phase 2: T006/T007/T009/T010/T012 可并行。
- US1: T013/T014/T015 可并行。
- US2: T025/T026/T027 可并行。
- US3: T034/T035/T036 可并行。
- Polish: T044/T045 可并行。

---

## Parallel Example: User Story 1

```bash
Task: "T013 [US1] 服务层单测 in backend/tests/unit/test_precheck_role_service.py"
Task: "T014 [US1] 集成测试 in backend/tests/integration/test_precheck_flow.py"
Task: "T015 [US1] 前端 API 单测 in frontend/src/tests/services/editor/precheck.api.test.ts"
```

## Parallel Example: User Story 2

```bash
Task: "T025 [US2] academic-check 单测 in backend/tests/unit/test_precheck_role_service.py"
Task: "T026 [US2] academic-check 集成测试 in backend/tests/integration/test_precheck_flow.py"
Task: "T027 [US2] 拒稿门禁测试 in backend/tests/integration/test_editor_http_methods.py"
```

## Parallel Example: User Story 3

```bash
Task: "T034 [US3] 后端可视化字段集成测试 in backend/tests/integration/test_editor_service.py"
Task: "T035 [US3] 表格渲染测试 in frontend/src/components/editor/__tests__/manuscript-table.precheck.test.tsx"
Task: "T036 [US3] E2E 回归 in frontend/tests/e2e/specs/precheck_workflow.spec.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. 完成 Phase 1 与 Phase 2。
2. 完成 US1（ME 分派 + AE 技术质检 + 审计）。
3. 先做独立验收并可演示，再推进后续故事。

### Incremental Delivery

1. Setup + Foundational 完成后，先交付 US1（最小可用预审闭环）。
2. 再交付 US2（EIC 学术初审与拒稿门禁约束）。
3. 最后交付 US3（Process/详情可视化 + E2E 回归），完成上线前验证。

### Parallel Team Strategy

1. 开发者 A：后端 service + API（T016-T020, T028-T030, T037-T038）。
2. 开发者 B：前端 API + UI（T021-T024, T031-T033, T039-T042）。
3. 开发者 C：测试与验收（T013-T015, T025-T027, T034-T036, T046-T047）。
