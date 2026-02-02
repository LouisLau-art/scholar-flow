---
description: "Tasks for Notification Center implementation"
---

# Tasks: Notification Center

**Input**: Design documents from `/specs/011-notification-center`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 [P] Install `jinja2` dependency in `backend/requirements.txt`
- [x] T002 [P] Create email templates directory `backend/app/templates/emails/`
- [x] T003 [P] Create email templates for submission, review invite, and chase in `backend/app/templates/emails/`
- [x] T004 [P] Create SMTP configuration in `backend/app/core/config.py` (reading from env vars)
- [x] T005 [P] Create notification icons/assets in `frontend/src/components/icons/` (Bell icon)

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T006 Create `notifications` table migration in `supabase/migrations/`
- [x] T007 Add `last_reminded_at` column to `review_assignments` table in migration
- [x] T008 [P] Implement `EmailService` class using `smtplib` in `backend/app/core/mail.py`
- [x] T009 [P] Implement `NotificationService` for DB operations in `backend/app/services/notification_service.py`
- [x] T010 [P] Define Pydantic models for Notifications in `backend/app/models/notification.py`
- [x] T011 [P] Update `SupabaseClient` helper in `frontend/src/lib/supabase.ts` to support Realtime subscriptions

## Phase 3: User Story 1 - Multi-channel Status Notifications (Priority: P1)

**Goal**: Enable email and in-app notifications for manuscript status changes.
**Independent Test**: Trigger a status change and verify email/notification creation.

- [x] T012 [P] [US1] Create test for email sending in `backend/tests/unit/test_mail.py`
- [x] T013 [P] [US1] Create test for notification creation in `backend/tests/integration/test_notifications.py` (Verify DB insert triggers Realtime event)
- [x] T014 [US1] Integrate `EmailService` into `ManuscriptService` for submission acknowledgement
- [x] T015 [US1] Integrate `NotificationService` into `ManuscriptService` for submission alert
- [x] T016 [US1] Integrate `EmailService` into `ReviewService` for invitation emails (with Token generation and Expiry check)
- [x] T017 [US1] Integrate `NotificationService` into `ReviewService` for invitation alerts

## Phase 4: User Story 2 - In-App Notification Center (Priority: P2)

**Goal**: Frontend UI for viewing and managing notifications.
**Independent Test**: Click bell icon, view list, mark as read.

- [x] T018 [P] [US2] Create `GET /api/v1/notifications` endpoint in `backend/app/api/v1/notifications.py`
- [x] T019 [P] [US2] Create `PATCH /api/v1/notifications/{id}/read` endpoint in `backend/app/api/v1/notifications.py`
- [x] T020 [P] [US2] Create `NotificationList` component in `frontend/src/components/notifications/NotificationList.tsx`
- [x] T021 [P] [US2] Create `NotificationItem` component in `frontend/src/components/notifications/NotificationItem.tsx`
- [x] T022 [US2] Integrate `BellIcon` with Realtime subscription in `frontend/src/components/layout/SiteHeader.tsx`
- [x] T023 [US2] Implement "Mark as Read" logic in frontend

## Phase 5: User Story 3 - Automated Chasing (Priority: P3)

**Goal**: Background job to chase overdue reviews.
**Independent Test**: Trigger cron endpoint and verify email sent/idempotency.

- [x] T024 [P] [US3] Create `POST /api/v1/internal/cron/chase-reviews` endpoint in `backend/app/api/v1/internal.py`
- [x] T025 [P] [US3] Implement `ChaseScheduler` logic in `backend/app/core/scheduler.py` (idempotency check)
- [x] T026 [P] [US3] Create test for chase scheduler idempotency in `backend/tests/integration/test_scheduler.py`
- [x] T027 [US3] Configure `X-Admin-Key` security dependency in `backend/app/core/security.py`

## Final Phase: Polish & Cross-Cutting Concerns

- [x] T028 [P] Add detailed logging for SMTP failures in `backend/app/core/mail.py`
- [x] T029 [P] Create empty state UI for Notification List
- [x] T030 [P] Verify academic English phrasing in all templates
- [x] T031 Run full regression test suite

## Dependencies

- Phase 2 blocks Phase 3, 4, 5
- Phase 3, 4, 5 can run in parallel (mostly independent backend/frontend tasks)

## Parallel Execution

**User Story 1**:
- T012 (Email Test) and T013 (Notification Test) can run in parallel.
- T014/T015 (Manuscript) and T016/T017 (Review) can run in parallel.

**User Story 2**:
- Backend endpoints (T018, T019) and Frontend components (T020, T021) can run in parallel.

**User Story 3**:
- Scheduler logic (T025) and Endpoint definition (T024) can run in parallel.
