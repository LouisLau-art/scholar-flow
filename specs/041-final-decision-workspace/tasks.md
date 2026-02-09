# Tasks: Final Decision Workspace (Feature 041)

**Feature**: Final Decision Workspace (041)  
**Status**: Done

## Phase 1: Setup
**Goal**: 初始化决策信数据结构与附件存储。

- [X] T001 Create migration for `decision_letters` table in `supabase/migrations/20260206160000_create_decision_letters.sql`
- [X] T002 Create `decision-attachments` bucket + access policy migration in `supabase/migrations/20260206161000_decision_storage.sql`
- [X] T003 Add DB constraints/indexes for draft and optimistic locking in `supabase/migrations/20260206162000_decision_letter_constraints.sql`

## Phase 2: Foundational (Backend)
**Goal**: 实现核心服务、阶段门禁、可见性和 API。

- [X] T004 Create `DecisionLetter` request/response models in `backend/app/models/decision.py`
- [X] T005 Implement `DecisionService.get_decision_context` in `backend/app/services/decision_service.py`
- [X] T006 Implement `DecisionService.submit_decision` (draft/final + optimistic locking + stage gate + final notification trigger) in `backend/app/services/decision_service.py`
- [X] T007 Implement attachment service methods (`upload_attachment`, `get_attachment_signed_url`) in `backend/app/services/decision_service.py`
- [X] T008 Implement `GET /api/v1/editor/manuscripts/{id}/decision-context` in `backend/app/api/v1/editor.py`
- [X] T009 Implement `POST /api/v1/editor/manuscripts/{id}/submit-decision` in `backend/app/api/v1/editor.py`
- [X] T010 Implement attachment APIs: editor upload/preview in `backend/app/api/v1/editor.py`, author final-only signed-url in `backend/app/api/v1/manuscripts.py`
- [X] T011 [P] Add integration tests for state transitions (`accept/reject/revision`) and stage gate in `backend/tests/integration/test_decision_workspace.py`
- [X] T012 [P] Add integration tests for final-only visibility and author notification in `backend/tests/integration/test_decision_visibility.py`
- [X] T013 [P] Add integration test for optimistic-lock conflicts in `backend/tests/integration/test_decision_workspace.py`

## Phase 3: User Story 1 (Immersive View)
**Goal**: 完成沉浸式三栏工作间与入口守卫。
**Test Criteria**:
- Page loads at `/editor/decision/[id]` without global sidebar/footer.
- Submitted reports are shown in comparison view.
- PDF preview loads correctly.

- [X] T014 [US1] Create workspace route in `frontend/src/app/(admin)/editor/decision/[id]/page.tsx`
- [X] T015 [US1] Implement `DecisionWorkspaceLayout` (three-column) in `frontend/src/components/editor/decision/DecisionWorkspaceLayout.tsx`
- [X] T016 [US1] Implement `ReviewReportComparison` in `frontend/src/components/editor/decision/ReviewReportComparison.tsx`
- [X] T017 [P] [US1] Update editor API client methods in `frontend/src/services/editorService.ts`
- [X] T018 [US1] Add role/assignment guard and unavailable-state handling in `frontend/src/app/(admin)/editor/decision/[id]/page.tsx`

## Phase 4: User Story 2 (Draft Generation & Editing)
**Goal**: 完成 Markdown 决策信编辑和草稿流程。
**Test Criteria**:
- Clicking "Generate Letter Draft" fills editor with aggregated reviewer comments.
- User can edit and save draft, then reload and recover content.

- [X] T019 [US2] Implement `DecisionEditor` (Markdown + decision selector) in `frontend/src/components/editor/decision/DecisionEditor.tsx`
- [X] T020 [US2] Implement `assembleLetter` and wire "Generate Letter Draft" in `frontend/src/lib/decision-utils.ts` and `frontend/src/components/editor/decision/DecisionEditor.tsx`
- [X] T021 [US2] Wire Save Draft / Submit Final with `last_updated_at` in `frontend/src/components/editor/decision/DecisionEditor.tsx`
- [X] T022 [P] [US2] Add unit tests for draft generation in `frontend/tests/unit/decision-utils.test.ts`
- [X] T023 [US2] Add client-side validation (`final` requires non-empty letter) in `frontend/src/components/editor/decision/DecisionEditor.tsx`

## Phase 5: User Story 3 (Workflow Constraints & Audit)
**Goal**: 强化流程约束、审计完整性与权限验证。
**Test Criteria**:
- Reject is blocked outside `decision/decision_done`.
- `status_transition_logs` stores decision letter snapshot.
- Only `editor_in_chief` / `assigned_editor` / `admin` can operate workspace.

- [X] T024 [US3] Update transition logging payload with decision letter + attachments in `backend/app/services/editorial_service.py`
- [X] T025 [US3] Add server-side guard tests for "No Direct Reject" policy in `backend/tests/integration/test_decision_workspace.py`
- [X] T026 [US3] Add RBAC tests for decision workspace APIs in `backend/tests/integration/test_decision_rbac.py`

## Final Phase: Polish & Cross-Cutting
**Goal**: 完成易用性、反馈、一致性与性能质量门禁。

- [X] T027 Add unsaved-change protection (`useBeforeUnload`) and return-to-detail path in `frontend/src/app/(admin)/editor/decision/[id]/page.tsx`
- [X] T028 Implement attachment upload/download UI and final-only visibility hints in `frontend/src/components/editor/decision/DecisionEditor.tsx`
- [X] T029 Add success/error toast feedback for save/submit/upload in `frontend/src/app/(admin)/editor/decision/[id]/page.tsx`
- [X] T030 Add decision-context performance test (`P95 < 500ms`) in `backend/tests/integration/test_decision_context_performance.py`
- [X] T031 Add visual consistency checks against reviewer workspace in `frontend/tests/e2e/specs/decision_workspace.visual.spec.ts`
- [X] T032 Add full E2E flow (draft, conflict, final visibility) in `frontend/tests/e2e/specs/decision_workspace.spec.ts`

## Dependencies

1. **Phase 1 -> Phase 2**: Schema/storage 必须先落地。
2. **Phase 2 -> Phase 3/4**: 后端 API 与约束先稳定，再接 UI。
3. **Phase 3/4 -> Phase 5**: 有可用界面后再收紧流程和审计。
4. **Phase 5 -> Final Phase**: 核心正确性通过后再做性能/一致性门禁。

## Parallel Execution Examples

- T011 / T012 / T013 可并行（后端不同测试文件）。
- T015 与 T017 可并行（UI 布局与 API client）。
- T022 可并行（纯工具函数测试，不依赖页面集成）。

## Implementation Strategy

- **MVP Scope**: 完成 Phase 1-3 + Phase 5 的强约束项（stage gate/RBAC/audit）。
- **Incremental**:
  1. Schema & context API.
  2. Immersive workspace.
  3. Draft + final submission.
  4. Workflow hardening.
  5. Performance and UX polish.
