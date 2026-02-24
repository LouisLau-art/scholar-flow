# Tasks: Editor Performance Refactor

**Input**: Design documents from `/specs/001-editor-performance-refactor/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`)
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 初始化性能基线与报告工作区，确保后续任务有统一落盘位置

- [X] T001 Create feature artifact workspace README in `specs/001-editor-performance-refactor/artifacts/README.md`
- [X] T002 Create baseline capture script scaffold in `scripts/perf/capture-editor-baseline.sh`
- [X] T003 [P] Create baseline comparison script scaffold in `scripts/perf/compare-editor-baseline.sh`
- [X] T004 [P] Create baseline schema template in `specs/001-editor-performance-refactor/artifacts/baseline.schema.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 建立三条用户故事共享的性能模型、缓存抽象和门禁脚本

**⚠️ CRITICAL**: 该阶段完成前，不进入任一用户故事实现

- [X] T005 Add performance metric type definitions in `frontend/src/types/performance.ts`
- [X] T006 [P] Add browser perf recorder utility in `frontend/src/services/perfMetrics.ts`
- [X] T007 [P] Extend scoped cache/inflight invalidation helpers in `frontend/src/services/editorApi.ts`
- [X] T008 Add regression report writer script in `scripts/perf/write-regression-report.sh`
- [X] T009 Add feature-specific release validation wrapper in `scripts/validate-editor-performance.sh`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - 编辑详情页快速可操作 (Priority: P1) 🎯 MVP

**Goal**: 保证详情页核心信息先可操作，延迟区块不阻塞，用户动作只触发局部刷新，并具备超时重试入口

**Independent Test**: 打开高负载稿件详情页，验证首屏先可操作、时间线/卡片延后加载且操作后不触发整页重载；模拟超时后可见明确重试入口

### Tests for User Story 1

- [X] T010 [P] [US1] Add detail core-first load orchestration test in `frontend/src/app/(admin)/editor/manuscript/[id]/__tests__/page.performance.test.tsx`
- [X] T011 [P] [US1] Add deferred timeline/cards rendering test in `frontend/src/components/editor/__tests__/audit-log-timeline.performance.test.tsx`
- [X] T012 [P] [US1] Add targeted refresh-only behavior test for notebook actions in `frontend/src/components/editor/__tests__/internal-notebook-mentions.test.tsx`
- [X] T013 [P] [US1] Add timeout and retry-entry behavior test in `frontend/src/app/(admin)/editor/manuscript/[id]/__tests__/page.performance.test.tsx`

### Implementation for User Story 1

- [X] T014 [US1] Enforce initial `skip_cards=true` + staged hydration flow in `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- [X] T015 [US1] Guard viewport-triggered loaders to avoid duplicate deferred requests in `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- [X] T016 [US1] Add explicit timeout state and retry action for deferred blocks in `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- [X] T017 [US1] Align timeline aggregate fallback and retry prompt behavior in `frontend/src/components/editor/AuditLogTimeline.tsx`
- [X] T018 [US1] Keep notebook/task mutations on targeted context refresh only in `frontend/src/components/editor/InternalNotebook.tsx`
- [X] T019 [US1] Ensure backend detail payload parity between core and deferred paths in `backend/app/api/v1/editor_detail.py`
- [X] T020 [US1] Add/adjust API tests for detail staged loading behavior in `backend/tests/integration/test_editor_timeline.py`
- [X] T021 [US1] Verify timeline-context/card-context failure fallback behavior in `backend/tests/integration/test_internal_collaboration_flow.py`

**Checkpoint**: User Story 1 should be independently functional and testable

---

## Phase 4: User Story 2 - 审稿人分配与候选搜索响应稳定 (Priority: P2)

**Goal**: 审稿候选链路统一实现“弹窗后加载 + 搜索防抖 + 结果短缓存 + 正确失效”

**Independent Test**: 同稿件同关键词重复搜索时，首次请求走网络，20 秒内重复请求命中缓存，切换稿件或上下文后自动失效

### Tests for User Story 2

- [X] T022 [P] [US2] Add modal debounce behavior test in `frontend/src/components/ReviewerAssignModal.test.tsx`
- [X] T023 [P] [US2] Add reviewer search short-cache hit/miss test in `frontend/src/services/__tests__/editorApi.reviewer-library-cache.test.ts`
- [X] T024 [P] [US2] Add modal context-switch invalidation test in `frontend/src/components/ReviewerAssignModal.test.tsx`

### Implementation for User Story 2

- [X] T025 [US2] Implement reviewer scoped cache (20s TTL + inflight dedupe + invalidation) in `frontend/src/services/editorApi.ts`
- [X] T026 [US2] Refactor modal candidate fetch to use open-triggered load and cached search API in `frontend/src/components/ReviewerAssignModal.tsx`
- [X] T027 [US2] Ensure assignment entry passes stable manuscript context to modal search flow in `frontend/src/components/editor/ReviewerAssignmentSearch.tsx`
- [X] T028 [US2] Preserve invite policy metadata correctness on cache hit in `frontend/src/components/ReviewerAssignModal.tsx`
- [X] T029 [US2] Add API-level regression checks for reviewer library query parameters in `backend/tests/integration/test_reviewer_library.py`

**Checkpoint**: User Story 2 should be independently functional and testable

---

## Phase 5: User Story 3 - Process/Workspace 与性能基线治理 (Priority: P3)

**Goal**: 将降载策略扩展到 process/workspace，并建立改前改后基线与门禁报告，同时补齐 RBAC 无回归验证

**Independent Test**: 在固定样本下输出 before/after 报告，process/workspace 达到目标阈值；RBAC 回归通过且 release validation 给出可追溯结论

### Tests for User Story 3

- [X] T030 [P] [US3] Add process panel staged-load regression test in `frontend/src/components/editor/__tests__/manuscripts-process-panel.performance.test.tsx`
- [X] T031 [P] [US3] Add workspace stale-response guard test in `frontend/src/pages/editor/workspace/__tests__/page.performance.test.tsx`
- [X] T032 [P] [US3] Add release validation smoke test for performance gate in `backend/tests/integration/test_release_validation_gate.py`
- [X] T033 [P] [US3] Add RBAC regression for process/workspace visibility in `frontend/tests/e2e/specs/rbac-journal-scope.spec.ts`
- [X] T034 [P] [US3] Add reviewer assignment RBAC and policy regression checks in `backend/tests/integration/test_editor_invite.py`

### Implementation for User Story 3

- [X] T035 [US3] Apply core-first + deferred refresh strategy to process list pipeline in `frontend/src/components/editor/ManuscriptsProcessPanel.tsx`
- [X] T036 [US3] Add workspace request dedupe and incremental refresh flow in `frontend/src/pages/editor/workspace/page.tsx`
- [X] T037 [US3] Extend workspace service call options and error normalization in `frontend/src/services/editorService.ts`
- [X] T038 [US3] Complete release-validation contract coverage for readiness/finalize/report in `specs/001-editor-performance-refactor/contracts/editor-performance.openapi.yaml`
- [X] T039 [US3] Capture before/after baseline outputs in `specs/001-editor-performance-refactor/artifacts/baseline-before.json` and `specs/001-editor-performance-refactor/artifacts/baseline-after.json`
- [X] T040 [US3] Write regression gate summary report in `specs/001-editor-performance-refactor/artifacts/regression-report.md`
- [X] T041 [US3] Update validation workflow with baseline and gate steps in `specs/001-editor-performance-refactor/quickstart.md`

**Checkpoint**: User Story 3 should be independently functional and testable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 做全链路收口、文档同步、反馈指标闭环与宪法发布门禁收尾

- [X] T042 [P] Sync performance snapshot updates in `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`
- [X] T043 Record Tier-1/Tier-2 validation commands and outputs in `specs/001-editor-performance-refactor/artifacts/test-log-tier12.md`
- [X] T044 [P] Record Tier-3 full regression and gate outcome in `specs/001-editor-performance-refactor/artifacts/test-log-tier3.md`
- [X] T045 Define 7-day feedback metric scope, data source, and baseline window in `specs/001-editor-performance-refactor/artifacts/feedback-metrics-plan.md`
- [ ] T046 Collect and compare 7-day feedback delta report for SC-005 in `specs/001-editor-performance-refactor/artifacts/feedback-7day-report.md`
- [ ] T047 Execute release closure checklist (merge-to-main / branch cleanup / GitHub Actions green) in `specs/001-editor-performance-refactor/artifacts/release-closure-checklist.md`
- [X] T048 [P] Final consistency pass for spec artifacts in `specs/001-editor-performance-refactor/plan.md`, `specs/001-editor-performance-refactor/research.md`, `specs/001-editor-performance-refactor/data-model.md`, and `specs/001-editor-performance-refactor/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependency, start immediately
- **Phase 2 (Foundational)**: depends on Phase 1, blocks all user stories
- **Phase 3/4/5 (User Stories)**: all depend on Phase 2 completion
- **Phase 6 (Polish)**: depends on selected user stories being complete

### User Story Dependencies

- **US1 (P1)**: depends only on Foundational phase
- **US2 (P2)**: depends only on Foundational phase, no hard dependency on US1
- **US3 (P3)**: depends only on Foundational phase, can run parallel to US2 after capacity allows

### Within Each User Story

- Tests first (or at least in same phase before final verify)
- Core data-flow implementation before UI wiring
- Story-specific validation before moving to next checkpoint

### Parallel Opportunities

- Setup: T003, T004 can run in parallel after T001
- Foundational: T006, T007 parallel; T008 and T009 parallel after T005
- US1: T010-T013 parallel; T014/T015 parallel then T016-T018
- US2: T022-T024 parallel; T025 and T026 parallel then T027-T029
- US3: T030-T034 parallel; T035 and T036 parallel then T037-T041
- Polish: T042, T044, T048 parallel; T043 after validation commands; T046 after T045; T047 after T044

---

## Parallel Example: User Story 1

```bash
# Tests in parallel
Task: "T010 [US1] detail core-first load test in frontend/src/app/(admin)/editor/manuscript/[id]/__tests__/page.performance.test.tsx"
Task: "T011 [US1] deferred timeline/cards test in frontend/src/components/editor/__tests__/audit-log-timeline.performance.test.tsx"
Task: "T013 [US1] timeout and retry-entry test in frontend/src/app/(admin)/editor/manuscript/[id]/__tests__/page.performance.test.tsx"

# Implementation in parallel (different files)
Task: "T016 [US1] timeout state + retry action in frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx"
Task: "T017 [US1] timeline fallback/retry prompt in frontend/src/components/editor/AuditLogTimeline.tsx"
```

## Parallel Example: User Story 2

```bash
# Tests in parallel
Task: "T022 [US2] modal debounce test in frontend/src/components/ReviewerAssignModal.test.tsx"
Task: "T023 [US2] short-cache hit/miss test in frontend/src/services/__tests__/editorApi.reviewer-library-cache.test.ts"
Task: "T024 [US2] context invalidation test in frontend/src/components/ReviewerAssignModal.test.tsx"

# Implementation in parallel
Task: "T025 [US2] scoped cache implementation in frontend/src/services/editorApi.ts"
Task: "T026 [US2] modal cached fetch refactor in frontend/src/components/ReviewerAssignModal.tsx"
```

## Parallel Example: User Story 3

```bash
# Tests in parallel
Task: "T030 [US3] process panel staged-load test in frontend/src/components/editor/__tests__/manuscripts-process-panel.performance.test.tsx"
Task: "T032 [US3] release validation smoke test in backend/tests/integration/test_release_validation_gate.py"
Task: "T033 [US3] process/workspace RBAC regression test in frontend/tests/e2e/specs/rbac-journal-scope.spec.ts"

# Implementation in parallel
Task: "T035 [US3] process staged loading in frontend/src/components/editor/ManuscriptsProcessPanel.tsx"
Task: "T036 [US3] workspace dedupe refresh in frontend/src/pages/editor/workspace/page.tsx"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1
2. Complete Phase 2
3. Complete Phase 3 (US1)
4. Validate US1 independently using its test and quickstart scenario
5. If needed, release as first optimization increment

### Incremental Delivery

1. Setup + Foundational
2. Deliver US1 (detail page)
3. Deliver US2 (reviewer candidate search)
4. Deliver US3 (process/workspace + baseline governance)
5. Polish and full regression gate + release closure

### Parallel Team Strategy

1. One owner handles foundational cache/perf abstraction
2. Then split by story:
- Owner A: US1
- Owner B: US2
- Owner C: US3
3. Merge at Phase 6 with unified regression evidence and release closure checklist

---

## Notes

- T042/T048 属于治理类任务（文档同步与一致性复核），不直接绑定业务需求但为宪法要求。
- T047 为宪法强制发布门禁任务，必须在进入实现收尾时执行。
- All tasks follow required checklist format with IDs, optional `[P]`, story labels, and file paths.
