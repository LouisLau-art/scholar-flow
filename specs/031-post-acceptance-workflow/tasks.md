# Tasks: Enhance Post-Acceptance Workflow

**Input**: Design documents from `specs/031-post-acceptance-workflow/`
**Prerequisites**: plan.md, spec.md, data-model.md, openapi.yaml
**Organization**: Tasks are grouped by user story to ensure independent implementation and testability.

## Phase 1: Setup

**Purpose**: Initialize the backend service layer for handling production transitions and gates.

- [x] T001 Create `ProductionService` with state transition and reversion logic in `backend/app/services/production_service.py`
- [x] T002 Implement unit tests for `ProductionService` verifying state paths and reversions in `backend/tests/unit/test_production_service.py`

---

## Phase 2: User Story 2 - Publication with Gates (Priority: P1)

**Goal**: Enforce Payment and Production gates before publication.

**Independent Test**: Attempt to publish a manuscript with pending payment and verify rejection. Mark paid and verify success.

- [x] T003 [US2] Implement Payment Gate check logic (Invoice status/amount) in `backend/app/services/production_service.py`
- [x] T004 [US2] Implement Production Gate check logic (Final PDF + Env Var) in `backend/app/services/production_service.py`
- [x] T005 [US2] Implement `POST /api/v1/editor/manuscripts/{id}/production/advance` and `revert` endpoints in `backend/app/api/v1/editor.py`
- [x] T006 [US2] Implement integration tests for production gates (verify PRODUCTION_GATE_ENABLED=true/false scenarios and mocked invoice states) in `backend/tests/integration/test_production_gates.py`

---

## Phase 3: User Story 1 - Sequential Status Progression (Priority: P1)

**Goal**: Provide UI controls for the editor to manage the workflow.

**Independent Test**: Verify "Start Layout", "Start English Editing", etc. buttons appear correctly based on current status and successfully update the backend.

- [x] T007 [US1] Create `ProductionStatusCard` component showing current status and action buttons (handling error states) in `frontend/src/components/editor/ProductionStatusCard.tsx`
- [x] T008 [US1] Integrate `ProductionStatusCard` into the Manuscript Details sidebar in `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- [x] T009 [US1] Implement optimistic UI updates for status transitions (with immediate rollback on gate failure) in `frontend/src/components/editor/ProductionStatusCard.tsx`

---

## Phase 4: Polish & Cross-Cutting Concerns

- [x] T010 Add audit log verification to integration tests in `backend/tests/integration/test_production_gates.py`
- [x] T011 Ensure error messages from failed gates (e.g., "Payment Pending") are displayed clearly in `frontend/src/components/editor/ProductionStatusCard.tsx`
- [x] T012 Final E2E test verifying the full flow from Accepted to Published in `frontend/tests/e2e/production_flow.spec.ts`

---

## Dependencies & Execution Order

1. **Phase 1** establishes the core logic.
2. **Phase 2** adds the critical business rules (gates) and API.
3. **Phase 3** exposes functionality to the user.

## Parallel Execution Examples

- **Backend/Frontend**: Phase 2 (API & Gates) and Phase 3 (UI Component) can be built in parallel once the API contract is agreed.

## Implementation Strategy

1. **Gate First**: Focus on the backend validation logic (Phase 2) as it's the highest risk area (revenue assurance).
2. **UI Integration**: Once the API is robust, wire up the frontend component.
