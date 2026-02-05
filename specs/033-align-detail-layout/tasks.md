# Tasks: Align Manuscript Detail Page Layout

**Input**: Design documents from `specs/033-align-detail-layout/`
**Prerequisites**: plan.md, spec.md, data-model.md, openapi.yaml
**Organization**: Tasks are grouped by user story to ensure independent implementation and testability.

## Phase 1: Setup

**Purpose**: Initialize the component structure for the layout refactor.

- [x] T001 Scaffold the new component files (`ManuscriptHeader`, `FileSectionCard`, `InvoiceInfoPanel`, `UploadReviewFile`) in `frontend/src/components/editor/`

---

## Phase 2: User Story 1 - Header Information Alignment (Priority: P1)

**Goal**: Implement the consolidated metadata header.

**Independent Test**: View a manuscript page and verify the header contains Title, Authors, Funding, APC Status, Owner, and Editor in a grid layout.

- [x] T002 [US1] Implement `ManuscriptHeader` component using CSS Grid (Tailwind) to display Title, Authors, and Funding in `frontend/src/components/editor/ManuscriptHeader.tsx`
- [x] T003 [US1] Add "Internal Owner" and "Assigned Editor" fields to the `ManuscriptHeader` metadata grid in `frontend/src/components/editor/ManuscriptHeader.tsx`
- [x] T004 [US1] Integrate `ManuscriptHeader` into the main page layout in `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`

---

## Phase 3: User Story 2 - Structured File Sections (Priority: P1)

**Goal**: Split file display into three distinct areas and add peer review upload.

**Independent Test**: Verify 3 separate cards for Cover, Original, Review. Verify "Upload" button works for Review section.

- [x] T005 [US2] Implement generic `FileSectionCard` component in `frontend/src/components/editor/FileSectionCard.tsx`
- [x] T006 [US2] Create helper function to filter files by type (Cover, Manuscript, Review) in `frontend/src/app/(admin)/editor/manuscript/[id]/utils.ts` (ensuring DB schema supports `review_attachment` enum value)
- [x] T007 [US2] Implement `UploadReviewFile` component (file input + API call) in `frontend/src/components/editor/UploadReviewFile.tsx`
- [x] T008 [US2] Implement `POST /api/v1/editor/manuscripts/{id}/files/review-attachment` endpoint in `backend/app/api/v1/editor.py` (Enforcing RLS/Permission check: Editor-only)
- [x] T008b [US2] Implement integration test verifying Authors cannot access/upload review files in `backend/tests/integration/test_file_permissions.py`
- [x] T009 [US2] Integrate the 3 `FileSectionCard` instances into the main page grid in `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`

---

## Phase 4: User Story 3 - Bottom Invoice Management (Priority: P2)

**Goal**: Move invoice management to the footer area.

**Independent Test**: Scroll to bottom, see Invoice table, click Edit to open modal.

- [x] T010 [US3] Implement `InvoiceInfoPanel` component (Table + Edit Button) in `frontend/src/components/editor/InvoiceInfoPanel.tsx`
- [x] T011 [US3] Integrate `InvoiceInfoPanel` at the bottom of the main page layout in `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T012 Add skeleton loading states for Header, Files, and Invoice components in `frontend/src/app/(admin)/editor/manuscript/[id]/loading.tsx` (or inline skeletons)
- [x] T013 Verify visual layout against PDF requirements using Playwright screenshot comparison (manual or automated) in `frontend/tests/e2e/specs/manuscript_layout.spec.ts`

---

## Dependencies & Execution Order

1. **Phase 1** scaffolds the files.
2. **Phase 2, 3, 4** can be developed roughly in parallel as they touch distinct components, but integration (T004, T009, T011) depends on `page.tsx` structure.
3. **T008 (Backend)** blocks T007's functionality but not UI.

## Parallel Execution Examples

- **Frontend Components**: T002 (Header), T005 (FileCard), T010 (InvoicePanel) can be built simultaneously by different agents/devs.
- **Backend**: T008 can be built while frontend components are being laid out.

## Implementation Strategy

1. **Scaffold & Layout**: Set up the main `grid` in `page.tsx` first.
2. **Componentize**: Build each section (Header, Files, Invoice) as pure components.
3. **Wire Data**: Connect the components to the data source.
