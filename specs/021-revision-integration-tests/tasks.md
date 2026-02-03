# Tasks: Revision & Resubmission Integration Tests

**Feature**: Revision & Resubmission Integration Tests (021-revision-integration-tests)

## Phase 1: Setup

- [X] T001 Create `backend/tests/integration/conftest.py` with shared fixtures (Supabase client, user generation)
- [X] T002 Configure `frontend/playwright.config.ts` if needed for new test patterns (optional)

## Phase 2: Foundational

- [X] T003 Implement `backend/tests/integration/test_utils.py` with helpers for creating manuscripts and auth tokens

## Phase 3: Backend Integration Tests (User Story 1)

**Goal**: Verify the correctness of the Revision & Resubmission logic, data integrity, and security controls via API tests.
**Independent Test**: Run `pytest backend/tests/integration/test_revision_cycle.py` and ensure all tests pass against a local database.

- [X] T004 [US1] Create `backend/tests/integration/test_revision_cycle.py` with `test_happy_path_revision_loop` (Scenario 1)
- [X] T005 [US1] Add `test_rbac_enforcement` to `backend/tests/integration/test_revision_cycle.py` (Scenario 2)
- [X] T006 [US1] Add `test_file_safety` to `backend/tests/integration/test_revision_cycle.py` (Scenario 3)
- [X] T007 [US1] Verify all backend tests pass

## Phase 4: Frontend E2E Tests (User Story 2)

**Goal**: Verify the user interface elements for the revision workflow are visible and interactive via browser automation.
**Independent Test**: Run `npx playwright test frontend/tests/e2e/specs/revision_flow.spec.ts` and verify successful execution.

- [X] T008 [US2] Create/Update `frontend/tests/e2e/specs/revision_flow.spec.ts` with "Editor Requests Revision" flow
- [X] T009 [US2] Add "Author Submits Revision" flow to `frontend/tests/e2e/specs/revision_flow.spec.ts` (verify "Submit Revision" button visibility)
- [X] T010 [US2] Add "Editor Verifies Resubmission" flow to `frontend/tests/e2e/specs/revision_flow.spec.ts` (verify "Resubmitted" column)
- [X] T011 [US2] Verify E2E tests pass

## Final Phase: Polish

- [X] T012 Verify both test suites run in CI-like environment (locally)
- [X] T013 Update `quickstart.md` if any new test commands are discovered

## Dependencies

- Phase 4 depends on UI elements from Feature 020 being present.

## Parallel Execution Examples

- **Backend**: T004, T005, T006 can be implemented in parallel if T003 (utils) is ready.
- **Frontend**: T008, T009, T010 can be drafted in parallel but depend on each other for the full flow test.

## Implementation Strategy

1.  **Backend First**: Validate the core logic and safety guarantees first. This is the P1 requirement.
2.  **Frontend Second**: Ensure the UI exposes the validated backend logic correctly.
