---
description: "Tasks for Dynamic Portal CMS implementation"
---

# Tasks: Dynamic Portal CMS

**Input**: Design documents from `/specs/013-portal-cms`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup (Project Initialization)

- [x] T001 [P] Install frontend dependencies: `@tiptap/react`, `@tiptap/starter-kit`, `@tiptap/extension-image`, `isomorphic-dompurify` in `frontend/package.json`
- [x] T002 [P] Install backend dependencies: `bleach` in `backend/requirements.txt`
- [x] T003 [P] Create `cms_pages` and `cms_menu_items` tables migration with RLS in `supabase/migrations/`
- [x] T004 [P] Create `cms-assets` public storage bucket in Supabase via migration or setup script

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T005 [P] Implement `CMSPage` and `CMSMenuItem` Pydantic models in `backend/app/models/cms.py`
- [x] T006 [P] Implement `CMSService` for DB operations (CRUD for pages and menus) in `backend/app/services/cms_service.py`
- [x] T007 [P] Create `cms` API router and register in `backend/main.py`
- [x] T008 [P] Implement backend XSS sanitization using `bleach` in `backend/app/services/cms_service.py`

## Phase 3: User Story 1 - Editor Page Management (Priority: P1)

**Goal**: Enable Editors to manage static pages via a rich text editor.
**Independent Test**: Create and publish a page in the admin UI, verify it exists in the database.

- [ ] T009 [P] [US1] Implement `POST /api/v1/cms/pages` and `PATCH /api/v1/cms/pages/{slug}` with Audit Trail logging (API-006) in `backend/app/api/v1/cms.py`
- [ ] T010 [P] [US1] Implement "Reserved Slugs" validation and duplicate slug check in `backend/app/api/v1/cms.py`
- [ ] T011 [P] [US1] Implement image upload proxy endpoint `POST /api/v1/cms/upload` in `backend/app/api/v1/cms.py`
- [ ] T012 [US1] Create `TiptapEditor` component with image upload support in `frontend/src/components/cms/TiptapEditor.tsx`
- [x] T009 [P] [US1] Implement `POST /api/v1/cms/pages` and `PATCH /api/v1/cms/pages/{slug}` with Audit Trail logging (API-006) in `backend/app/api/v1/cms.py`
- [x] T010 [P] [US1] Implement "Reserved Slugs" validation and duplicate slug check in `backend/app/api/v1/cms.py`
- [x] T011 [P] [US1] Implement image upload proxy endpoint `POST /api/v1/cms/upload` in `backend/app/api/v1/cms.py`
- [x] T012 [US1] Create `TiptapEditor` component with image upload support in `frontend/src/components/cms/TiptapEditor.tsx`
- [x] T013 [US1] Create Page Management UI (List/Edit) in `frontend/src/components/cms/CmsPagesPanel.tsx` (入口：`Dashboard → Editor → Website`)
- [x] T014 [P] [US1] Add unit tests for CMS API endpoints (including slug conflict tests) in `backend/tests/unit/test_cms_api.py`

## Phase 4: User Story 2 - Dynamic Page Rendering (Priority: P1)

**Goal**: Publicly render dynamic pages with SSR and SEO support.
**Independent Test**: Visit `/journal/about` and verify content matches the published database entry.

- [x] T015 [P] [US2] Implement `GET /api/v1/cms/pages/{slug}` with 404 for drafts in `backend/app/api/v1/cms.py`
- [x] T016 [US2] Create dynamic route `frontend/src/app/journal/[slug]/page.tsx` using SSR and DOMPurify for sanitization
- [x] T017 [US2] Configure Incremental Static Regeneration (ISR) with `revalidate: 60` in `frontend/src/app/journal/[slug]/page.tsx`
- [x] T018 [US2] Create branded 404 page for missing CMS slugs in `frontend/src/app/not-found.tsx`

## Phase 5: User Story 3 - Menu & Navigation Management (Priority: P2)

**Goal**: Allow editors to manage Navbar and Footer links.
**Independent Test**: Update menu via admin UI and verify changes on the public homepage.

- [x] T019 [P] [US3] Implement `GET /api/v1/cms/menu` and `PUT /api/v1/cms/menu` in `backend/app/api/v1/cms.py`
- [x] T020 [US3] Create Menu Builder UI (MVP: flat list) in `frontend/src/components/cms/CmsMenuPanel.tsx` (入口：`Dashboard → Editor → Website`)
- [x] T021 [US3] Update `SiteHeader` and add `SiteFooter` to fetch data from CMS menu API in `frontend/src/components/layout/`

## Phase 6: User Story 4 - Preset Content Initialization (Priority: P3)

**Goal**: Auto-initialize standard pages.
**Independent Test**: Fresh DB deployment should contain placeholder content for standard pages.

- [x] T022 [P] [US4] Implement initialization script/service to seed `cms_pages` with standard entries in `backend/app/core/init_cms.py`
- [x] T023 [US4] Trigger CMS initialization on application startup in `backend/main.py`

## Final Phase: Polish & Cross-Cutting Concerns

- [ ] T024 [P] Add breadcrumbs and navigation between CMS management sections
- [ ] T025 [P] Add loading skeletons for CMS pages
- [ ] T026 Run full E2E flow test using Playwright in `frontend/tests/e2e/cms.spec.ts`

## Dependencies

- Phase 2 (Foundational) blocks all US implementation.
- US1 (Page Management) and US2 (Page Rendering) are closely linked but US1 can be tested via API before UI.
- US3 (Menu) depends on US1 if linking to internal pages.

## Parallel Execution

**User Story 1**:
- Backend API (T009, T010) and Frontend Editor (T011) can be developed in parallel.

**User Story 2**:
- API Fetching (T014) and Page Rendering (T015) can be developed in parallel once contract is stable.
