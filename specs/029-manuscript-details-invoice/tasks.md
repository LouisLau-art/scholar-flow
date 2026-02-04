# Tasks: Manuscript Details and Invoice Info Management

**Input**: Design documents from `specs/029-manuscript-details-invoice/`
**Prerequisites**: plan.md, spec.md, data-model.md, openapi.yaml
**Organization**: Tasks are grouped by user story to ensure independent implementation and testability.

## Phase 1: Setup

**Purpose**: Initialize backend service logic for metadata management and auditing.

- [x] T001 Implement `EditorialService.update_invoice_info` with audit logging in `backend/app/services/editorial_service.py`
- [x] T002 Implement unit tests for `update_invoice_info` and audit logging in `backend/tests/unit/test_editorial_service.py`

---

## Phase 2: Foundational (Backend API)

**Purpose**: Create endpoints for fetching manuscript details and updating invoice metadata.

- [x] T003 Implement `GET /api/v1/editor/manuscripts/{id}` endpoint in `backend/app/api/v1/editor.py` (Must return Signed URLs for private files)
- [x] T004 Implement `PUT /api/v1/editor/manuscripts/{id}/invoice-info` endpoint in `backend/app/api/v1/editor.py` (Verify Editor/Admin role permission)
- [x] T005 Create integration tests for manuscript details and invoice info endpoints in `backend/tests/integration/test_editor_api.py`
- [x] T005b [Security] Implement integration tests verifying that Authors cannot access Peer Review files or edit Invoice Metadata in `backend/tests/integration/test_editor_security.py`

---

## Phase 3: User Story 3 - High-Level Manuscript Metadata Display (Priority: P2)

**Goal**: Implement the page header with essential manuscript context.

**Independent Test**: Navigate to `/editor/manuscript/[id]` and verify the title, authors, owner, and APC status are visible in the header.

- [x] T006 [US3] Create `ManuscriptDetailsHeader` component in `frontend/src/components/editor/ManuscriptDetailsHeader.tsx`
- [x] T007 [US3] Implement dedicated manuscript details page route in `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`

---

## Phase 4: User Story 1 - Centralized Document Management (Priority: P1)

**Goal**: Organize manuscript files into structured sections.

**Independent Test**: On the details page, verify that files are grouped into Cover Letter, Original, and Peer Review sections with role-based access.

- [x] T008 [US1] Create `FileSectionGroup` component for categorizing files in `frontend/src/components/editor/FileSectionGroup.tsx`
- [x] T009 [US1] Integrate `FileSectionGroup` into the details page in `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- [x] T010 [US1] Implement role-based visibility logic for Peer Review Reports in `frontend/src/components/editor/FileSectionGroup.tsx`

---

## Phase 5: User Story 2 - Invoice Info and Metadata Editing (Priority: P1)

**Goal**: Enable editing of invoice-related metadata via a modal.

**Independent Test**: Click "Edit Invoice Info", modify fields, save, and verify data persists and displays updated values.

- [x] T011 [US2] Create `InvoiceInfoModal` component using Shadcn UI in `frontend/src/components/editor/InvoiceInfoModal.tsx`
- [x] T012 [US2] Create `InvoiceInfoSection` display component in `frontend/src/components/editor/InvoiceInfoSection.tsx`
- [x] T013 [US2] Implement metadata update logic using API client in `frontend/src/components/editor/InvoiceInfoModal.tsx`
- [x] T014 [US2] Integrate `InvoiceInfoSection` and `InvoiceInfoModal` into the details page in `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T015 Ensure precision timestamp formatting (YYYY-MM-DD HH:mm) on the details page in `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- [x] T016 Implement error handling and loading states for manuscript data fetching in `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- [x] T017 Final E2E verification of manuscript details and invoice editing flow in `frontend/tests/e2e/manuscript_details.spec.ts`

---

## Dependencies & Execution Order

1. **Phase 1 & 2** are foundational and required for all frontend features.
2. **Phase 3 (US3)** sets up the page structure.
3. **Phase 4 (US1)** and **Phase 5 (US2)** can be implemented in any order after Phase 3.

## Parallel Execution Examples

- **Backend/Frontend**: Phase 2 (Backend API) and Phase 3 (Frontend Header) can be developed in parallel if the API contract is followed.
- **Frontend Components**: `FileSectionGroup` (T008) and `InvoiceInfoModal` (T011) can be developed simultaneously.

## Implementation Strategy

1. **API First**: Ensure the backend provides all necessary data and supports updates.
2. **Skeleton UI**: Build the details page layout with the header first.
3. **Interactive Features**: Add file management and modal editing once the basic page is stable.
