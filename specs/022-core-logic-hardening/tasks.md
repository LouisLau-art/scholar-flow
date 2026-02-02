---
description: "Task list for Core Logic Hardening"
---

# Tasks: Core Logic Hardening (Financial Gate & Reviewer Privacy)

**Input**: Design documents from `/specs/022-core-logic-hardening/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/openapi.yaml, research.md

**Tests**: Included as per Constitution "Test-First" requirement.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database schema updates and project preparation.

- [X] T001 Create migration for `review_reports` (add confidential fields) in `supabase/migrations/20260202000000_add_dual_comments.sql`
- [X] T002 [P] Verify `invoices` table structure in `supabase/migrations/` (or create if missing)

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Apply schema changes.

**⚠️ CRITICAL**: Must complete before user stories.

- [X] T003 Apply database migrations locally using `supabase db push` (or equivalent script)
- [X] T004 Update backend Pydantic models for `ReviewReport` in `backend/app/models/reviews.py`
- [X] T005 Update backend Pydantic models for `Invoice` in `backend/app/models/invoices.py` (if not exists)

**Checkpoint**: Database schema and backend models are ready.

---

## Phase 3: User Story 1 - Reviewer Submits Dual-Channel Feedback (Priority: P1)

**Goal**: Enable reviewers to send confidential comments/attachments to editors, hidden from authors.

**Independent Test**: Submit a review with confidential data; verify Author cannot see it via API.

### Tests for User Story 1 ⚠️

- [X] T006 [P] [US1] Create integration test for dual-channel submission in `backend/tests/integration/test_reviews_dual_channel.py`
- [X] T007 [P] [US1] Create privacy test (Author view) in `backend/tests/integration/test_reviews_privacy.py`

### Implementation for User Story 1

- [X] T008 [US1] Update `submit_review` service logic to handle confidential fields in `backend/app/api/v1/reviews.py`
- [X] T009 [US1] Update `get_review` endpoint to filter confidential fields for Authors in `backend/app/api/v1/reviews.py`
- [X] T010 [US1] Update Frontend Review Form to add "Confidential Comments" and "Attachment" fields in `frontend/src/app/review/[token]/page.tsx` (or relevant component)
- [X] T011 [US1] Update Frontend Review View (Author) to ensure UI handles missing confidential fields gracefully in `frontend/src/app/dashboard/author/manuscripts/[id]/page.tsx`

**Checkpoint**: Reviewer flow is updated and privacy is enforced.

---

## Phase 4: User Story 2 - Editor Sets APC and Faces Financial Gate (Priority: P1)

**Goal**: Enforce payment before publication and allow APC confirmation.

**Independent Test**: Accept manuscript -> Set APC -> Try Publish (Fail) -> Pay -> Try Publish (Success).

### Tests for User Story 2 ⚠️

- [X] T012 [P] [US2] Create integration test for Financial Gate (403 check) in `backend/tests/integration/test_financial_gate.py`
- [X] T013 [P] [US2] Create integration test for APC confirmation flow in `backend/tests/integration/test_editor_apc.py`

### Implementation for User Story 2

- [X] T014 [US2] Update `submit_final_decision` to accept and persist `apc_amount` in `backend/app/api/v1/editor.py`
- [X] T015 [US2] Implement Financial Gate check in `publish_manuscript` (add `# CRITICAL: PAYMENT GATE CHECK`) in `backend/app/api/v1/editor.py`
- [X] T016 [US2] Update Editor Dashboard "Accept" modal to include APC input in `frontend/src/components/editor/DecisionModal.tsx`
- [X] T017 [US2] Update Editor Dashboard "Publish" button to check invoice status and disable if unpaid in `frontend/src/app/dashboard/editor/page.tsx`

**Checkpoint**: Financial Gate is active and APC workflow is complete.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and cleanup.

- [X] T018 [P] Update API documentation (OpenAPI/Swagger) with new fields and 403 response
- [X] T019 Verify `quickstart.md` test scenarios manually
- [X] T020 Ensure code coverage meets Constitution requirements (>80% Backend)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Phase 1. Blocks Phase 3 & 4.
- **User Stories (Phase 3 & 4)**: Independent of each other (can run in parallel if multiple devs).
- **Polish (Phase 5)**: Depends on completion of stories.

### User Story Dependencies

- **US1 (Reviewer)**: Independent.
- **US2 (Financial Gate)**: Independent.

### Implementation Strategy

1. **Foundational**: Get the DB schema right first.
2. **US2 (Security)**: Prioritize Financial Gate as it fixes a "major security vulnerability".
3. **US1 (Privacy)**: Implement immediately after or in parallel.
4. **Validation**: Run new integration tests.

## Parallel Example: User Story 2

```bash
# Launch tests
Task: "Create integration test for Financial Gate..."
Task: "Create integration test for APC confirmation..."

# Launch Backend Implementation
Task: "Update submit_final_decision..."
Task: "Implement Financial Gate check..."
```
