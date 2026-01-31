---
description: "Task list for Feature 016: Comprehensive QA & E2E Regression"
---

# Tasks: Feature 016 - Comprehensive QA & E2E Regression

**Input**: Design documents from `/specs/016-qa-regression/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: This is a pure testing feature. All tasks are effectively implementing tests or test infrastructure.

**Organization**: Tasks are grouped by user story (User Journey) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Test infrastructure initialization and basic structure.

- [X] T001 Implement DB Reset endpoint (truncate tables) in `backend/app/api/v1/internal.py`
- [X] T002 Implement DB Seed endpoint (seed test users/journals) in `backend/app/api/v1/internal.py`
- [X] T003 Implement `MockCrossrefClient` in `backend/app/services/crossref_client.py` (controlled by env var)
- [X] T004 Update `backend/main.py` to dependency-inject Crossref client based on config
- [X] T005 [P] Setup Playwright configuration (base URL, timeouts, mobile viewports) in `frontend/playwright.config.ts`
- [X] T006 [P] Create shared Playwright fixtures/helpers (login, db-reset) in `frontend/tests/e2e/utils.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story test can run.

- [X] T007 Fix database migration conflict (articles vs manuscripts reference) in `supabase/migrations/20260130210000_doi_registration.sql`
- [X] T008 Update `backend/app/core/schema.sql` to match current migration state (merged 013+015)
- [X] T009 Ensure `auth.users` references have `ON DELETE` policies in `supabase/migrations/` (verify manually or via script)
- [X] T010 Verify `api/v1/internal/reset-db` works correctly (truncates data, preserves schema) via curl/script

**Checkpoint**: Foundation ready - DB reset/seed works, Mock client is injectable.

---

## Phase 3: User Story 1 - Author Critical User Journey (Priority: P1)

**Goal**: Validate Author registration, login, submission, and status tracking.

**Independent Test**: Run `frontend/tests/e2e/author-flow.spec.ts` independently.

### Implementation for User Story 1

- [X] T011 [P] [US1] Create Author Flow test file `frontend/tests/e2e/author-flow.spec.ts`
- [X] T012 [P] [US1] Implement "Author Registration" test case in `frontend/tests/e2e/author-flow.spec.ts`
- [X] T013 [P] [US1] Implement "Author Login" test case in `frontend/tests/e2e/author-flow.spec.ts`
- [X] T014 [P] [US1] Implement "Submit Manuscript" test case (metadata + PDF upload) in `frontend/tests/e2e/author-flow.spec.ts`
- [X] T015 [P] [US1] Implement "Check Dashboard Status" test case in `frontend/tests/e2e/author-flow.spec.ts`
- [ ] T016 [US1] Run Author Flow tests and fix any discovered UI/API bugs

**Checkpoint**: Author flow is fully covered and passing.

---

## Phase 4: User Story 2 - Editor Critical User Journey (Priority: P1)

**Goal**: Validate Editor assignment, decision making, and publishing.

**Independent Test**: Run `frontend/tests/e2e/editor-flow.spec.ts` independently.

### Implementation for User Story 2

- [X] T017 [P] [US2] Create Editor Flow test file `frontend/tests/e2e/editor-flow.spec.ts`
- [X] T018 [P] [US2] Implement "Editor Login & Dashboard Load" test case in `frontend/tests/e2e/editor-flow.spec.ts`
- [X] T019 [P] [US2] Implement "Assign Reviewer" test case in `frontend/tests/e2e/editor-flow.spec.ts`
- [X] T020 [P] [US2] Implement "Submit Decision (Accept)" test case in `frontend/tests/e2e/editor-flow.spec.ts`
- [X] T021 [P] [US2] Implement "Verify Published Status" test case in `frontend/tests/e2e/editor-flow.spec.ts`
- [ ] T022 [US2] Run Editor Flow tests and fix any discovered UI/API bugs

**Checkpoint**: Editor flow is fully covered and passing.

---

## Phase 5: User Story 3 - CMS Content Management (Priority: P2)

**Goal**: Validate CMS page creation and public rendering.

**Independent Test**: Run `frontend/tests/e2e/cms-flow.spec.ts` independently.

### Implementation for User Story 3

- [X] T023 [P] [US3] Create CMS Flow test file `frontend/tests/e2e/cms-flow.spec.ts`
- [X] T024 [P] [US3] Implement "Admin Create Page" test case in `frontend/tests/e2e/cms-flow.spec.ts`
- [X] T025 [P] [US3] Implement "Public Page View" test case in `frontend/tests/e2e/cms-flow.spec.ts`
- [X] T026 [P] [US3] Implement "Admin Update Menu" test case in `frontend/tests/e2e/cms-flow.spec.ts`
- [ ] T027 [US3] Run CMS Flow tests and fix any discovered UI/API bugs

**Checkpoint**: CMS functionality is verified.

---

## Phase 6: User Story 4 - DOI Registration Integration (Priority: P2)

**Goal**: Validate DOI registration trigger and status.

**Independent Test**: Run `frontend/tests/e2e/doi-flow.spec.ts` independently.

### Implementation for User Story 4

- [X] T028 [P] [US4] Create DOI Flow test file `frontend/tests/e2e/doi-flow.spec.ts`
- [X] T029 [P] [US4] Implement "Trigger DOI Registration (via Publish)" test case in `frontend/tests/e2e/doi-flow.spec.ts`
- [X] T030 [P] [US4] Implement "Verify DOI Metadata on Public Page" test case in `frontend/tests/e2e/doi-flow.spec.ts`
- [X] T031 [P] [US4] Implement "Verify Admin DOI Dashboard" test case in `frontend/tests/e2e/doi-flow.spec.ts`
- [ ] T032 [US4] Run DOI Flow tests (with Mock Client) and fix any integration bugs

**Checkpoint**: DOI integration is verified (mocked).

---

## Phase 7: User Story 5 - AI Matchmaker Integration (Priority: P3)

**Goal**: Validate AI Reviewer suggestions UI.

**Independent Test**: Run `frontend/tests/e2e/ai-matchmaker.spec.ts` independently.

### Implementation for User Story 5

- [X] T033 [P] [US5] Create AI Matchmaker test file `frontend/tests/e2e/ai-matchmaker.spec.ts`
- [X] T034 [P] [US5] Implement "Open Assignment Modal & Load Suggestions" test case in `frontend/tests/e2e/ai-matchmaker.spec.ts`
- [ ] T035 [US5] Run AI Matchmaker tests and fix any discovered bugs

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: General stability and clean-up.

- [X] T036 [P] Ensure mobile responsiveness for all CUJs (configure Playwright projects for Mobile Chrome)
- [X] T037 Standardize error toast messages across Frontend components (Refactor `toast.error` calls)
- [ ] T038 Verify backend test coverage > 80% for `doi`, `cms`, `manuscripts` services
- [ ] T039 Run full regression suite locally (`npm run test:e2e`)
- [X] T040 Update `docs/TESTING.md` with new E2E instructions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 (DB Reset needed for verification).
- **User Stories (Phase 3-7)**: All depend on Phase 2 completion. Can run in parallel.
- **Polish (Phase 8)**: Depends on all user stories being covered.

### User Story Dependencies

- **US1 (Author)**: Independent.
- **US2 (Editor)**: Independent (uses seeded data).
- **US3 (CMS)**: Independent.
- **US4 (DOI)**: Depends on US2 (Publishing triggers DOI), but can test independently if seeded with published article.
- **US5 (AI)**: Independent.

### Parallel Opportunities

- Once Phase 2 is done, 5 different developers could write the 5 test specs (T011, T017, T023, T028, T033) simultaneously.
- Implementation of Mock Client (T003) can happen parallel to DB Reset (T001).

---

## Implementation Strategy

### MVP First (Critical Flows)

1. Complete Phase 1 & 2 (Infrastructure).
2. Complete Phase 3 (Author) & 4 (Editor).
3. **STOP and VALIDATE**: Core publishing workflow is safe.

### Full Regression

1. Add Phase 5 (CMS) & 6 (DOI).
2. Add Phase 7 (AI).
3. Polish and final CI run.