# Tasks: Reviewer Library Management

**Spec**: [specs/030-reviewer-library-management/spec.md](spec.md)
**Status**: In Progress

## Phase 1: Setup
*Goal: Initialize database schema changes for extended profile fields.*

- [x] T001 Create migration to add `is_reviewer_active` and a fast search index to `public.user_profiles` in `supabase/migrations/20260204210000_reviewer_library_active_and_search.sql`

## Phase 2: Foundational
*Goal: Establish backend models and schemas required for all stories.*

- [x] T002 Update Profile domain model to include `title`, `homepage_url`, and `is_reviewer_active` in `backend/app/models/user.py`
- [x] T003 Create Reviewer API schemas (Create, Update, Response) in `backend/app/schemas/reviewer.py`

## Phase 3: User Story 1 - Build Reviewer Library (P1)
*Goal: Allow editors to add reviewers to the pool without triggering immediate emails.*
*Independent Test*: Add a new reviewer with full details via API/UI; verify `auth.users` and `public.user_profiles` exist, but no email is sent.

- [x] T004 [US1] Implement `add_to_library` service logic (handle `auth.users` creation/linking) in `backend/app/services/reviewer_service.py`
- [x] T005 [US1] Implement `POST /api/v1/editor/reviewer-library` endpoint in `backend/app/api/v1/editor.py`
- [x] T006 [US1] Create integration test for library addition (verify no email sent) in `backend/tests/integration/test_reviewer_library.py`
- [x] T007 [US1] Implement `AddReviewerModal` component in `frontend/src/components/editor/AddReviewerModal.tsx`
- [x] T008 [US1] Create Reviewer Library page in `frontend/src/app/(admin)/editor/reviewers/page.tsx`
- [x] T009 [US1] Integrate "Add to Library" API call in `frontend/src/services/editorApi.ts`
- [x] T010 [US1] Implement `DELETE /api/v1/editor/reviewer-library/{id}` (soft delete via `is_reviewer_active=false`) in `backend/app/api/v1/editor.py`
- [x] T011 [US1] Add "Remove from Library" action in `frontend/src/components/editor/ReviewerLibraryList.tsx`

## Phase 4: User Story 2 - Search and Assign from Library (P1)
*Goal: Enable searching the library and assigning reviewers to manuscripts.*
*Independent Test*: Search for a reviewer by interest, select them, and assign to a manuscript (triggering the standard invitation).

- [x] T012 [P] [US2] Implement `search_reviewers` logic (active-only) in `backend/app/services/reviewer_service.py`
- [x] T013 [P] [US2] Implement `GET /api/v1/editor/reviewer-library` endpoint in `backend/app/api/v1/editor.py`
- [x] T014 [US2] Create `ReviewerLibraryList` component in `frontend/src/components/editor/ReviewerLibraryList.tsx`
- [x] T015 [US2] Create `ReviewerAssignmentSearch` component in `frontend/src/components/editor/ReviewerAssignmentSearch.tsx`
- [x] T016 [US2] Integrate existing assign flow with library selection in `frontend/src/components/ReviewerAssignModal.tsx`

## Phase 5: User Story 3 - Reviewer Profile Completion (P2)
*Goal: View and edit detailed reviewer metadata.*
*Independent Test*: Open a reviewer profile, update the Homepage URL, and verify persistence.

- [x] T017 [P] [US3] Implement `get_reviewer` and `update_reviewer` in `backend/app/services/reviewer_service.py`
- [x] T018 [P] [US3] Implement `GET` and `PUT` `/api/v1/editor/reviewer-library/{id}` endpoints in `backend/app/api/v1/editor.py`
- [x] T019 [US3] Support editing details via modal in `frontend/src/components/editor/ReviewerLibraryList.tsx`

## Phase 6: Polish & Cross-Cutting
*Goal: Final UI refinements and performance checks.*

- [ ] T020 Verify index usage and search performance (<500ms) via `EXPLAIN ANALYZE` on cloud Supabase (manual check)
- [x] T021 Ensure responsive design for Reviewer Library table (horizontal scroll) in `frontend/src/components/editor/ReviewerLibraryList.tsx`
- [x] T022 Sync implementation details back to `specs/030-reviewer-library-management/contracts/openapi.yaml`

## Dependencies

1. **Phase 1 & 2** are blocking for all subsequent phases.
2. **Phase 3 (US1)** establishes the data population mechanism.
3. **Phase 4 (US2)** depends on Phase 3 (needs data to search).
4. **Phase 5 (US3)** depends on Phase 3 (needs data to edit).

## Parallel Execution Examples

- **Backend/Frontend Split**:
  - Developer A implements T004, T005, T006 (Backend US1).
  - Developer B implements T007, T008 (Frontend US1) using mocked API responses.
- **Story Split**:
  - Once Phase 2 is done, US2 Backend (T010, T011) and US3 Backend (T015, T016) can be started in parallel with US1 Frontend.

## Implementation Strategy

1. **MVP (US1 + US2)**: Focus on getting data IN (Add) and OUT (Search/Assign) to unblock the core workflow.
2. **Enhancement (US3)**: Add editing capabilities once the flow is stable.
