# Tasks: Enhance Manuscripts Process List with Filters and Actions

**Input**: Design documents from `specs/032-enhance-process-list/`
**Prerequisites**: plan.md, spec.md, data-model.md, openapi.yaml
**Organization**: Tasks are grouped by user story to ensure independent implementation and testability.

## Phase 1: Setup

**Purpose**: Initialize backend search capabilities and filter logic.

- [ ] T001 Implement dynamic filter query builder (Status, Journal, Editor, Search) in `backend/app/services/editor_service.py`
- [ ] T002 Implement unit tests for filter logic (including multi-status and text search) in `backend/tests/unit/test_editor_service.py`

---

## Phase 2: User Story 1 - Advanced Filtering (Priority: P1)

**Goal**: Enable multi-dimension filtering via URL parameters.

**Independent Test**: Navigate to `/editor/process?status=under_review&journal_id=...` and verify the API returns filtered results.

- [ ] T003 [US1] Update `GET /api/v1/editor/manuscripts/process` to support new query parameters in `backend/app/api/v1/editor.py`
- [ ] T004 [US1] Create `ProcessFilterBar` component with URL sync logic (useSearchParams) in `frontend/src/components/editor/ProcessFilterBar.tsx`
- [ ] T005 [US1] Integrate `ProcessFilterBar` into the process page layout in `frontend/src/app/(admin)/editor/process/page.tsx`
- [ ] T006 [US1] Implement server-side search integration tests in `backend/tests/integration/test_editor_service.py`
- [ ] T006b [US1] Create basic E2E test for list filtering in `frontend/tests/e2e/process_list_basic.spec.ts`

---

## Phase 3: User Story 2 - Quick Actions (Priority: P1)

**Goal**: Provide inline quick actions for high-frequency tasks.

**Independent Test**: Click "Pre-check" on a row, complete the modal, and verify status update without page reload.

- [ ] T007 [US2] Create `QuickPrecheckModal` component (Shadcn Dialog) in `frontend/src/components/editor/QuickPrecheckModal.tsx`
- [ ] T008 [US2] Implement `POST /api/v1/editor/manuscripts/{id}/quick-precheck` endpoint in `backend/app/api/v1/editor.py` (Delegating to `EditorialService.update_status` for state transition)
- [ ] T009 [US2] Create `ManuscriptActions` component (Icon Buttons) in `frontend/src/components/editor/ManuscriptActions.tsx`
- [ ] T010 [US2] Integrate `ManuscriptActions` into the `ManuscriptTable` columns in `frontend/src/components/editor/ManuscriptTable.tsx`

---

## Phase 4: User Story 3 - Precision Timing (Priority: P2)

**Goal**: Standardize timestamp display.

**Independent Test**: Verify dates in the table match `YYYY-MM-DD HH:mm`.

- [ ] T011 [US3] Update `ManuscriptTable` date formatting to use `yyyy-MM-dd HH:mm` in `frontend/src/components/editor/ManuscriptTable.tsx`

---

## Phase 5: Polish & Cross-Cutting Concerns

- [ ] T012 Implement debounce logic for the text search input in `frontend/src/components/editor/ProcessFilterBar.tsx`
- [ ] T013 Final E2E test verifying filter persistence and quick action flows in `frontend/tests/e2e/process_list_enhancements.spec.ts`

---

## Dependencies & Execution Order

1. **Phase 1** is foundational for all list data.
2. **Phase 2** (Filters) and **Phase 3** (Actions) can run in parallel after Phase 1.
3. **Phase 4** is a minor UI update.

## Parallel Execution Examples

- **Backend/Frontend**: Phase 2 (Backend API) and Phase 2 (Frontend FilterBar) can be developed in parallel.
- **Components**: `QuickPrecheckModal` (T007) can be built independently of the table integration.

## Implementation Strategy

1. **Backend First**: Ensure the list API supports all filter combinations.
2. **Component Composition**: Build the FilterBar and Actions as standalone components before integrating into the main page.
