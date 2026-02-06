# Tasks: Pre-check Role Workflow (ME → AE → EIC)

**Feature**: Pre-check Role Workflow (038)
**Status**: Todo

## Phase 1: Setup
**Goal**: Initialize database schema changes for the new workflow.

- [x] T001 Create migration for `assistant_editor_id` and `pre_check_status` in `supabase/migrations/20260206150000_add_precheck_fields.sql`

## Phase 2: Foundational
**Goal**: Update backend models and shared schemas to support the new fields.

- [x] T002 Update `ManuscriptStatus` enum (if needed) and add `PreCheckStatus` constants in `backend/app/models/manuscript.py`
- [x] T003 Update Pydantic models `ManuscriptBase` and `Manuscript` in `backend/app/models/schemas.py` to include new fields

## Phase 3: User Story 1 (ME Intake)
**Goal**: Managing Editor performs intake pre-check and assigns AE.
**Test Criteria**:
- ME can list manuscripts in `intake` queue.
- ME can assign a manuscript to an AE, changing status to `technical`.
- Audit log records the assignment.

- [x] T004 [P] [US1] Create integration test for ME intake flow in `backend/tests/integration/test_precheck_flow.py`
- [x] T005 [P] [US1] Implement `assign_ae` service logic in `backend/app/services/editor_service.py`
- [x] T006 [P] [US1] Implement `GET /editor/intake` endpoint in `backend/app/api/v1/editor/manuscripts.py`
- [x] T007 [US1] Implement `POST /editor/manuscripts/{id}/assign-ae` endpoint in `backend/app/api/v1/editor/manuscripts.py`
- [x] T008 [P] [US1] Update frontend `editorService` with `getIntakeQueue` and `assignAE` in `frontend/src/services/editorService.ts`
- [x] T009 [US1] Create `ReviewerAssignModal`-like `AssignAEModal` component in `frontend/src/components/AssignAEModal.tsx`
- [x] T010 [US1] Create ME Intake page in `frontend/src/pages/editor/intake/page.tsx` (or `app/editor/intake/page.tsx` if App Router)

## Phase 4: User Story 2 (AE Technical Check)
**Goal**: Assistant Editor performs technical check and submits to EIC.
**Test Criteria**:
- AE sees only assigned manuscripts in `technical` queue.
- AE can submit check, changing status to `academic`.

- [x] T011 [P] [US2] Update integration test for AE flow in `backend/tests/integration/test_precheck_flow.py`
- [x] T012 [P] [US2] Implement `submit_technical_check` service logic in `backend/app/services/editor_service.py`
- [x] T013 [P] [US2] Implement `GET /editor/workspace` endpoint in `backend/app/api/v1/editor/manuscripts.py`
- [x] T014 [US2] Implement `POST /editor/manuscripts/{id}/submit-check` endpoint in `backend/app/api/v1/editor/manuscripts.py`
- [x] T015 [P] [US2] Update frontend `editorService` with `getAEWorkspace` and `submitTechnicalCheck` in `frontend/src/services/editorService.ts`
- [x] T016 [US2] Create AE Workspace page in `frontend/src/pages/editor/workspace/page.tsx`

## Phase 5: User Story 3 (EIC Academic Check)
**Goal**: EIC performs academic pre-check and routes to Review or Decision.
**Test Criteria**:
- EIC sees manuscripts in `academic` queue.
- EIC can route to `under_review` (Review) or `decision` (Decision Phase).
- Direct reject is NOT offered/allowed.

- [x] T017 [P] [US3] Update integration test for EIC flow in `backend/tests/integration/test_precheck_flow.py`
- [x] T018 [P] [US3] Implement `submit_academic_check` service logic in `backend/app/services/editor_service.py`
- [x] T019 [P] [US3] Implement `GET /editor/academic` endpoint in `backend/app/api/v1/editor/manuscripts.py`
- [x] T020 [US3] Implement `POST /editor/manuscripts/{id}/academic-check` endpoint in `backend/app/api/v1/editor/manuscripts.py`
- [x] T021 [P] [US3] Update frontend `editorService` with `getAcademicQueue` and `submitAcademicCheck` in `frontend/src/services/editorService.ts`
- [x] T022 [US3] Create `AcademicCheckModal` (Decision/Review routing) in `frontend/src/components/AcademicCheckModal.tsx`
- [x] T023 [US3] Create EIC Academic Queue page in `frontend/src/pages/editor/academic/page.tsx`

## Final Phase: Polish & Cross-Cutting
**Goal**: Verify E2E flow and constraints.

- [x] T024 Create E2E test for full ME->AE->EIC flow in `frontend/tests/e2e/specs/precheck_workflow.spec.ts`
- [x] T025 Verify "No Direct Reject" constraint in backend service logic `backend/app/services/editor_service.py`

## Dependencies

1. **Setup & Foundational** (T001-T003) -> **US1** (T004-T010)
2. **US1** -> **US2** (T011-T016) (Data flow requires ME assignment first)
3. **US2** -> **US3** (T017-T023) (Data flow requires AE submission first)
4. **US3** -> **Polish** (T024-T025)

## Parallel Execution Examples

- **Within US1**: T005 (Backend Service), T008 (Frontend Service), and T009 (Frontend Component) can be developed in parallel after T003 (Models) is done.
- **Across Stories**: Frontend UI skeletons (T010, T016, T023) can be started once the API contract (T006, T013, T019) is defined, even if logic isn't fully ready.

## Implementation Strategy
- **MVP Scope**: Complete US1, US2, and US3 happy paths. Error handling (e.g., reassignment) can be basic.
- **Incremental**:
    1.  Schema & Models.
    2.  ME Intake (US1) - enables data entry.
    3.  AE Check (US2) - enables workflow progression.
    4.  EIC Check (US3) - completes pre-check.
    5.  E2E Verification.
