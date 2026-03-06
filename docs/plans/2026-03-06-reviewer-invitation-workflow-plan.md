# Reviewer Invitation Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure reviewer management so “select reviewer”, “send invitation”, “reviewer responds”, and “review submitted” become distinct states, while preserving magic-link review access and adding proper reviewer history and manuscript detail visibility.

**Architecture:** Reuse the existing reviewer invitation, magic-link, and reviewer summary foundations, but split the current over-coupled assignment path into explicit workflow stages. The backend should treat reviewer outreach as a state machine, not as a side effect of reviewer selection. The frontend should move the heavy reviewer management UI into the manuscript detail main column and keep the right rail as a lightweight summary only.

**Tech Stack:** FastAPI, Supabase Auth, Supabase Postgres, Supabase email/auth links, Next.js App Router, React, shadcn/ui, reviewer magic-link flow.

---

## Priority

Execute this plan **after** the `Next 16` stabilization plan. This workflow touches multiple reviewer routes and detail pages, and should not be implemented on top of an unstable framework baseline.

## Product Rules

- Selecting a reviewer must **not** imply invitation was sent.
- Invitation email must include a secure magic link.
- Reviewer can preview manuscript metadata and PDF before responding.
- Decline reasons must be structured.
- First-time reviewers should **not** receive a plaintext password by email.
- If a reviewer needs a full account, use an activation / set-password flow after acceptance.
- Manuscript detail must show all reviewers, including declined ones.
- Reviewer workspace/session access must **not** auto-mark acceptance.
- Re-inviting after decline must generate a fresh valid invitation attempt, not keep reusing a dead link.
- UI "Email status" must distinguish `queued`, `sent`, `failed`, and editorial invite state; do not pretend queued means delivered.

## Current Audit Snapshot

The current implementation has multiple workflow breaks that justify a full restructuring rather than patching one endpoint:

1. **Selection already behaves like invitation**: `reviews_handlers_assignment_assign.py` writes assignment state, `invited_at`, and even advances the manuscript too early.
2. **Acceptance is bypassed**: reviewer workspace/session code auto-accepts assignments, which means reviewers can enter the review flow without explicitly clicking `Accept`.
3. **Decline -> re-invite is inconsistent**: declined reviewers cannot accept again, but the system can still send more invite emails to the stale assignment path.
4. **Status semantics are mixed**: the same logical milestone is represented as both `pending` and `accepted` in different code paths.
5. **Email evidence is too weak**: current flows mostly prove "queued" or "timestamp written", not "email actually delivered".
6. **First-time account creation is split across multiple flows**: reviewer library creation, admin invite, and actual reviewer invitation do not share one onboarding policy.
7. **Default password policy leaks into reviewer onboarding**: this conflicts with the target of secure, invite-driven onboarding.
8. **Manuscript detail aggregation is lossy**: some submitted status mapping is keyed only by `reviewer_id`, which can misrepresent multiple invitation rounds.
9. **E2E coverage is not proving the real funnel**: several reviewer tests are still mocked and do not validate the true invitation-to-response path.

## Official Guidance Anchors (Context7)

The relevant official `Supabase Auth` guidance supports this plan direction:

- `auth.admin.invite_user_by_email(...)` is the server-side admin invite path when the goal is to send an invite link.
- `auth.admin.generate_link(...)` supports `invite`, `magiclink`, and `recovery` style links and can be used to drive controlled onboarding flows.
- `signInWithOtp(...)` / magic-link style flows are the official passwordless entry pattern.
- None of these flows require sending a plaintext password by email, and that should remain prohibited in the reviewer journey.

### Task 1: Freeze the Target State Machine in Code and Docs

**Files:**
- Create: `docs/plans/2026-03-06-reviewer-invitation-state-machine-notes.md`
- Modify: `backend/app/schemas/review.py`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/helpers.ts`

**Step 1: Define canonical states**

Recommended canonical model:

- `invite_status`
  - `selected`
  - `invited`
  - `opened`
  - `accepted`
  - `declined`
- `review_status`
  - `not_started`
  - `in_progress`
  - `submitted`

If one-column compatibility is required for MVP, explicitly document the mapping layer and mark it as temporary debt.

**Step 2: Add a failing test plan for current wrong behavior**

Examples:
- selecting a reviewer should not set `invited_at`
- selecting a reviewer should not move manuscript to `under_review`
- only `Send Invitation` should mark `invited`
- opening workspace should not auto-mark `accepted`
- decline + re-invite should create a fresh valid invitation path

**Step 3: Commit**

```bash
git add docs/plans/2026-03-06-reviewer-invitation-state-machine-notes.md backend/app/schemas/review.py frontend/src/app/'(admin)'/editor/manuscript/[id]/helpers.ts
git commit -m "docs(reviewer): freeze reviewer invitation state machine"
```

### Task 2: Stop Treating Selection as Invitation

**Files:**
- Modify: `backend/app/api/v1/reviews_handlers_assignment_assign.py`
- Modify: `backend/app/api/v1/reviews.py`
- Modify: `frontend/src/components/ReviewerAssignModal.tsx`
- Modify: `frontend/src/components/editor/reviewer-assign-modal/*`

**Step 1: Write the failing backend tests**

Required assertions:
- selecting reviewer creates a draft/selected record only
- `invited_at` remains `null`
- manuscript status does not jump to `under_review`

**Step 2: Introduce a dedicated “selection” path**

Recommended behavior:
- AE picks reviewers
- backend persists them as `selected`
- no email side effect
- no `invited_at`
- no manuscript stage transition

**Step 3: Add a separate send-invitation action**

Only this action should:
- generate or reuse assignment magic link
- send template email
- set `invited_at`
- transition reviewer invite state to `invited`
- create an email-delivery evidence row with at least `queued/sent/failed`

**Step 4: Define re-invite semantics before coding**

Recommended rule:
- if a reviewer previously declined, a new invitation must create a fresh invitation attempt (`invite_round` or a new assignment/versioned token)
- stale declined links stay terminal and auditable
- the manuscript detail page should show both the decline and the later re-invite attempt

**Step 5: Run tests**

```bash
cd backend && pytest -o addopts= tests/unit -k reviewer
```

**Step 6: Commit**

```bash
git add backend/app/api/v1/reviews_handlers_assignment_assign.py backend/app/api/v1/reviews.py frontend/src/components/ReviewerAssignModal.tsx frontend/src/components/editor/reviewer-assign-modal
git commit -m "feat(reviewer): split reviewer selection from invitation send"
```

### Task 3: Keep Manuscript Stage Transitions Honest

**Files:**
- Modify: `backend/app/api/v1/reviews_handlers_assignment_assign.py`
- Modify: `backend/app/services/editor_service_precheck_workspace_decisions.py`
- Test: reviewer assignment and manuscript transition tests

**Step 1: Write failing transition tests**

Rules:
- `selected` reviewers do not push manuscript into `under_review`
- manuscript enters `under_review` only after at least one effective invitation / acceptance policy condition is met, according to the final product decision

**Step 2: Implement the chosen gate**

Recommended default:
- move manuscript to `under_review` on first actual invitation send

Alternative if stricter:
- move on first reviewer acceptance

Pick one and use it consistently in API + UI copy.

**Step 3: Commit**

```bash
git add backend/app/api/v1/reviews_handlers_assignment_assign.py backend/app/services/editor_service_precheck_workspace_decisions.py
git commit -m "fix(workflow): align manuscript under-review transition with reviewer invitation state"
```

### Task 4: Remove Auto-Accept Side Effects from Workspace and Session Entry

**Files:**
- Modify: `backend/app/services/reviewer_workspace_service.py`
- Modify: `backend/app/api/v1/reviews_handlers_assignment_session.py`
- Modify: any tests covering reviewer workspace/session bootstrap

**Step 1: Write failing tests**

Required assertions:
- opening workspace must not mutate `invite_status`
- creating a reviewer session must not silently mark `accepted`
- only the explicit accept action may transition `invite_status` to `accepted`

**Step 2: Move acceptance into one explicit command**

Recommended rule:
- invite page `Accept` is the single acceptance entrypoint
- workspace/session endpoints validate `accepted` state but do not create it
- if a reviewer is still only `invited/opened`, workspace access should redirect back to the invite decision surface

**Step 3: Commit**

```bash
git add backend/app/services/reviewer_workspace_service.py backend/app/api/v1/reviews_handlers_assignment_session.py
git commit -m "fix(reviewer): remove implicit acceptance from workspace bootstrap"
```

### Task 5: Upgrade the Invite Page into a Real Decision Surface

**Files:**
- Modify: `frontend/src/app/(public)/review/invite/page.tsx`
- Modify: `frontend/src/app/(public)/review/invite/accept-form.tsx`
- Modify: `frontend/src/app/(public)/review/invite/decline-form.tsx`
- Modify: reviewer invite API if extra fields are needed

**Step 1: Add PDF preview**

The invite page should show:
- manuscript title
- abstract
- journal
- due date
- embedded PDF preview or viewer launch

**Step 2: Keep structured decline reasons**

Current reasons already exist:
- out of scope
- conflict of interest
- too busy
- insufficient expertise
- other

Keep them, but align labels to final editorial wording.

**Step 3: Add open tracking**

Opening the invite page should mark state/evidence as `opened`.

**Step 4: Use invite acceptance as the state gate**

After `Accept`:
- the current assignment can be opened immediately via magic-link/session continuation
- if the reviewer lacks a full account, queue the separate activation/set-password follow-up

**Step 5: Commit**

```bash
git add frontend/src/app/'(public)'/review/invite backend/app/api/v1/reviews.py backend/app/services/reviewer_service.py
git commit -m "feat(reviewer): turn invite page into manuscript preview and response surface"
```

### Task 6: Introduce First-Time Reviewer Activation Instead of Plaintext Password Email

**Files:**
- Modify: `backend/app/services/user_management.py`
- Modify: `backend/app/services/reviewer_service.py`
- Modify: `backend/app/api/v1/reviews.py`
- Modify: email template config / template docs

**Step 1: Write failing service tests**

Cases:
- existing reviewer account: no activation email needed
- accepted invite with no auth account: create dormant/auth user and send activation or set-password email
- no plaintext password sent in email body

**Step 2: Implement onboarding rule**

Recommended flow:
- reviewer uses magic link for the current assignment immediately
- if no auth account exists, use a trusted-server Supabase Auth flow such as `generate_link(...)` or `invite_user_by_email(...)` to send a follow-up `set password` / activation path after acceptance
- if auth account already exists, do nothing

**Step 3: Add audit/logging**

Record:
- account created
- activation email queued
- activation email failed

**Step 4: Commit**

```bash
git add backend/app/services/user_management.py backend/app/services/reviewer_service.py backend/app/api/v1/reviews.py
git commit -m "feat(reviewer): add reviewer activation flow without plaintext passwords"
```

### Task 7: Expand Reviewer Management in Manuscript Detail Main Column

**Files:**
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/detail-sections.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/types.ts`

**Step 1: Move heavy reviewer management UI to the left/main column**

The main reviewer table should include:
- reviewer name
- email
- invite status
- review status
- invited at
- opened at
- accepted at
- declined at
- decline reason
- due date
- last reminded at
- template picker
- send email button
- history button

**Step 2: Keep the right rail minimal**

Right-side snapshot only:
- selected count
- invited count
- accepted count
- declined count
- submitted count

**Step 3: Preserve all reviewers, including declined**

No filtering-out of declined rows from the detail page.

**Step 4: Fix assignment-level aggregation**

The detail page must key submitted/reported state by invitation or assignment record, not only by `reviewer_id`, so multiple rounds remain distinguishable.

**Step 5: Commit**

```bash
git add frontend/src/app/'(admin)'/editor/manuscript/[id]/page.tsx frontend/src/app/'(admin)'/editor/manuscript/[id]/detail-sections.tsx frontend/src/app/'(admin)'/editor/manuscript/[id]/types.ts
git commit -m "feat(editor): move reviewer management into manuscript detail main column"
```

### Task 8: Enrich Reviewer History

**Files:**
- Modify: `backend/app/api/v1/reviews.py`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- Modify: any reviewer history modal/component used there

**Step 1: Expand returned fields**

History should show:
- manuscript id/title
- who added the reviewer
- added via
- current/terminal status
- added on
- email action history
- prior review summary/rating if available
- manuscript status at the time

**Step 2: Add UI parity with the desired table**

The modal/table should feel closer to the MDPI-style reference:
- tabular
- sortable chronologically
- explicit invitation history

**Step 3: Commit**

```bash
git add backend/app/api/v1/reviews.py frontend/src/app/'(admin)'/editor/manuscript/[id]/page.tsx
git commit -m "feat(reviewer): expand reviewer history for editorial decision-making"
```

### Task 9: Add End-to-End Coverage for the Full Reviewer Funnel

**Files:**
- Create/Modify: `frontend/tests/e2e/*`
- Create/Modify: `backend/tests/*`

**Step 1: Cover the happy path**

Flow:
- AE selects reviewers
- selected list appears
- AE sends invitation
- reviewer opens invite page
- reviewer previews PDF
- reviewer accepts
- reviewer enters workspace
- reviewer submits review

**Step 2: Cover decline path**

Flow:
- reviewer opens invite
- reviewer declines with structured reason
- manuscript detail shows declined reviewer and reason

**Step 3: Cover first-time onboarding**

Flow:
- new reviewer accepts
- activation email is queued
- no plaintext password is mailed

**Step 4: Cover regression edges**

Flow:
- reviewer opens invite but does not accept -> workspace remains blocked
- reviewer declines -> later re-invite generates a fresh valid path
- manuscript detail shows multiple invitation rounds for the same reviewer correctly

**Step 5: Commit**

```bash
git add frontend/tests/e2e backend/tests
git commit -m "test(reviewer): cover reviewer invitation funnel end to end"
```

Plan complete and saved to `docs/plans/2026-03-06-reviewer-invitation-workflow-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?

## References

- Supabase Auth docs via Context7:
  - `auth.admin.invite_user_by_email(...)`
  - `auth.admin.generate_link(...)`
  - passwordless / magic-link / OTP sign-in flows
