---
description: "Task list for Feature 040: Reviewer Workspace"
---

# Tasks: Reviewer Workspace

**Input**: Design documents from `/specs/040-reviewer-workspace/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/reviewer-api.yaml
**Tests**: Unit/E2E tests included as per Constitution "Test-First" principle.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable
- **[US#]**: User Story ID

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Install `react-pdf` dependency (optional fallback) in `frontend/package.json`
- [X] T002 Create `ReviewSubmission` and `WorkspaceData` types in `frontend/src/types/review.ts`

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core backend schemas and API structure

- [X] T003 Create Pydantic schemas in `backend/app/schemas/review.py` matching `contracts/reviewer-api.yaml`
- [X] T004 Implement backend service for workspace data aggregation in `backend/app/services/reviewer_service.py`
- [X] T005 Create backend unit tests for workspace service in `backend/tests/unit/test_reviewer_service.py`

## Phase 3: User Story 1 - Immersive Manuscript Viewing (Priority: P1)

**Goal**: Split-screen interface with PDF viewer.
**Independent Test**: Load workspace -> No sidebar -> PDF visible.

### Tests for US1

- [X] T006 [P] [US1] Create E2E test for immersive layout in `frontend/tests/e2e/specs/reviewer_workspace_layout.spec.ts`

### Implementation for US1

- [X] T007 [US1] Create `frontend/src/app/(reviewer)/layout.tsx` (minimal header, no sidebar)
- [X] T008 [US1] Create `frontend/src/app/(reviewer)/workspace/[id]/page.tsx` (main container)
- [X] T009 [US1] Implement `GET /assignments/{id}/workspace` endpoint in `backend/app/api/v1/endpoints/reviewer.py`
- [X] T010 [US1] Create `PDFViewer` component in `frontend/src/app/(reviewer)/workspace/[id]/pdf-viewer.tsx` (including mobile responsive stacked layout)

## Phase 4: User Story 2 & 3 - Feedback & Submission (Priority: P1)

**Goal**: Dual-channel form, attachments, and submission.
**Independent Test**: Fill form -> Attach file -> Submit -> Verify DB status.

### Tests for US2/US3

- [X] T011 [P] [US2] Create integration test for submission endpoint in `backend/tests/integration/test_reviewer_submission.py`

### Implementation for US2/US3

- [X] T012 [P] [US2] Create `ActionPanel` component with React Hook Form in `frontend/src/app/(reviewer)/workspace/[id]/action-panel.tsx`
- [X] T013 [US2] Implement `POST /assignments/{id}/attachments` endpoint in `backend/app/api/v1/endpoints/reviewer.py`
- [X] T014 [US3] Implement `POST /assignments/{id}/submit` endpoint in `backend/app/api/v1/endpoints/reviewer.py`
- [X] T015 [US3] Add "Warn on Exit" logic using `beforeunload` in `frontend/src/app/(reviewer)/workspace/[id]/page.tsx`
- [X] T016 [US3] Implement Read-Only view state in `ActionPanel` post-submission

## Phase 5: User Story 4 - Security & Isolation (Priority: P0)

**Goal**: Strict access control.
**Independent Test**: Access unassigned ID -> 403.

### Tests for US4

- [X] T017 [P] [US4] Add security unit tests (Guest & Auth access) in `backend/tests/unit/test_reviewer_security.py`

### Implementation for US4

- [X] T018 [US4] Implement strict `assignment_id` vs `current_user` check in `backend/app/services/reviewer_service.py`
- [X] T019 [US4] Verify Signed URL generation logic enforces short expiry in `backend/app/services/manuscript_service.py`

## Phase 6: Polish

- [X] T020 [P] Update API documentation in `backend/openapi.json`
- [X] T021 Run full test suite (`./scripts/run-all-tests.sh`)

---

## Dependencies & Execution Order

1. **Setup & Foundational (T001-T005)**: Must complete first.
2. **US1 (Layout)**: Depends on Foundational (API to fetch PDF URL).
3. **US2/3 (Form)**: Depends on US1 (to host the form) and Foundational (Schemas).
4. **US4 (Security)**: Can be implemented alongside Backend Service (T004/T018).

## Implementation Strategy

1. **MVP**: Complete Phase 1-4. Delivers the full functional flow.
2. **Hardening**: Phase 5 ensures no security gaps.
