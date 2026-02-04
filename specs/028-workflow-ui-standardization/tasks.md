# Tasks: Workflow and UI Standardization

**Input**: Design documents from `specs/028-workflow-ui-standardization/`
**Prerequisites**: plan.md, spec.md, data-model.md, openapi.yaml
**Organization**: Tasks are grouped by user story to ensure independent implementation and testability.

## Phase 1: Setup (Core Schema & Models)

**Purpose**: Initialize the database and backend models to support the new 12-stage lifecycle and extended metadata.

- [ ] T001 Create Supabase migration for `manuscripts.status` enum update and `invoice_metadata` column in `supabase/migrations/20260204000000_update_manuscript_status.sql`
- [ ] T002 Create Supabase migration for `user_profiles` academic fields (title, institution, interests) in `supabase/migrations/20260204000001_extend_user_profiles.sql`
- [ ] T003 Create `status_transition_logs` table migration in `supabase/migrations/20260204000002_create_transition_logs.sql`
- [ ] T004 [P] Update Python `ManuscriptStatus` Enum in `backend/app/models/manuscript.py`
- [ ] T005 [P] Update `UserProfile` model with academic fields in `backend/app/models/user.py`
- [ ] T006 [P] Create `StatusTransitionLog` model in `backend/app/models/audit.py`

---

## Phase 2: Foundational (Backend Logic)

**Purpose**: Implement the core service logic for managing state transitions and auditing.

- [ ] T007 Implement `EditorialService.update_status` with validation and logging in `backend/app/services/editorial_service.py`
- [ ] T008 [P] Implement `EditorialService.update_invoice_info` in `backend/app/services/editorial_service.py`
- [ ] T009 Create unit tests for 12-stage status machine transitions in `backend/tests/unit/test_editorial_service.py`

---

## Phase 3: User Story 1 - Centralized Manuscript Processing (Priority: P1)

**Goal**: Implement the new "Manuscripts Process" table view with filtering.

**Independent Test**: Navigate to `/editor/manuscripts-process` and verify manuscripts load in a table with correct columns and working "Journal" filter.

### Implementation for User Story 1

- [ ] T010 [US1] Implement `GET /api/v1/editor/manuscripts/process` endpoint in `backend/app/api/v1/editor.py`
- [ ] T011 [P] [US1] Create `ManuscriptTable` component using Shadcn UI in `frontend/src/components/editor/ManuscriptTable.tsx`
- [ ] T012 [P] [US1] Create `ProcessFilterBar` component in `frontend/src/components/editor/ProcessFilterBar.tsx`
- [ ] T013 [US1] Create "Manuscripts Process" page in `frontend/src/app/editor/process/page.tsx`
- [ ] T014 [US1] Update `useManuscriptsProcess` hook to support new filters in `frontend/src/services/editorHooks.ts`

---

## Phase 4: User Story 2 - Comprehensive Lifecycle Management (Priority: P1)

**Goal**: Complete the "Manuscript Details" page and post-acceptance workflow.

**Independent Test**: Open a manuscript details page, advance it through `Layout` and `English Editing`, and verify the status updates in the main table.

### Implementation for User Story 2

- [ ] T015 [US2] Create dedicated "Manuscript Details" page layout in `frontend/src/app/editor/manuscript/[id]/page.tsx`
- [ ] T016 [P] [US2] Implement `FileManagementCard` for Cover Letter/Original Files in `frontend/src/components/editor/FileManagementCard.tsx`
- [ ] T017 [P] [US2] Implement `InvoiceInfoSection` with "Edit" modal in `frontend/src/components/editor/InvoiceInfoSection.tsx`
- [ ] T018 [US2] Implement `PATCH /api/v1/editor/manuscripts/{id}/status` endpoint in `backend/app/api/v1/editor.py`
- [ ] T019 [US2] Implement `PUT /api/v1/editor/manuscripts/{id}/invoice-info` endpoint in `backend/app/api/v1/editor.py`
- [ ] T020 [US2] Add status transition buttons (e.g., "Move to Layout") to details page in `frontend/src/app/editor/manuscript/[id]/page.tsx`

---

## Phase 5: User Story 3 - Refined Reviewer and Owner Management (Priority: P2)

**Goal**: Decouple reviewer library management from assignment and implement independent owner binding.

**Independent Test**: Add a reviewer without sending an invite, then bind an internal owner from the process table.

### Implementation for User Story 3

- [ ] T021 [US3] Update "Add Reviewer" modal to library-only logic in `frontend/src/components/editor/AddReviewerModal.tsx`
- [ ] T022 [P] [US3] Implement `BindingOwnerDropdown` in `frontend/src/components/editor/BindingOwnerDropdown.tsx`
- [ ] T023 [US3] Add "Binding Owner" column/action to the process table in `frontend/src/components/editor/ManuscriptTable.tsx`
- [ ] T024 [US3] Implement `POST /api/v1/editor/manuscripts/{id}/bind-owner` in `backend/app/api/v1/editor.py`

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T025 Format all table timestamps using `date-fns` in `frontend/src/components/editor/ManuscriptTable.tsx`
- [ ] T026 Update global navigation: Rename "Pipeline" to "Manuscripts Process" in `frontend/src/components/layout/Sidebar.tsx`
- [ ] T027 [P] Ensure all new status labels have consistent colors in `frontend/src/lib/statusStyles.ts`
- [ ] T028 Perform final E2E verification of the 12-stage flow using Playwright in `frontend/tests/e2e/workflow_standardization.spec.ts`

---

## Dependencies & Execution Order

1. **Phase 1 & 2** are foundational and block all frontend work.
2. **Phase 3 (US1)** is the MVP for the new table view.
3. **Phase 4 (US2)** depends on the table view for navigation (clicking IDs).
4. **Phase 5 (US3)** can be done independently after Phase 3.

## Parallel Execution Examples

- **Backend/Frontend Split**: T010 (Backend API) and T011/T012 (Frontend UI) can run in parallel.
- **Components**: T016 and T017 can be developed simultaneously.

## Implementation Strategy

1. **Database First**: Run migrations to enable the new 12 states.
2. **MVP View**: Replace the card view with the basic table (US1) to unblock daily operations.
3. **Incremental States**: Implement post-acceptance states (`Layout` onwards) last.
