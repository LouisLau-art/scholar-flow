# Tasks: Revision & Resubmission Loop

**Feature**: Revision & Resubmission Loop (020-manuscript-revision)

## Implementation Strategy

We will implement this feature in phases, starting with the database schema changes, followed by the backend logic for requesting and submitting revisions, and finally the frontend interfaces for Editors and Authors.

- **Phase 1 (Setup)**: Create necessary database tables and update existing schemas.
- **Phase 2 (Foundational)**: Backend API endpoints for revision workflow.
- **Phase 3 (User Story 1)**: Editor "Request Revision" flow.
- **Phase 4 (User Story 2)**: Author "Submit Revision" flow.
- **Phase 5 (User Story 3)**: Editor "Re-review/Final Decision" flow.
- **Phase 6 (Polish)**: Notifications, email templates, and UI refinements.

## Dependencies

- Phase 3 depends on Phase 2 & Phase 1.
- Phase 4 depends on Phase 3.
- Phase 5 depends on Phase 4.

## Phase 1: Setup

- [x] T001 [P] Write SQL migration for `manuscript_versions` table in `supabase/migrations/20260201000000_create_manuscript_versions.sql`
- [ ] T002 [P] Write SQL migration for `revisions` table in `supabase/migrations/20260201000001_create_revisions.sql`
- [ ] T003 [P] Write SQL migration to add `version` column to `manuscripts` table in `supabase/migrations/20260201000002_update_manuscripts_version.sql`
- [ ] T004 [P] Write SQL migration to add `round_number` column to `review_assignments` table in `supabase/migrations/20260201000003_update_review_assignments.sql`
- [ ] T005 Run migrations to update local database schema

## Phase 2: Foundational

- [ ] T006 [P] Implement Pydantic models for `Revision` and `ManuscriptVersion` in `backend/app/models/revision.py`
- [ ] T007 [P] Implement API schemas for revision requests and submissions in `backend/app/schemas/revision.py`
- [ ] T008 [P] Implement `RevisionService` class methods (create_request, submit_revision) in `backend/app/services/revision_service.py`

## Phase 3: User Story 1 - Editor Requests Revision

- [ ] T009 [US1] Implement `create_revision_request` method in `RevisionService` (snapshotting + status update) in `backend/app/services/revision_service.py`
- [ ] T010 [US1] Implement FastAPI endpoint logic for `POST /api/v1/editor/revisions` in `backend/app/api/v1/editor.py`
- [ ] T011 [US1] Update `EditorPipeline` component to handle `revision_requested` status in `frontend/src/components/EditorPipeline.tsx`
- [ ] T012 [US1] Implement React component `RequestRevisionModal` for Editor in `frontend/src/components/editor/RequestRevisionModal.tsx`
- [ ] T013 [US1] Integrate `RequestRevisionModal` into `EditorDashboard` in `frontend/src/components/EditorDashboard.tsx`

## Phase 4: User Story 2 - Author Submits Revision

- [ ] T014 [US2] Implement `submit_revision` method in `RevisionService` (file upload + version increment) in `backend/app/services/revision_service.py`
- [ ] T015 [US2] Implement FastAPI endpoint logic for `POST /api/v1/manuscripts/{id}/revisions` in `backend/app/api/v1/manuscripts.py`
- [ ] T016 [US2] Update `AuthorDashboard` to show "Submit Revision" button for `revision_requested` items in `frontend/src/components/AuthorDashboard.tsx`
- [ ] T017 [US2] Implement React page `SubmitRevisionPage` (or modal) with Rich Text Editor and File Upload in `frontend/src/app/submit-revision/[id]/page.tsx`
- [ ] T018 [US2] Implement file versioning logic (rename on upload) in `backend/app/core/storage.py` (or relevant service)

## Phase 5: User Story 3 - Editor Processes Resubmission

- [ ] T019 [US3] Update `get_editor_pipeline` to highlight `resubmitted` manuscripts in `backend/app/api/v1/editor.py`
- [ ] T020 [US3] Implement FastAPI endpoint logic for `get_manuscript_versions` in `backend/app/api/v1/manuscripts.py`
- [ ] T021 [US3] Frontend: Display version history and response letter in `ManuscriptDetail` view in `frontend/src/components/ManuscriptDetail.tsx`
- [ ] T022 [US3] Update `ReviewerAssignModal` to support assigning for specific rounds (Round 2+) in `frontend/src/components/ReviewerAssignModal.tsx`
- [ ] T023 [US3] Backend: Ensure new review assignments link to the correct `round_number` in `backend/app/api/v1/reviews.py`

## Phase 6: Polish & Cross-Cutting

- [ ] T024 Trigger email notifications for "Revision Requested" and "Revision Submitted" in `backend/app/services/notification_service.py`
- [ ] T025 Add E2E test for full revision loop in `frontend/tests/e2e/specs/revision_flow.spec.ts`
- [ ] T026 Verify file download links point to the correct version in `frontend/src/components/ManuscriptDetail.tsx`
