# Tasks: Refine Portal Home and Navigation

**Input**: Design documents from `specs/034-portal-refinement/`
**Prerequisites**: plan.md, spec.md, data-model.md, openapi.yaml
**Organization**: Tasks are grouped by user story to ensure independent implementation and testability.

## Phase 1: Setup

**Purpose**: Initialize static configuration and portal components structure.

- [x] T001 Create site metadata configuration in `frontend/src/config/site-config.ts` (Title, ISSN, IF placeholder)
- [x] T002 Scaffold portal components structure in `frontend/src/components/portal/`

---

## Phase 2: User Story 1 - Academic Identity Banner (Priority: P1)

**Goal**: Implement a professional homepage banner.

**Independent Test**: Navigate to `/` and verify the banner displays correct journal info and a working "Submit" button.

- [x] T003 [US1] Implement `HomeBanner` component with responsive Tailwind styling in `frontend/src/components/portal/HomeBanner.tsx`
- [x] T004 [US1] Update root homepage to include the `HomeBanner` in `frontend/src/app/page.tsx`
- [x] T005 [US1] Ensure the "Submit Manuscript" button correctly redirects to `/submit` in `frontend/src/components/portal/HomeBanner.tsx`

---

## Phase 3: User Story 3 - Latest Articles Showcase (Priority: P2)

**Goal**: Display published articles on the homepage.

**Independent Test**: Create a published manuscript and verify it appears in the list; verify non-published ones are hidden.

- [x] T006 [US3] Implement `GET /api/v1/articles/latest` endpoint (strict `status='published'` filter) in `backend/app/api/v1/portal.py`
- [x] T007 [US3] Implement portal API client for fetching articles in `frontend/src/services/portal.ts`
- [x] T008 [US3] Create `ArticleList` and `ArticleCard` components in `frontend/src/components/portal/ArticleList.tsx`
- [x] T009 [US3] Integrate `ArticleList` into the homepage in `frontend/src/app/page.tsx`
- [x] T010 [US3] Add unit tests for the portal API ensuring it only returns published manuscripts in `backend/tests/unit/test_portal_api.py`

---

## Phase 4: User Story 2 - Standardized Footer (Priority: P2)

**Goal**: Implement a site-wide academic footer.

**Independent Test**: Verify the footer is visible on Home, Submit, and Dashboard pages.

- [x] T011 [US2] Implement `SiteFooter` component with ISSN and legal links in `frontend/src/components/portal/SiteFooter.tsx`
- [x] T012 [US2] Include `SiteFooter` in the root layout in `frontend/src/app/layout.tsx`

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T013 Update Navbar to ensure clear "Login" vs "Dashboard" vs "Submit" distinction in `frontend/src/components/layout/Navbar.tsx`
- [x] T014 Implement basic E2E test for the homepage visual flow in `frontend/tests/e2e/homepage.spec.ts`

---

## Dependencies & Execution Order

1. **Phase 1** is a prerequisite for US1 and US2.
2. **Phase 3** (Backend) must be started early to support `ArticleList` integration.
3. **Phase 2 & 4** are primarily UI-focused and can be done in parallel.

## Parallel Execution Examples

- **Backend/Frontend**: Phase 3 Backend (T006) and Phase 2 Frontend (T003) can be developed in parallel.
- **Component UI**: `HomeBanner` and `SiteFooter` can be developed independently.

## Implementation Strategy

1. **Brand First**: Implement the Banner and Footer to establish the site's academic identity immediately.
2. **Data Integration**: Hook up the published articles query once the API is ready.
3. **Responsive Check**: Ensure the new components handle mobile viewports gracefully.