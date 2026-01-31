# Tasks: User Acceptance Testing (UAT) & Staging Environment Setup

**Feature**: 019-uat-staging-setup  
**Input**: [Implementation Plan](plan.md), [Research](research.md), [Contracts](contracts/api_v1_system.yaml)

## Phase 1: Setup & Configuration (Dependencies)

> **Goal**: Establish the "Staging" concept in the codebase and configure strict isolation rules.

- [x] T001 Define `APP_ENV` and `IS_STAGING` constants in `frontend/src/lib/env.ts` to centralize environment logic
- [x] T002 Update backend `app/core/config.py` to support `APP_ENV` (staging/production) and separate `SUPABASE_URL` loading
- [x] T003 Create `uat_feedback` migration SQL file in `supabase/migrations/` (User Story 2 dependency, but schema needed early)
- [x] T004 Create `rpc_truncate_all_tables` migration SQL file in `supabase/migrations/` (Required for Seed Script)
- [x] T005 [P] Create `frontend/src/components/uat/` directory for UAT-specific components

## Phase 2: Foundational Components (Blocking)

> **Goal**: Implement the shared visual indicators and core backend isolation logic.

- [x] T006 Add E2E test `tests/e2e/uat.spec.ts` verifying Banner/Widget presence in Staging and absence in Prod (Test-First)
- [x] T007 Create unit tests for `EnvironmentBanner` in `frontend/src/components/uat/__tests__/EnvironmentBanner.test.tsx` (Test-First)
- [x] T008 [P] [US1] Create `EnvironmentBanner` component in `frontend/src/components/uat/EnvironmentBanner.tsx` (Fixed position, non-dismissible)
- [x] T009 [P] [US1] Implement `EnvironmentProvider` in `frontend/src/components/providers/EnvironmentProvider.tsx` to conditionally render Banner/Widget based on `IS_STAGING`
- [x] T010 [US1] Update `frontend/src/app/layout.tsx` to include `EnvironmentProvider`
- [x] T011 [US1] Verify Backend isolation: Ensure DB connection switches based on `APP_ENV` in `backend/app/db/session.py` (or equivalent)

## Phase 3: User Story 2 - In-App Feedback Collection

> **Goal**: Allow UAT testers to report issues directly from the interface.

**Independent Test Criteria**: Clicking "Report Issue" in Staging submits data to `uat_feedback` table; Button is invisible in Production.

- [x] T012 Add `test_system.py` integration test for Feedback API (Test-First)
- [x] T013 [P] [US2] Create Pydantic models for Feedback in `backend/app/schemas/feedback.py` (Create/Response)
- [x] T014 [P] [US2] Implement SQLAlchemy model for `UATFeedback` in `backend/app/models/feedback.py`
- [x] T015 [US2] Implement Feedback API endpoints (`POST /system/feedback`) in `backend/app/api/v1/endpoints/system.py`
- [x] T016 Create unit tests for `FeedbackWidget` in `frontend/src/components/uat/__tests__/FeedbackWidget.test.tsx` (Test-First)
- [x] T017 [P] [US2] Create `FeedbackWidget` component in `frontend/src/components/uat/FeedbackWidget.tsx` (Floating button + Dialog)
- [x] T018 [US2] Integrate `FeedbackWidget` with `POST /api/v1/system/feedback` using fetch/axios
- [x] T019 [US2] Create Admin View: `AdminFeedbackList` page in `frontend/src/app/(admin)/admin/feedback/page.tsx` (Staging only route)
- [x] T020 [US2] Implement `GET /api/v1/admin/feedback` endpoint for the Admin View

## Phase 4: User Story 3 - Demo Data Seeding

> **Goal**: Provide a "Reset" button for UAT testing.

**Independent Test Criteria**: Running `python -m scripts.seed_staging` wipes the DB and creates exactly 3 manuscripts and 1 overdue task.

- [x] T021 [P] [US3] Create `backend/scripts/seed_staging.py` skeleton with `truncate_all_tables` RPC call
- [x] T022 [US3] Implement `create_test_users` function in seed script (using Supabase Admin API)
- [x] T023 [US3] Implement `seed_manuscripts` function to generate the 3 specific scenarios (Pending, Overdue, Unpaid)
- [x] T024 [US3] Verify seed script idempotency (Run twice, ensure clean state)

## Phase 5: User Story 4 - UAT Playbook

> **Goal**: Document how to test the system for non-technical users.

- [x] T025 [US4] Create `docs/UAT_SCENARIOS.md` with "Scenario A: Academic Misconduct" and "Scenario B: Finance Approval"
- [x] T026 [US4] Add "How to Report Bugs" section to Playbook referencing the new Widget

## Final Phase: Polish & Cross-Cutting

- [x] T027 Ensure `EnvironmentProvider` uses `dynamic` import for Widget to enable tree-shaking in Production

## Dependencies

1. **Setup (Phase 1)** must complete before **Foundational (Phase 2)**
2. **Foundational (Phase 2)** must complete before **Feedback (Phase 3)** (Widget needs Provider)
3. **Setup (Phase 1)** must complete before **Seeding (Phase 4)** (Needs DB config and RPC)
4. **Feedback (Phase 3)** and **Seeding (Phase 4)** can run in **PARALLEL**
5. **Playbook (Phase 5)** depends on all prior phases being stable

## Parallel Execution Examples

- **Backend Dev**: T012-T015 (Feedback API) AND T021-T023 (Seed Script)
- **Frontend Dev**: T007-T009, T016-T018 (UI Components)
