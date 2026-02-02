---
description: "Task list for Owner Binding feature"
---

# Tasks: Owner Binding

**Input**: Design documents from `/specs/023-owner-binding/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md

**Organization**: Grouped by user story, with backend prerequisites first.

## Phase 1: Setup (Database Schema)

**Purpose**: Update database schema to support owner tracking.

- [ ] T001 Create migration `supabase/migrations/20260203000000_add_owner_id.sql` to add `owner_id` column to `manuscripts` table with FK to `auth.users`

## Phase 2: Foundational (Backend API)

**Purpose**: Enable reading and writing of owner information.

**Goal**: Expose owner data and enforce role validation (US2).

### Tests for User Story 2 (API)

- [ ] T002 [P] [US2] Create integration test for `PATCH /manuscripts/{id}` owner update (valid/invalid roles) in `backend/tests/integration/test_owner_binding.py`

### Implementation for User Story 2

- [ ] T003 [US2] Update `Manuscript` Pydantic models in `backend/app/models/schemas.py` (or relevant file) to include `owner_id` and `owner` details
- [ ] T004 [US2] Implement `GET /api/v1/editor/staff` endpoint in `backend/app/api/v1/editor.py` to list eligible owners (admins/editors)
- [ ] T005 [US2] Update `GET /api/v1/manuscripts/{id}` in `backend/app/api/v1/manuscripts.py` to include owner details (join user_profiles)
- [ ] T006 [US2] Update `PATCH /api/v1/manuscripts/{id}` (or create dedicated endpoint) in `backend/app/api/v1/manuscripts.py` to handle `owner_id` update with RBAC validation

**Checkpoint**: API is ready for frontend integration. Tests T002 should pass.

---

## Phase 3: User Story 1 - Bind Owner (UI) (Priority: P1)

**Goal**: Allow editors to assign an owner via the UI.

**Independent Test**: Select owner in sidebar -> verify "Owner updated" toast -> refresh -> owner persists.

### Implementation for User Story 1

- [ ] T007 [P] [US1] Create `OwnerCombobox` component in `frontend/src/components/editor/OwnerCombobox.tsx` using `GET /api/v1/editor/staff`
- [ ] T008 [US1] Integrate `OwnerCombobox` into Manuscript Detail Sidebar in `frontend/src/app/dashboard/editor/manuscripts/[id]/page.tsx` (or `Sidebar.tsx`)
- [ ] T009 [US1] Implement auto-save logic in `OwnerCombobox` calling the patch API

**Checkpoint**: Editors can assign owners.

---

## Phase 4: User Story 3 - Owner Column (List View) (Priority: P3)

**Goal**: Show owner in the manuscript list.

**Independent Test**: View list -> verify "Owner" column shows names.

### Implementation for User Story 3

- [ ] T010 [US3] Update `GET /api/v1/editor/pipeline` (or list endpoint) in `backend/app/api/v1/editor.py` to include owner name in the list payload
- [ ] T011 [US3] Update Editor Manuscript Table in `frontend/src/app/dashboard/editor/page.tsx` (or `EditorPipeline.tsx`) to add "Owner" column

**Checkpoint**: Feature complete.

---

## Phase 5: Polish

- [ ] T012 Verify E2E flow: Assign owner -> Check List -> Check Database
- [ ] T013 Update API documentation if needed

---

## Dependencies & Execution Order

1.  **T001 (DB)** must happen first.
2.  **T002-T006 (Backend)** depend on T001.
3.  **T007-T009 (Frontend Detail)** depend on Backend T004 & T006.
4.  **T010-T011 (Frontend List)** depend on T001 (and ideally T006 for data generation).

## Parallel Example: Frontend Components

```bash
# While one dev works on Backend (T003-T006):
Task: "Create OwnerCombobox component..." (T007) # Can mock the API
```