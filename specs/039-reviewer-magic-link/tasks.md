---
description: "Task list for Feature 039: Reviewer Magic Link"
---

# Tasks: Reviewer Invitation & Magic Link

**Input**: Design documents from `/specs/039-reviewer-magic-link/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/magic-link.yaml
**Tests**: Unit/E2E tests included as per Constitution "Test-First" principle.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable
- **[US#]**: User Story ID

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Install `pyjwt` dependency in `backend/requirements.txt` and rebuild container
- [x] T002 [P] Create email template `backend/app/core/templates/invitation.html`

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure for JWT and Auth

- [x] T003 Implement JWT utilities (encode/decode) in `backend/app/core/security.py`
- [x] T004 [P] Create `MagicLinkPayload` schema in `backend/app/schemas/token.py`
- [x] T005 Create backend unit tests for JWT logic in `backend/tests/unit/test_magic_link.py`

## Phase 3: User Story 1 - Editor invites Reviewer (Priority: P1)

**Goal**: Editor can send an invite email with a magic link.
**Independent Test**: Editor clicks invite -> Email sent with valid JWT.

### Tests for US1

- [x] T006 [P] [US1] Create integration test for invite endpoint in `backend/tests/integration/test_editor_invite.py`

### Implementation for US1

- [x] T007 [P] [US1] Implement magic-link JWT generator in `backend/app/core/security.py` (HS256)
- [x] T008 [US1] Update `POST /api/v1/reviews/assign` in `backend/app/api/v1/reviews.py` to send magic link (`/review/invite?token=...`)
- [x] T009 [US1] Verify email sending logic includes magic link (integration test parses email HTML and decodes JWT)

## Phase 4: User Story 2 - Reviewer Access (Priority: P1)

**Goal**: Reviewer clicks link -> Auto-logged in as guest.
**Independent Test**: Access `?token=...` in incognito -> Session created -> Redirected to manuscript.

### Tests for US2

- [x] T010 [P] [US2] Create E2E test for magic link flow in `frontend/tests/e2e/specs/magic_link.spec.ts`

### Implementation for US2

- [x] T011 [P] [US2] Implement `POST /api/v1/auth/magic-link/verify` in `backend/app/api/v1/auth.py`
- [x] T012 [P] [US2] Add helper `authService.verifyMagicLink()` in `frontend/src/services/auth.ts`
- [x] T013 [US2] Implement Middleware logic in `frontend/src/middleware.ts` to intercept `/review/invite?token=...`, set httpOnly cookie, redirect to assignment page
- [x] T014 [US2] Create reviewer pages in `frontend/src/app/(public)/review/*` (loading/error/assignment workspace)

## Phase 5: User Story 3 - Security & Expiration (Priority: P2)

**Goal**: Expired/Tampered tokens are rejected.
**Independent Test**: Modify token char -> Access denied.

### Tests for US3

- [x] T015 [P] [US3] Add unit tests for expired/invalid tokens in `backend/tests/unit/test_magic_link.py`

### Implementation for US3

- [x] T016 [US3] Add revocation/status checks in `backend/app/api/v1/auth.py` and cookie-auth endpoints in `backend/app/api/v1/reviews.py`
- [x] T017 [US3] Implement error UI for invalid tokens in `frontend/src/app/(public)/review/error/page.tsx`

## Phase 6: Polish

- [x] T018 [P] Update OpenAPI via FastAPI (routes are self-documented; no manual `openapi.json` needed)
- [x] T019 Run full test suite (`./scripts/run-all-tests.sh`)

---

## Dependencies & Execution Order

1. **Setup & Foundational (T001-T005)**: Must complete first.
2. **US1 (Editor Invite)**: Depends on JWT utils.
3. **US2 (Reviewer Access)**: Depends on US1 (to get a valid token for testing).
4. **US3 (Security)**: Can implement backend checks in parallel, but UI depends on US2.

## Implementation Strategy

1. **MVP**: Complete Phase 1-4. This delivers the core "Invite -> Click -> Login" loop.
2. **Hardening**: Phase 5 adds critical security checks (revocation, expiry UI).
