---
description: "Task list for Feature 037: Reviewer Invite Response"
---

# Tasks: Reviewer Invite Response

**Input**: Design documents from `/specs/037-reviewer-invite-response/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md
**Tests**: Unit/E2E tests included as per Constitution "Test-First" principle.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable
- **[US#]**: User Story ID

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 [P] Create `DeclineReason` enum in `backend/app/schemas/review.py` (if not exists)
- [X] T002 Update `ReviewAssignment` model in `backend/app/models/review_assignment.py` (add `accepted_at`, `declined_at`, `due_date`, `decline_reason`)

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core backend logic for state transitions

- [X] T003 Create DB migration for new `review_assignments` columns (`supabase/migrations/`)
- [X] T004 Implement backend state transition logic in `backend/app/services/reviewer_service.py` (invite->accept/decline)
- [X] T005 Create backend unit tests for state transitions in `backend/tests/unit/test_reviewer_invite.py`

## Phase 3: User Story 1 - Reviewer Accept/Decline (Priority: P1)

**Goal**: Reviewer can accept (with due date) or decline (with reason).
**Independent Test**: Magic Link -> Invite Page -> Accept -> DB Updated.

### Tests for US1

- [X] T006 [P] [US1] Create E2E test for accept flow in `frontend/tests/e2e/specs/reviewer_invite_accept.spec.ts`
- [X] T007 [P] [US1] Create E2E test for decline flow in `frontend/tests/e2e/specs/reviewer_invite_decline.spec.ts`

### Implementation for US1

- [X] T008 [US1] Create `frontend/src/app/(public)/review/invite/page.tsx` (Logic: Status Check & Preview)
- [X] T009 [US1] Create `AcceptForm` component in `frontend/src/app/(public)/review/invite/accept-form.tsx`
- [X] T010 [US1] Create `DeclineForm` component in `frontend/src/app/(public)/review/invite/decline-form.tsx`
- [X] T011 [US1] Implement `GET /assignments/{id}/invite` endpoint in `backend/app/api/v1/endpoints/reviewer.py`
- [X] T012 [US1] Implement `POST /assignments/{id}/accept` endpoint in `backend/app/api/v1/endpoints/reviewer.py`
- [X] T013 [US1] Implement `POST /assignments/{id}/decline` endpoint in `backend/app/api/v1/endpoints/reviewer.py`

## Phase 4: User Story 2 - Editor Timeline (Priority: P2)

**Goal**: Editor visibility of status/timestamps.
**Independent Test**: Reviewer Acts -> Editor refreshes -> Status/Timeline updated.

### Tests for US2

- [X] T014 [P] [US2] Create integration test for timeline data in `backend/tests/integration/test_editor_timeline.py`

### Implementation for US2

- [X] T015 [US2] Update `GET /editor/manuscripts/{id}` response schema to include invite timestamps
- [X] T016 [US2] Update Editor Manuscript Detail UI to show invite timeline/status in `frontend/src/app/(editor)/manuscript/[id]/page.tsx` (or component)

## Phase 5: User Story 3 - Idempotency & Safety (Priority: P3)

**Goal**: Safe re-clicks and double-submits.
**Independent Test**: Click Accept twice -> No error, single record.

### Tests for US3

- [X] T017 [P] [US3] Add unit tests for idempotent state transitions in `backend/tests/unit/test_reviewer_invite.py`

### Implementation for US3

- [X] T018 [US3] Add idempotency checks in backend `accept`/`decline` services (if status already X, return success or 409 safely)
- [X] T019 [US3] Add frontend handling for "Already Accepted" state (redirect to workspace) or "Already Declined" (show message)

## Phase 6: Polish

- [X] T020 [P] Update API documentation in `backend/openapi.json`
- [X] T021 Run full test suite (`./scripts/run-all-tests.sh`)

---

## Dependencies & Execution Order

1. **Setup & Foundational (T001-T005)**: Must complete first (DB schema).
2. **US1 (Reviewer Action)**: Core value.
3. **US2 (Editor View)**: Depends on US1 (to generate data).
4. **US3 (Safety)**: Can be done in parallel with US1 backend logic.

## Implementation Strategy

1. **MVP**: Complete Phase 1-3. This unblocks the "Invite -> Accept -> Work" flow.
2. **Hardening**: Phase 5 ensures robustness.
