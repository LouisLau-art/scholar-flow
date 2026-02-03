# Tasks: Post-Acceptance Pipeline

**Feature**: `024-post-acceptance-pipeline`
**Status**: Ready for Implementation

## Phase 1: Setup
- [X] T001 Install `reportlab` dependency in `backend/requirements.txt`
- [X] T002 Create Supabase SQL migration in `supabase/migrations/` for `manuscripts` columns (`final_pdf_path`, `doi`, `published_at`) — see `supabase/migrations/20260203143000_post_acceptance_pipeline.sql` (invoices/owner_id already exist)

## Phase 2: Foundational
- [X] T003 [US1] Use Supabase PostgREST tables directly (no SQLAlchemy in this repo)
- [X] T004 [US1] Manuscripts fields handled via Supabase migration + dict payloads (`final_pdf_path/doi/published_at`)
- [X] T005 [US1] Invoice payloads returned as JSON dicts (no dedicated Pydantic schema needed for MVP)

## Phase 3: User Story 1 - Financial Gate & Payment (P1)
**Goal**: Authors get invoices on acceptance, Admins confirm payment.
**Independent Test**: Approve manuscript -> Verify Invoice DB entry -> Mark Paid -> Verify Status.

- [ ] T006 [P] [US1] Implement `InvoiceService.generate_pdf` using `reportlab` in `backend/app/services/invoice_service.py`
- [X] T006 [P] [US1] Implement invoice PDF generator using `reportlab` — see `backend/app/core/invoice_generator.py`
- [X] T007 [US1] Invoice creation already happens on `POST /api/v1/editor/decision` (accept) via upsert
- [X] T008 [US1] Invoice hook already wired in accept decision (idempotent on `manuscript_id`)
- [X] T009 [P] [US1] Create API endpoint `GET /api/v1/manuscripts/{id}/invoice` — see `backend/app/api/v1/manuscripts.py`
- [X] T010 [P] [US1] Create API endpoint `POST /api/v1/invoices/{id}/pay` — see `backend/app/api/v1/invoices.py`
- [X] T011 [US1] Add "Download Invoice" button in Author tab — see `frontend/src/app/dashboard/page.tsx`
- [X] T012 [US1] Editor can mark invoice paid in Pipeline — see `frontend/src/components/EditorPipeline.tsx`
- [X] T013 [US1] Integration tests added — see `backend/tests/integration/test_post_acceptance_pipeline.py`

## Phase 4: User Story 2 - Production File Management (P2)
**Goal**: Editors upload final PDF.
**Independent Test**: Upload PDF -> Verify `final_pdf_path` in DB.

- [ ] T014 [US2] Implement `ProductionService.upload_final_pdf` (handling storage) in `backend/app/services/production_service.py`
- [X] T014 [US2] Implement production PDF upload to Supabase Storage — see `backend/app/api/v1/manuscripts.py`
- [X] T015 [P] [US2] Create API endpoint `POST /api/v1/manuscripts/{id}/production-file` — see `backend/app/api/v1/manuscripts.py`
- [X] T016 [US2] Add upload UI component — see `frontend/src/components/ProductionUploadDialog.tsx`
- [X] T017 [US2] Integrate upload UI into Editor pipeline cards — see `frontend/src/components/EditorPipeline.tsx`

## Phase 5: User Story 3 - One-Click Publication & DOI (P1)
**Goal**: Publish article after gates are met.
**Independent Test**: Click Publish -> Verify Status `published`, DOI set, Email sent.

- [ ] T018 [US3] Implement `PublicationService.publish` (validate gates, mint DOI, update status) in `backend/app/services/publication_service.py`
- [X] T018 [US3] Publish service implemented (Payment + Production gates, status update) — see `backend/app/services/post_acceptance_service.py`
- [X] T019 [US3] DOI mock generator implemented — see `backend/app/core/doi_generator.py`
- [X] T020 [P] [US3] Create API endpoint `POST /api/v1/manuscripts/{id}/publish` — see `backend/app/api/v1/manuscripts.py` (also keeps `/api/v1/editor/publish`)
- [X] T021 [US3] Publish button already exists and now enforces both gates — see `frontend/src/components/EditorPipeline.tsx`
- [X] T022 [US3] Publication notification email + in-app notification — see `backend/app/api/v1/editor.py` and `backend/app/templates/emails/published.html`
- [X] T023 [US3] Integration tests cover gates + upload + publish — see `backend/tests/integration/test_post_acceptance_pipeline.py`

## Phase 6: User Story 4 - Public Access & Discovery (P3)
**Goal**: Readers see published articles.
**Independent Test**: Publish -> Check Homepage.

- [ ] T024 [P] [US4] Update `ManuscriptService.get_latest_articles` (or equivalent) to filter by `status='published'` and sort by `published_at`
- [X] T024 [P] [US4] Add endpoint for latest published articles (published-only, published_at desc) — see `backend/app/api/v1/manuscripts.py`
- [X] T025 [US4] Add Frontend "Latest Articles" component — see `frontend/src/components/home/LatestArticles.tsx`

## Phase 7: Polish & Cross-Cutting
- [ ] T026 [P] Add E2E test for the full "Accept to Publish" pipeline in `frontend/tests/e2e/specs/publish_flow.spec.ts`
- [X] T026 [P] Add mocked E2E publish flow test — see `frontend/tests/e2e/specs/publish_flow.spec.ts`
- [X] T027 Ensure Next build typecheck passes (`npm run build`)
- [X] T028 Run full backend test suite (`pytest -o addopts= -q`)

## Dependencies

1.  Phase 1 & 2 (Setup/Foundational) MUST be done first.
2.  Phase 3 (Financial) and Phase 4 (Production) can be done in parallel (independent of each other).
3.  Phase 5 (Publication) DEPENDS ON Phase 3 AND Phase 4.
4.  Phase 6 (Public Access) DEPENDS ON Phase 5.

## Implementation Strategy
- **MVP**: Focus on T001-T010, T014-T015, T018-T020 to get the API working.
- **UI Integration**: Then bind the UI components (T011, T012, T016, T021).
- **Public View**: Finally, expose to readers (T024-T025).
