# Tasks: Automated Invoice PDF (Feature 026)

**Input**: Design documents from `specs/026-automated-invoice-pdf/`  
**Prerequisites**: `specs/026-automated-invoice-pdf/plan.md`, `specs/026-automated-invoice-pdf/spec.md`, `specs/026-automated-invoice-pdf/research.md`, `specs/026-automated-invoice-pdf/data-model.md`, `specs/026-automated-invoice-pdf/contracts/openapi.yaml`

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Add WeasyPrint dependency and system libs to backend Docker images (`backend/Dockerfile`, root `Dockerfile`)
- [x] T002 Define invoice configuration (payment instructions, signed URL TTL) in `backend/app/core/config.py`
- [x] T003 [P] Add invoice HTML template (Jinja2) in `backend/app/core/templates/invoice_pdf.html`

---

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T004 Add DB migration for invoice PDF fields on `public.invoices` (`supabase/migrations/20260204120000_invoice_pdf_fields.sql`: add `invoice_number`, `pdf_path`, `pdf_generated_at`, `pdf_error`)
- [x] T005 Add Storage bucket `invoices` (private) via migration (`supabase/migrations/20260204121000_invoices_bucket.sql`)
- [x] T006 Implement Storage helper for upload + signed URL in `backend/app/services/storage_service.py`
- [x] T007 Implement invoice number + PDF generation service in `backend/app/services/invoice_pdf_service.py`
- [x] T008 Add lightweight observability logs for generation outcomes in `backend/app/services/invoice_pdf_service.py`

**Checkpoint**: Foundation ready — invoice PDF can be generated and stored by backend code.

---

## Phase 3: User Story 1 - Automatic Invoice Generation (Priority: P1) 🎯 MVP

**Goal**: Accepted manuscript automatically gets a stored invoice PDF linked from the invoice record.

**Independent Test**: Accept a manuscript (status becomes `approved`) and confirm `invoices.pdf_path` is set and the Storage object exists.

- [x] T009 [US1] Trigger PDF generation on accept via BackgroundTasks (`backend/app/api/v1/editor.py`)
- [x] T010 [US1] Ensure generation is idempotent (re-accept overwrites PDF without duplicating invoice record) (`backend/app/services/invoice_pdf_service.py`)
- [x] T011 [US1] Persist `invoice_number`, `pdf_path`, `pdf_generated_at`, `pdf_error` on `public.invoices` (`backend/app/services/invoice_pdf_service.py`)

- [x] T012 [P] [US1] Unit test: invoice number format + no payment status mutation (`backend/tests/unit/test_invoice_pdf_unit.py`)
- [x] T013 [US1] Integration test: accept manuscript generates invoice PDF fields (`backend/tests/integration/test_invoice_pdf_generation.py`)

---

## Phase 4: User Story 2 - Author Invoice Download (Priority: P1)

**Goal**: Author can download their invoice PDF from the app.

**Independent Test**: Login as the manuscript author and download invoice PDF via signed URL.

- [x] T014 [US2] Update existing endpoint `GET /api/v1/manuscripts/{id}/invoice` to serve the stored PDF (generate+persist if missing) (`backend/app/api/v1/manuscripts.py`)
- [x] T015 [US2] Add endpoint `GET /api/v1/invoices/{invoice_id}/pdf-signed` (`backend/app/api/v1/invoices.py`)
- [x] T016 [US2] Enforce access control for invoice download (manuscript author OR editor/admin) (`backend/app/api/v1/manuscripts.py`, `backend/app/api/v1/invoices.py`)
- [x] T017 [P] [US2] Integration test: author can download; other author gets 403; editor/admin can download (`backend/tests/integration/test_invoice_pdf_download.py`)

- [x] T018 [US2] Frontend: ensure “Download Invoice” uses `/api/v1/manuscripts/{id}/invoice` and shows friendly errors (`frontend/src/app/dashboard/page.tsx`)

---

## Phase 5: User Story 3 - Admin/Editor Regeneration (Priority: P2)

**Goal**: Internal user can regenerate invoice PDF without changing payment status.

**Independent Test**: Adjust invoice amount, regenerate, and verify PDF regenerated while `invoices.status/confirmed_at` remains unchanged.

- [x] T019 [US3] Add endpoint `POST /api/v1/invoices/{invoice_id}/pdf/regenerate` (`backend/app/api/v1/invoices.py`)
- [x] T020 [US3] Ensure regeneration overwrites PDF and updates `pdf_generated_at/pdf_error` only (must not change `status/confirmed_at`) (`backend/app/services/invoice_pdf_service.py`)
- [x] T021 [P] [US3] Integration test: editor/admin regeneration succeeds; non-internal 403 (`backend/tests/integration/test_invoice_pdf_regenerate.py`)
- [x] T022 [US3] Frontend: add “Regenerate Invoice PDF” action for editor/admin (optional MVP UI) (`frontend/src/components/EditorPipeline.tsx`)

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T023 Normalize error messages for generation/download failures (user-friendly + debuggable) (`backend/app/api/v1/invoices.py`, `backend/app/services/invoice_pdf_service.py`)
- [x] T024 Update `specs/026-automated-invoice-pdf/quickstart.md` with the final env var names and migration filenames
- [x] T025 Re-run agent context sync to keep `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` consistent (if new env vars are introduced) (`.specify/scripts/bash/update-agent-context.sh`)
- [x] T026 Validate critical tests: `cd backend && pytest -q` (or focused suite) and confirm no coverage regressions

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 blocks all user stories.
- US1 (Phase 3) is MVP; US2 depends on US1 having a generated PDF; US3 depends on US1 service.
