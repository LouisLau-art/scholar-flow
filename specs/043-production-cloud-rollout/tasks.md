# Tasks: Cloud Rollout Regression (GAP-P0-02)

**Input**: Design documents from `/root/scholar-flow/specs/043-production-cloud-rollout/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.yaml, quickstart.md

**Tests**: 包含测试任务。该规格明确要求“真实环境回归、阻塞判定与 skip=0 放行门禁”，必须通过自动化测试保证可重复验收。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All tasks include exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 初始化 GAP-P0-02 的验收域骨架。

- [x] T001 创建 release validation 迁移骨架 `supabase/migrations/20260209160000_release_validation_runs.sql`
- [x] T002 创建 release validation 模型骨架 `backend/app/models/release_validation.py`
- [x] T003 [P] 创建 release validation 服务骨架 `backend/app/services/release_validation_service.py`
- [x] T004 [P] 创建云端放行脚本骨架 `scripts/validate-production-rollout.sh`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 所有用户故事共用的基础能力；未完成前禁止进入用户故事开发。

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T005 完成验收批次与检查明细表迁移（含索引/唯一约束）`supabase/migrations/20260209160000_release_validation_runs.sql`
- [x] T006 [P] 定义验收运行/检查/报告的 Pydantic 模型与枚举 `backend/app/models/release_validation.py`
- [x] T007 实现批次创建、列表查询、检查项写入、报告聚合基础方法 `backend/app/services/release_validation_service.py`
- [x] T008 在 internal 路由注册验收批次创建与列表端点 `backend/app/api/v1/internal.py`
- [x] T009 [P] 新增 release validation 服务单测基础 fixture 与 fake client `backend/tests/unit/test_release_validation_service.py`
- [x] T010 [P] 新增 internal 验收接口集成测试基础 fixture（含 `X-Admin-Key`）`backend/tests/integration/test_release_validation_api.py`
- [x] T011 实现脚本的参数解析、环境变量校验与统一退出码 `scripts/validate-production-rollout.sh`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - 环境就绪验证与放行 (Priority: P1) 🎯 MVP

**Goal**: 提供一键 readiness 检查，并输出可阻塞放行的明确结论与阻塞项。

**Independent Test**: 创建验收批次后执行 readiness 检查，能稳定返回 `passed/failed/blocked` 且阻塞项可追溯。

### Tests for User Story 1

- [x] T012 [P] [US1] 新增 readiness 规则与阻塞判定单测 `backend/tests/unit/test_release_validation_service.py`
- [x] T013 [P] [US1] 新增 readiness 端点集成测试（通过/失败/阻塞）`backend/tests/integration/test_release_validation_api.py`

### Implementation for User Story 1

- [x] T014 [US1] 实现 readiness 检查目录（schema/storage/permission/gate）`backend/app/services/release_validation_service.py`
- [x] T015 [US1] 实现 readiness 执行编排与批次状态更新 `backend/app/services/release_validation_service.py`
- [x] T016 [US1] 实现端点 `POST /internal/release-validation/runs/{run_id}/readiness` `backend/app/api/v1/internal.py`
- [x] T017 [US1] 在脚本中实现 `--readiness-only` 执行路径与阻塞输出 `scripts/validate-production-rollout.sh`
- [x] T018 [US1] 在 quickstart 回写 readiness 验收命令与判定标准 `specs/043-production-cloud-rollout/quickstart.md`

**Checkpoint**: User Story 1 should be fully functional and independently testable.

---

## Phase 4: User Story 2 - 真实环境回归验证 (Priority: P1)

**Goal**: 执行生产协作关键回归并强制 `skip=0` 才可放行。

**Independent Test**: 同一验收批次执行 regression 后，核心场景通过时返回 `passed`，任意关键场景 skip/失败时返回 `no-go` 信号。

### Tests for User Story 2

- [x] T019 [P] [US2] 新增 regression 结果分类与 zero-skip 规则单测 `backend/tests/unit/test_release_validation_service.py`
- [x] T020 [P] [US2] 新增 regression 端点集成测试（success/fail/skip）`backend/tests/integration/test_release_validation_api.py`

### Implementation for User Story 2

- [x] T021 [US2] 实现 regression 场景执行器（production pipeline 关键路径探针）`backend/app/services/release_validation_service.py`
- [x] T022 [US2] 实现关键场景 skip=0 放行门禁与证据收集 `backend/app/services/release_validation_service.py`
- [x] T023 [US2] 实现端点 `POST /internal/release-validation/runs/{run_id}/regression` `backend/app/api/v1/internal.py`
- [x] T024 [US2] 扩展脚本支持 readiness+regression 串联执行并在 skip 时失败退出 `scripts/validate-production-rollout.sh`
- [x] T025 [US2] 在 quickstart 回写 regression 验收步骤与 no-go 判定 `specs/043-production-cloud-rollout/quickstart.md`

**Checkpoint**: User Stories 1 and 2 should both work independently.

---

## Phase 5: User Story 3 - 上线审计与回退保障 (Priority: P2)

**Goal**: 生成可审计验收报告，并在失败时给出标准化回退指引。

**Independent Test**: 在一次失败验收后执行 finalize/report，可看到完整检查证据、go/no-go 结论与回退计划。

### Tests for User Story 3

- [x] T026 [P] [US3] 新增 finalize 决策与 rollback_required 逻辑单测 `backend/tests/unit/test_release_validation_service.py`
- [x] T027 [P] [US3] 新增 finalize/report 端点集成测试 `backend/tests/integration/test_release_validation_api.py`

### Implementation for User Story 3

- [x] T028 [US3] 实现 finalize 聚合决策（go/no-go）`backend/app/services/release_validation_service.py`
- [x] T029 [US3] 实现回退模板生成与回退状态记录 `backend/app/services/release_validation_service.py`
- [x] T030 [US3] 实现端点 `POST /internal/release-validation/runs/{run_id}/finalize` `backend/app/api/v1/internal.py`
- [x] T031 [US3] 实现端点 `GET /internal/release-validation/runs/{run_id}/report` `backend/app/api/v1/internal.py`
- [x] T032 [US3] 扩展报告响应模型（rollback 字段、release_decision）`backend/app/models/release_validation.py`
- [x] T033 [US3] 脚本输出标准化验收报告摘要与回退提示 `scripts/validate-production-rollout.sh`
- [x] T034 [US3] 在 quickstart 补齐失败分支回退执行说明 `specs/043-production-cloud-rollout/quickstart.md`

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 文档对齐、收尾验证与上下文同步。

- [x] T035 [P] 按实现回写内部验收接口契约细节 `specs/043-production-cloud-rollout/contracts/api.yaml`
- [x] T036 [P] 更新验收命令与结果记录模板 `specs/043-production-cloud-rollout/quickstart.md`
- [x] T037 同步 Feature 043 关键约定到上下文文件 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`
- [x] T038 执行后端 release-validation 相关测试并记录结果 `specs/043-production-cloud-rollout/quickstart.md`
- [x] T039 执行脚本端到端演练（dry-run + real-run）并记录输出 `scripts/validate-production-rollout.sh`
- [x] T040 更新总行动清单中 GAP-P0-02 状态与下一步 `docs/GAP_ANALYSIS_AND_ACTION_PLAN.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: can start immediately.
- **Phase 2 (Foundational)**: depends on Phase 1, and blocks all user stories.
- **Phase 3-5 (User Stories)**: depend on Phase 2 completion.
- **Phase 6 (Polish)**: depends on target user stories completion.

### User Story Dependencies

- **US1 (P1)**: no dependency on other stories once foundational is ready.
- **US2 (P1)**: no mandatory dependency on US1；可复用同一 run 流程但应独立可测。
- **US3 (P2)**: depends on US1/US2 产出的检查结果数据以形成最终报告。

### Within Each User Story

- 测试任务先于实现任务。
- 服务层先于路由层。
- 路由层先于脚本/文档联调。
- 每个故事完成后必须执行独立验收。

### Parallel Opportunities

- Setup 中 T003/T004 可并行。
- Foundational 中 T006/T009/T010 可并行。
- US1 测试任务 T012/T013 可并行。
- US2 测试任务 T019/T020 可并行。
- US3 测试任务 T026/T027 可并行。
- Polish 中 T035/T036 可并行。

---

## Parallel Example: User Story 1

```bash
Task: "T012 [US1] readiness unit tests in backend/tests/unit/test_release_validation_service.py"
Task: "T013 [US1] readiness integration tests in backend/tests/integration/test_release_validation_api.py"
Task: "T014 [US1] readiness check catalog in backend/app/services/release_validation_service.py"
```

## Parallel Example: User Story 2

```bash
Task: "T019 [US2] regression rule unit tests in backend/tests/unit/test_release_validation_service.py"
Task: "T020 [US2] regression integration tests in backend/tests/integration/test_release_validation_api.py"
Task: "T024 [US2] script regression stage in scripts/validate-production-rollout.sh"
```

## Parallel Example: User Story 3

```bash
Task: "T026 [US3] finalize decision tests in backend/tests/unit/test_release_validation_service.py"
Task: "T027 [US3] finalize/report integration tests in backend/tests/integration/test_release_validation_api.py"
Task: "T032 [US3] report schema extension in backend/app/models/release_validation.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. 完成 Phase 1 + Phase 2。
2. 完成 US1（readiness 检查）。
3. 验证“阻塞项可识别 + 可阻止放行”后再继续。

### Incremental Delivery

1. 先交付 US1，确保“上线前可判定”。
2. 再交付 US2，确保“真实回归可执行且 skip 不放行”。
3. 最后交付 US3，补齐审计报告与回退闭环。

### Parallel Team Strategy

1. 一人推进后端 service/internal API。
2. 一人推进脚本与 quickstart 验收流程。
3. 一人补齐测试与文档同步（含三份 agent context）。
