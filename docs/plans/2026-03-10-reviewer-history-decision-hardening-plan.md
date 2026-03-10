# Reviewer History / Decision Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Finish the remaining reviewer-facing editorial hardening work by improving reviewer history readability, tightening decision visibility boundaries, and adding end-to-end coverage for AE review-stage exit.

**Architecture:** Keep the reviewer lifecycle model already in production. Do not introduce a new event table yet. Instead, harden existing `review_assignments + email_logs + decision stage` surfaces so editors can read history accurately and cannot bypass the intended `under_review -> exit review stage -> decision/final decision` flow.

**Tech Stack:** Next.js 16 App Router, React 19, shadcn/ui, FastAPI, Pydantic v2, Supabase Postgres/Auth, Playwright, Vitest, pytest.

---

## Product Rules

- reviewer history must remain readable to editors without exposing raw enum/token values
- reminder-related history should explain **who** triggered it and **what** happened
- decision workspace entry must stay aligned with manuscript stage rules
- AE review-stage-exit must remain the only legitimate bridge from `under_review` into decision queues
- all changes require regression tests before merge

### Task 1: Expand Reviewer History Readability

**Files:**
- Modify: `backend/app/api/v1/reviews.py`
- Modify: `backend/app/api/v1/editor_detail_main.py`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/helpers.ts`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/types.ts`
- Test: `backend/tests/integration/test_editor_timeline.py`
- Test: `frontend/src/tests/pages/reviewer-invite-summary-card.test.tsx`

**Step 1: Write the failing tests**

Add assertions for:

- reviewer history returns human-meaningful reminder/cancel metadata without exposing raw tokens
- manuscript detail history modal renders reminder/cancel text in editor-readable language

**Step 2: Run test to verify it fails**

Run:

```bash
cd backend && pytest -q -o addopts= tests/integration/test_editor_timeline.py -k reviewer_history
cd frontend && bun run test:run src/tests/pages/reviewer-invite-summary-card.test.tsx
```

Expected:
- FAIL because reminder/cancel narrative is still incomplete or raw

**Step 3: Write minimal implementation**

- extend reviewer history payload shaping in `backend/app/api/v1/reviews.py`
- ensure `editor_detail_main.py` preserves reminder/cancel context in detail payload
- update helper mapping in `helpers.ts`
- render the improved strings in the history modal

**Step 4: Run tests to verify it passes**

Run:

```bash
cd backend && pytest -q -o addopts= tests/integration/test_editor_timeline.py -k reviewer_history
cd frontend && bun run test:run src/tests/pages/reviewer-invite-summary-card.test.tsx
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add backend/app/api/v1/reviews.py backend/app/api/v1/editor_detail_main.py 'frontend/src/app/(admin)/editor/manuscript/[id]/helpers.ts' 'frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx' 'frontend/src/app/(admin)/editor/manuscript/[id]/types.ts' backend/tests/integration/test_editor_timeline.py frontend/src/tests/pages/reviewer-invite-summary-card.test.tsx
git commit -m "feat(reviewer): improve reviewer history readability"
```

### Task 2: Tighten Decision Visibility Boundaries

**Files:**
- Modify: `backend/app/services/decision_service.py`
- Modify: `backend/app/api/v1/editor_decision.py`
- Modify: `frontend/src/components/editor/decision/DecisionEditor.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- Test: `backend/tests/unit/test_decision_service_access.py`
- Test: `frontend/src/components/editor/decision/DecisionEditor.test.ts`

**Step 1: Write the failing tests**

Add assertions for:

- `first decision` never exposes `accept`
- detail page does not show decision workspace entry for manuscripts still blocked in review stage
- backend rejects stale/bypassing entry paths consistently

**Step 2: Run test to verify it fails**

Run:

```bash
cd backend && pytest -q -o addopts= tests/unit/test_decision_service_access.py
cd frontend && bun run test:run src/components/editor/decision/DecisionEditor.test.ts
```

Expected:
- FAIL because one or more stale visibility paths still allow inconsistent UI or access

**Step 3: Write minimal implementation**

- harden stage checks in `decision_service.py` and `editor_decision.py`
- align `DecisionEditor.tsx` option set with stage and final/non-final semantics
- align detail page entry visibility with the backend contract

**Step 4: Run tests to verify it passes**

Run:

```bash
cd backend && pytest -q -o addopts= tests/unit/test_decision_service_access.py
cd frontend && bun run test:run src/components/editor/decision/DecisionEditor.test.ts
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add backend/app/services/decision_service.py backend/app/api/v1/editor_decision.py frontend/src/components/editor/decision/DecisionEditor.tsx 'frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx' backend/tests/unit/test_decision_service_access.py frontend/src/components/editor/decision/DecisionEditor.test.ts
git commit -m "fix(decision): tighten decision visibility boundaries"
```

### Task 3: Add AE Review-Stage Exit E2E Coverage

**Files:**
- Modify: `frontend/tests/e2e/specs/reviewer_management_delivery.spec.ts`
- Create: `frontend/tests/e2e/specs/review_stage_exit.spec.ts`
- Test: `frontend/tests/e2e/specs/review_stage_exit.spec.ts`

**Step 1: Write the failing E2E test**

Cover:

- manuscript in `under_review`
- one reviewer already submitted
- one reviewer still `accepted`
- AE opens `Exit Review Stage`
- AE must explicitly cancel or wait
- cancel path succeeds and manuscript advances

**Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && bun run test:e2e tests/e2e/specs/review_stage_exit.spec.ts
```

Expected:
- FAIL because the flow is not yet fully asserted in browser automation

**Step 3: Write minimal implementation/test wiring**

- use route mocks or stable fixtures matching the current API shape
- assert:
  - dialog appears
  - accepted pending reviewer requires explicit action
  - manuscript advances only after valid resolution

**Step 4: Run tests to verify it passes**

Run:

```bash
cd frontend && bun run test:e2e tests/e2e/specs/review_stage_exit.spec.ts
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add frontend/tests/e2e/specs/reviewer_management_delivery.spec.ts frontend/tests/e2e/specs/review_stage_exit.spec.ts
git commit -m "test(e2e): cover review stage exit workflow"
```

### Task 4: Final Regression Sweep

**Files:**
- No new files; validate all touched files from Tasks 1-3

**Step 1: Run backend targeted regression**

Run:

```bash
cd backend && pytest -q -o addopts= tests/integration/test_editor_timeline.py tests/unit/test_decision_service_access.py
```

Expected:
- PASS

**Step 2: Run frontend targeted regression**

Run:

```bash
cd frontend && bun run test:run src/tests/pages/reviewer-invite-summary-card.test.tsx src/components/editor/decision/DecisionEditor.test.ts
cd frontend && bun run test:e2e tests/e2e/specs/review_stage_exit.spec.ts
```

Expected:
- PASS

**Step 3: Run static checks**

Run:

```bash
cd frontend && bun run lint && bunx tsc --noEmit
cd backend && uvx ruff check app tests --select=E9,F63,F7,F82
```

Expected:
- PASS

**Step 4: Commit**

```bash
git add .
git commit -m "chore: finish reviewer history and decision hardening"
```
