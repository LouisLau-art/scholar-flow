# Tasks: Production Email Service

**Input**: Design documents from `specs/025-production-email-service/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md
**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize dependencies and configuration for the Resend integration.

- [x] T001 Update `backend/requirements.txt` with `resend`, `tenacity`, `itsdangerous`
- [x] T002 Update `backend/.env.example` with `RESEND_API_KEY` and `EMAIL_SENDER`
- [x] T003 Update `backend/app/core/config.py` to load new email configuration

---

## Phase 2: Foundational (Core Email Engine)

**Purpose**: Implement the robust, asynchronous `EmailService` that powers all user stories. This explicitly implements the architecture required for **User Story 4 (Resilient Error Handling)**.

**⚠️ CRITICAL**: Must complete before US1, US2, or US3.

- [x] T004 Create `EmailLog` model in `backend/app/models/email_log.py`
- [x] T005 Create Supabase migration for `email_logs` table in `supabase/migrations/20260203000000_create_email_logs.sql`
- [x] T006 [P] Implement `EmailService` class with Resend SDK and Jinja2 loader in `backend/app/core/mail.py`
- [x] T007 Implement `send_email_background` method using `FastAPI.BackgroundTasks` and `tenacity` retry logic in `backend/app/core/mail.py`
- [x] T008 [P] Implement `create_token` and `verify_token` methods using `itsdangerous` in `backend/app/core/mail.py`
- [x] T009 Create integration test for async email sending and error handling in `backend/tests/integration/test_email_service_core.py`

**Checkpoint**: Core service is ready. Retries and logging (US4) are verified.

---

## Phase 3: User Story 1 - Reviewer Invitation (Priority: P1)

**Goal**: Send secure, tokenized invitation links to reviewers.

**Independent Test**: Trigger an invitation and verify the recipient receives a valid link that expires in 7 days.

### Implementation for User Story 1

- [x] T010 [P] [US1] Create `reviewer_invite.html` Jinja2 template in `backend/app/core/templates/reviewer_invite.html`
- [x] T011 [US1] Update `backend/app/api/v1/endpoints/reviews.py` (or assignments logic) to trigger background email on reviewer assignment
- [x] T012 [US1] Create or update `verify_invitation` endpoint to consume tokens in `backend/app/api/v1/endpoints/reviews.py`
- [x] T013 [US1] Verify `GET /review/accept` flow works with valid/expired tokens

**Checkpoint**: Reviewers can be invited via real emails.

---

## Phase 4: User Story 2 - Author Status Notifications (Priority: P1)

**Goal**: Notify authors of decision outcomes (Accept/Reject/Revise).

**Independent Test**: Change manuscript status and verify author receives correct HTML email.

### Implementation for User Story 2

- [x] T014 [P] [US2] Create `status_update.html` Jinja2 template in `backend/app/core/templates/status_update.html`
- [x] T015 [US2] Update `backend/app/services/editorial_service.py` (decision logic) to trigger background email on status transition

**Checkpoint**: Authors receive decision notifications.

---

## Phase 5: User Story 3 - Financial Invoice Delivery (Priority: P2)

**Goal**: deliver invoices to authors of accepted papers.

**Independent Test**: Generate an invoice and verify email delivery with payment details.

### Implementation for User Story 3

- [x] T016 [P] [US3] Create `invoice.html` Jinja2 template in `backend/app/core/templates/invoice.html`
- [x] T017 [US3] Update `backend/app/services/invoice_generator.py` (or service) to trigger background email on invoice creation

**Checkpoint**: Invoices are delivered via email.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T018 Update `docs/quickstart.md` or similar to include email testing instructions
- [x] T019 Ensure all new code has proper type hints and docstrings
- [x] T020 Verify `email_logs` are populating correctly in Supabase

---

## Dependencies & Execution Order

1.  **Phase 1 & 2** (Setup & Foundational) are **BLOCKING**. They must be done first.
2.  **Phase 3, 4, 5** (User Stories) can theoretically run in parallel after Phase 2, but P1 stories (US1, US2) should be prioritized over P2 (US3).

### Parallel Opportunities
- T006 (Service Impl) and T008 (Token Impl) can be done in parallel.
- T010, T014, T016 (Templates) can be created in parallel by a frontend/design-focused dev.
- T011, T015, T017 (Service wiring) can be done in parallel once T007 is ready.

## Implementation Strategy

1.  **Foundation**: Build the `EmailService` harness first. Verify it logs to DB and handles Resend errors without crashing.
2.  **MVP (US1)**: Enable reviewer invitations. This is the most critical "external loop" feature.
3.  **Expansion (US2)**: Enable author notifications.
4.  **Completion (US3)**: Enable finance notifications.
