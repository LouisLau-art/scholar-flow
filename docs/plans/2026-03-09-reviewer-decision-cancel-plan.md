# Reviewer Decision / Cancel Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve reviewer comment usability immediately, remove the fake score field, then add a formal reviewer-cancel and AE early-decision workflow for manuscripts in `under_review`.

**Architecture:** Split delivery into two phases. Phase 1 is a low-risk UI/data cleanup that only touches reviewer comment inputs and score handling. Phase 2 adds explicit `cancel` semantics, AE-controlled review-stage exit, and stricter `first decision` / `final decision` rules without reusing the old `unassign/delete` path.

**Tech Stack:** Next.js App Router, React 19, shadcn/ui, FastAPI, Pydantic v2, Supabase Postgres/Auth/Storage, reviewer magic-link flow.

---

## Product Rules

- Reviewer comment boxes must support long-form writing comfortably.
- `score` must no longer be written or shown.
- AE may leave `under_review` after at least one valid submitted review.
- `first decision` allows only:
  - `major_revision`
  - `minor_revision`
  - `reject`
- `accept` is allowed only in `final decision`.
- When leaving `under_review`:
  - `selected / invited / opened` reviewers are auto-cancelled
  - `accepted but not submitted` reviewers must be explicitly handled by AE
- `cancelled` reviewers must immediately lose access to invite/workspace/attachments/submit.

## Phase Split

- **Phase 1:** reviewer form usability + remove score
- **Phase 2:** AE early decision + reviewer cancel lifecycle

## Task 1: Phase 1 Reviewer Comment UX

**Files:**
- Modify: `frontend/src/app/(reviewer)/reviewer/workspace/[id]/action-panel.tsx`
- Modify: `frontend/src/app/(public)/review/assignment/[assignmentId]/page.tsx`
- Test: `frontend/src/app/(reviewer)/reviewer/workspace/[id]/page.test.tsx`
- Test: `frontend/tests/e2e/specs/reviewer_workspace_layout.spec.ts`

**Step 1: Write the failing tests**

Add assertions for:

- `Comment to Authors` renders with a larger textarea height expectation
- `Private note to Editor` renders with a larger textarea height expectation
- reviewer review page still submits normally after the UI change

**Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && bun run test:run 'src/app/(reviewer)/reviewer/workspace/[id]/page.test.tsx'
```

Expected:
- FAIL because current textarea props/classes still match the small layout

**Step 3: Write minimal implementation**

Update:

- `comments_for_author`
  - increase `rows`
  - add a stronger `min-h-*`
  - keep `resize-y`
- `confidential_comments_to_editor`
  - increase `rows`
  - add a smaller but still larger `min-h-*`
  - keep `resize-y`

Also mirror the same reviewer-facing form sizing in:

- `frontend/src/app/(public)/review/assignment/[assignmentId]/page.tsx`

**Step 4: Run tests to verify it passes**

Run:

```bash
cd frontend && bun run test:run 'src/app/(reviewer)/reviewer/workspace/[id]/page.test.tsx' 'tests/e2e/specs/reviewer_workspace_layout.spec.ts'
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add 'frontend/src/app/(reviewer)/reviewer/workspace/[id]/action-panel.tsx' 'frontend/src/app/(public)/review/assignment/[assignmentId]/page.tsx' 'frontend/src/app/(reviewer)/reviewer/workspace/[id]/page.test.tsx' 'frontend/tests/e2e/specs/reviewer_workspace_layout.spec.ts'
git commit -m "feat(reviewer): enlarge review comment inputs"
```

## Task 2: Phase 1 Remove Reviewer Score

**Files:**
- Modify: `backend/app/services/reviewer_workspace_service.py`
- Modify: `backend/app/services/decision_service_letters.py`
- Modify: `backend/app/models/reviews.py`
- Modify: `backend/app/schemas/review.py`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/detail-sections.tsx`
- Modify: `frontend/src/components/DecisionPanel.tsx`
- Test: `backend/tests/unit/test_reviewer_service.py`
- Test: `frontend/src/app/(admin)/editor/manuscript/[id]/__tests__/helpers.reviewer-summary.test.ts`

**Step 1: Write the failing tests**

Add assertions for:

- reviewer submission no longer writes `score`
- reviewer feedback summary no longer renders `Score 5`
- decision aggregation still works with reports lacking `score`

**Step 2: Run test to verify it fails**

Run:

```bash
cd backend && pytest -q -o addopts= tests/unit/test_reviewer_service.py
cd frontend && bun run test:run 'src/app/(admin)/editor/manuscript/[id]/__tests__/helpers.reviewer-summary.test.ts'
```

Expected:
- FAIL because current backend still writes `score: 5`
- FAIL because current frontend still renders `Score`

**Step 3: Write minimal implementation**

- Remove `score: 5` from `reviewer_workspace_service.py`
- Stop depending on `score` in reviewer summary rendering
- Keep schema compatibility where needed, but make `score` non-essential and non-displayed

**Step 4: Run tests to verify it passes**

Run:

```bash
cd backend && pytest -q -o addopts= tests/unit/test_reviewer_service.py
cd frontend && bun run test:run 'src/app/(admin)/editor/manuscript/[id]/__tests__/helpers.reviewer-summary.test.ts'
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add backend/app/services/reviewer_workspace_service.py backend/app/services/decision_service_letters.py backend/app/models/reviews.py backend/app/schemas/review.py 'frontend/src/app/(admin)/editor/manuscript/[id]/detail-sections.tsx' frontend/src/components/DecisionPanel.tsx backend/tests/unit/test_reviewer_service.py 'frontend/src/app/(admin)/editor/manuscript/[id]/__tests__/helpers.reviewer-summary.test.ts'
git commit -m "refactor(reviewer): remove placeholder review score"
```

## Task 3: Add Cancel Audit Fields

**Files:**
- Create: `supabase/migrations/20260309xxxxxx_review_assignment_cancel_audit.sql`
- Modify: `backend/app/api/v1/editor_detail_main.py`
- Modify: `backend/app/api/v1/reviews.py`
- Modify: `backend/app/services/reviewer_service.py`
- Test: `backend/tests/integration/test_editor_timeline.py`

**Step 1: Write the failing tests**

Cover:

- cancelled assignment returns `cancelled_at`
- cancelled assignment returns `cancelled_by`
- cancelled assignment returns `cancel_reason`
- old schema fallback still works before migration

**Step 2: Run test to verify it fails**

Run:

```bash
cd backend && pytest -q -o addopts= tests/integration/test_editor_timeline.py -k cancelled
```

Expected:
- FAIL because cancel audit fields do not exist yet

**Step 3: Write minimal implementation**

Migration should add to `review_assignments`:

- `cancelled_at timestamptz null`
- `cancelled_by uuid null`
- `cancel_reason text null`
- `cancel_via text null`

Add FK indexes for:

- `cancelled_by`

Use a `CHECK` for `cancel_via` values:

- `auto_stage_exit`
- `editor_manual_cancel`
- `post_acceptance_cleanup`
- `legacy`

**Step 4: Run tests to verify it passes**

Run:

```bash
cd backend && pytest -q -o addopts= tests/integration/test_editor_timeline.py -k cancelled
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add supabase/migrations/20260309xxxxxx_review_assignment_cancel_audit.sql backend/app/api/v1/editor_detail_main.py backend/app/api/v1/reviews.py backend/app/services/reviewer_service.py backend/tests/integration/test_editor_timeline.py
git commit -m "feat(reviewer): add cancel audit metadata"
```

## Task 4: Add Explicit Cancel Endpoint

**Files:**
- Modify: `backend/app/api/v1/reviews.py`
- Modify: `backend/app/api/v1/reviews_handlers_assignment_manage.py`
- Modify: `backend/app/api/v1/reviews_handlers_assignment_session.py`
- Modify: `backend/app/api/v1/auth.py`
- Test: `backend/tests/integration/test_reviews_authz.py`
- Test: `backend/tests/integration/test_editor_invite.py`

**Step 1: Write the failing tests**

Required behaviors:

- `POST /api/v1/reviews/assignments/{id}/cancel` cancels `invited/opened/accepted`
- `cancelled` assignment can no longer open invite/workspace
- `unassign` remains limited to shortlist-style early removal

**Step 2: Run test to verify it fails**

Run:

```bash
cd backend && pytest -q -o addopts= tests/integration/test_reviews_authz.py tests/integration/test_editor_invite.py -k cancel
```

Expected:
- FAIL because explicit cancel endpoint does not exist or does not preserve audit

**Step 3: Write minimal implementation**

Add endpoint:

- `POST /api/v1/reviews/assignments/{assignment_id}/cancel`

Request payload:

- `reason: str`
- `via: str`
- `send_email: bool = true`

Behavior:

- update assignment to `cancelled`
- set cancel audit fields
- preserve history
- reject future magic-link/session access

**Step 4: Run tests to verify it passes**

Run:

```bash
cd backend && pytest -q -o addopts= tests/integration/test_reviews_authz.py tests/integration/test_editor_invite.py -k cancel
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add backend/app/api/v1/reviews.py backend/app/api/v1/reviews_handlers_assignment_manage.py backend/app/api/v1/reviews_handlers_assignment_session.py backend/app/api/v1/auth.py backend/tests/integration/test_reviews_authz.py backend/tests/integration/test_editor_invite.py
git commit -m "feat(reviewer): add explicit cancel endpoint"
```

## Task 5: Add Review Stage Exit API for AE

**Files:**
- Modify: `backend/app/models/manuscript.py`
- Modify: `backend/app/services/decision_service.py`
- Modify: `backend/app/services/decision_service_transitions.py`
- Create: `backend/app/api/v1/editor_review_stage_exit.py`
- Test: `backend/tests/unit/test_decision_service_access.py`
- Test: `backend/tests/integration/test_decision_workspace.py`

**Step 1: Write the failing tests**

Cover:

- AE may leave `under_review` once at least one review is submitted
- `selected/invited/opened` reviewers are auto-cancelled
- `accepted but not submitted` reviewers must be explicitly resolved
- unresolved accepted reviewers block transition with `422`

**Step 2: Run test to verify it fails**

Run:

```bash
cd backend && pytest -q -o addopts= tests/unit/test_decision_service_access.py tests/integration/test_decision_workspace.py -k under_review
```

Expected:
- FAIL because current implementation still depends on “all assignments completed”

**Step 3: Write minimal implementation**

Add endpoint:

- `POST /api/v1/editor/manuscripts/{id}/review-stage-exit`

Payload should include:

- `target_stage`
- `decision_path`
- `auto_cancel_assignment_ids`
- `accepted_assignment_resolutions`

Rules:

- require at least one submitted review
- auto-cancel `selected/invited/opened`
- require AE to choose for each `accepted` unresolved assignment:
  - `continue_waiting`
  - `cancel_after_contact`

**Step 4: Run tests to verify it passes**

Run:

```bash
cd backend && pytest -q -o addopts= tests/unit/test_decision_service_access.py tests/integration/test_decision_workspace.py -k under_review
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add backend/app/models/manuscript.py backend/app/services/decision_service.py backend/app/services/decision_service_transitions.py backend/app/api/v1/editor_review_stage_exit.py backend/tests/unit/test_decision_service_access.py backend/tests/integration/test_decision_workspace.py
git commit -m "feat(decision): add AE review-stage exit workflow"
```

## Task 6: Restrict First vs Final Decision Options

**Files:**
- Modify: `frontend/src/components/editor/decision/DecisionEditor.tsx`
- Modify: `frontend/src/components/DecisionPanel.tsx`
- Modify: `backend/app/services/decision_service.py`
- Modify: `backend/app/services/decision_service_transitions.py`
- Test: `frontend/tests/e2e/specs/decision_workspace.visual.spec.ts`
- Test: `backend/tests/unit/test_decision_service_access.py`

**Step 1: Write the failing tests**

Required assertions:

- first decision UI does not offer `accept`
- final decision still allows `accept`
- backend rejects `accept` when `decision_stage = first`

**Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && bun run test:run tests/e2e/specs/decision_workspace.visual.spec.ts
cd backend && pytest -q -o addopts= tests/unit/test_decision_service_access.py -k first
```

Expected:
- FAIL because current UI still shows `Accept`

**Step 3: Write minimal implementation**

- split selectable options by decision stage
- enforce same rule in backend service layer

**Step 4: Run tests to verify it passes**

Run:

```bash
cd frontend && bun run test:run tests/e2e/specs/decision_workspace.visual.spec.ts
cd backend && pytest -q -o addopts= tests/unit/test_decision_service_access.py -k first
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add frontend/src/components/editor/decision/DecisionEditor.tsx frontend/src/components/DecisionPanel.tsx backend/app/services/decision_service.py backend/app/services/decision_service_transitions.py frontend/tests/e2e/specs/decision_workspace.visual.spec.ts backend/tests/unit/test_decision_service_access.py
git commit -m "fix(decision): separate first and final decision options"
```

## Task 7: Add Reviewer Cancel UI in Manuscript Detail

**Files:**
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/detail-sections.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/helpers.ts`
- Test: `frontend/src/tests/pages/reviewer-invite-summary-card.test.tsx`
- Test: `frontend/tests/e2e/specs/reviewer_management_delivery.spec.ts`

**Step 1: Write the failing tests**

Cover:

- under-review exit panel lists `selected/invited/opened` auto-cancel reviewers
- accepted but not submitted reviewers require explicit AE resolution
- cancelled reviewers render as cancelled and lose active actions

**Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && bun run test:run src/tests/pages/reviewer-invite-summary-card.test.tsx tests/e2e/specs/reviewer_management_delivery.spec.ts
```

Expected:
- FAIL because current reviewer management UI lacks the new panel and resolution controls

**Step 3: Write minimal implementation**

Add to manuscript detail:

- a “Leave Under Review” action surface
- auto-cancel preview list
- accepted reviewer resolution controls
- final submit action wired to `review-stage-exit`

**Step 4: Run tests to verify it passes**

Run:

```bash
cd frontend && bun run test:run src/tests/pages/reviewer-invite-summary-card.test.tsx tests/e2e/specs/reviewer_management_delivery.spec.ts
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add 'frontend/src/app/(admin)/editor/manuscript/[id]/detail-sections.tsx' 'frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx' 'frontend/src/app/(admin)/editor/manuscript/[id]/helpers.ts' frontend/src/tests/pages/reviewer-invite-summary-card.test.tsx frontend/tests/e2e/specs/reviewer_management_delivery.spec.ts
git commit -m "feat(reviewer): add under-review exit and cancel handling UI"
```

## Task 8: Add Reviewer Cancellation Email Templates

**Files:**
- Modify: `backend/app/api/v1/reviews.py`
- Modify: `backend/app/core/mail.py`
- Modify: `frontend/src/app/admin/email-templates/page.tsx`
- Modify: relevant template seed/migration files
- Test: `backend/tests/integration/test_editor_invite.py`

**Step 1: Write the failing tests**

Cover:

- auto-cancel can send cancellation email
- manual cancel can send cancellation email
- history shows cancellation outreach

**Step 2: Run test to verify it fails**

Run:

```bash
cd backend && pytest -q -o addopts= tests/integration/test_editor_invite.py -k cancel
```

Expected:
- FAIL because cancellation email event/template does not exist

**Step 3: Write minimal implementation**

Add template support for:

- reviewer cancellation notice
- optional “please stop work” message for accepted reviewers

**Step 4: Run tests to verify it passes**

Run:

```bash
cd backend && pytest -q -o addopts= tests/integration/test_editor_invite.py -k cancel
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add backend/app/api/v1/reviews.py backend/app/core/mail.py frontend/src/app/admin/email-templates/page.tsx
git commit -m "feat(email): add reviewer cancellation templates"
```

## Task 9: Final Regression

**Files:**
- Test: `frontend/tests/e2e/specs/reviewer_invite_accept.spec.ts`
- Test: `frontend/tests/e2e/specs/reviewer_workspace_gate.spec.ts`
- Test: `frontend/tests/e2e/specs/reviewer_management_delivery.spec.ts`
- Test: `backend/tests/integration/test_editor_invite.py`
- Test: `backend/tests/integration/test_reviews_authz.py`
- Test: `backend/tests/integration/test_decision_workspace.py`

**Step 1: Run focused reviewer + decision regressions**

Run:

```bash
cd frontend && bun run test:e2e tests/e2e/specs/reviewer_invite_accept.spec.ts tests/e2e/specs/reviewer_workspace_gate.spec.ts tests/e2e/specs/reviewer_management_delivery.spec.ts
cd backend && pytest -q -o addopts= tests/integration/test_editor_invite.py tests/integration/test_reviews_authz.py tests/integration/test_decision_workspace.py
```

Expected:
- PASS

**Step 2: Run lint / typecheck**

Run:

```bash
cd frontend && bun run lint && bunx tsc --noEmit
cd backend && uvx ruff check . --select=E9,F63,F7,F82
```

Expected:
- PASS

**Step 3: Commit**

```bash
git add .
git commit -m "test(reviewer): cover decision exit and cancellation workflow"
```

## Notes for Implementation

- Do not reuse `DELETE /reviews/assign/{assignment_id}` as the new cancel path.
- Keep `unassign` only for shortlist-stage cleanup.
- Prefer preserving old rows and marking them `cancelled`; do not delete reviewer history.
- Preserve reviewer magic-link blocking via the existing `cancelled` checks in auth/session/workspace paths.
- Apply `@context7` guidance:
  - React textarea sizing should stay simple (`rows`, native resize, controlled input)
  - FastAPI should use explicit `HTTPException` with stable `409/422/404` semantics

## Plan Handoff

Plan complete and saved to `docs/plans/2026-03-09-reviewer-decision-cancel-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
