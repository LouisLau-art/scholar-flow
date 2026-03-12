# Pre-check AE Assignment Decoupling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Decouple technical-return waiting state from AE ownership so ME can assign/reassign AE before author resubmission, and author resubmission returns to the correct queue automatically.

**Architecture:** Keep the existing manuscript table and treat workflow state and responsibility as two orthogonal dimensions. Reuse `status`, `pre_check_status`, and `assistant_editor_id`; make every write path set them explicitly; then expose a stable AE assignment entry outside the Intake-only shortcut.

**Tech Stack:** FastAPI, Pydantic v2, Supabase Postgres, Next.js App Router, React 19, Tailwind CSS, Vitest/Playwright, pytest.

---

### Task 1: Lock the canonical backend state rules with failing tests

**Files:**
- Modify: `backend/tests/unit/test_precheck_role_service.py`
- Modify: `backend/tests/unit/test_revision_service.py`
- Modify: `backend/tests/integration/test_precheck_flow.py`

**Step 1: Write the failing unit tests for waiting-author assignment**

Add tests covering:

- `assign_ae()` allows `status='revision_before_review'` with `pre_check_status='intake'`
- `assign_ae()` allows `status='revision_before_review'` with `pre_check_status='technical'`
- assigning AE while waiting author forces resume stage to `technical`

**Step 2: Write the failing unit tests for return semantics**

Add tests covering:

- ME intake return explicitly persists `pre_check_status='intake'` and clears `assistant_editor_id`
- AE technical return explicitly persists `pre_check_status='technical'` and preserves `assistant_editor_id`

**Step 3: Write the failing integration tests for end-to-end routing**

Add or extend scenarios:

- `ME intake return -> ME assign AE -> author resubmit -> manuscript appears in AE workspace`
- `AE technical return -> ME reassign AE -> author resubmit -> manuscript appears in new AE workspace`
- `ME intake return without AE assignment -> author resubmit -> manuscript returns to intake`

**Step 4: Run tests to verify failure**

Run:
```bash
cd backend && pytest -q -o addopts= tests/unit/test_precheck_role_service.py tests/unit/test_revision_service.py tests/integration/test_precheck_flow.py
```

Expected:
- FAIL because waiting-author assignment guards and explicit state persistence are incomplete

**Step 5: Commit**

```bash
git add backend/tests/unit/test_precheck_role_service.py backend/tests/unit/test_revision_service.py backend/tests/integration/test_precheck_flow.py
git commit -m "test(precheck): cover ae assignment decoupling rules"
```

### Task 2: Make backend write paths set resume-stage and ownership explicitly

**Files:**
- Modify: `backend/app/services/editor_service_precheck_intake.py`
- Modify: `backend/app/services/editor_service_precheck_workspace_decisions.py`
- Modify: `backend/app/services/revision_service.py`
- Modify: `backend/app/api/v1/manuscripts_submission.py`

**Step 1: Implement intake return canonical write**

In `request_intake_revision()` ensure the status update writes:

- `status='revision_before_review'`
- `pre_check_status='intake'`
- `assistant_editor_id=None`
- `ae_sla_started_at=None`

through `extra_updates` or equivalent explicit update payload.

**Step 2: Implement technical return canonical write**

In `submit_technical_check(decision='revision')` ensure the status update writes:

- `status='revision_before_review'`
- `pre_check_status='technical'`
- preserve existing `assistant_editor_id`
- preserve or refresh `ae_sla_started_at` as needed

**Step 3: Extend `assign_ae()` guard to waiting-author states**

Allow:

- `pre_check/intake`
- `pre_check/technical`
- `revision_before_review/intake`
- `revision_before_review/technical`

When assignment happens under `revision_before_review`, explicitly set:

- `assistant_editor_id=<ae>`
- `pre_check_status='technical'`

**Step 4: Keep author resubmission logic canonical**

In `submit_revision()` and/or `manuscripts_submission.py` make the resume logic depend on:

- `status='revision_before_review'`
- persisted `pre_check_status`
- `assistant_editor_id`

and stop relying on loosely inferred stage when a canonical persisted value exists.

**Step 5: Run tests to verify pass**

Run:
```bash
cd backend && pytest -q -o addopts= tests/unit/test_precheck_role_service.py tests/unit/test_revision_service.py tests/integration/test_precheck_flow.py
```

Expected:
- PASS

**Step 6: Commit**

```bash
git add backend/app/services/editor_service_precheck_intake.py backend/app/services/editor_service_precheck_workspace_decisions.py backend/app/services/revision_service.py backend/app/api/v1/manuscripts_submission.py
git commit -m "feat(precheck): decouple waiting author state from ae assignment"
```

### Task 3: Normalize audit payloads and read-model interpretation

**Files:**
- Modify: `backend/app/services/editor_service.py`
- Modify: `backend/app/api/v1/editor_detail_cards.py`
- Modify: `backend/app/services/editor_service_precheck_workspace_views.py`

**Step 1: Write the failing read-model tests**

Add tests covering:

- `revision_before_review` rows are interpreted as waiting-author items with resume target
- detail/process cards show the correct current or next assignee
- audit payloads expose `source_status` / `source_pre_check_status` when assigning AE while waiting author

**Step 2: Run tests to verify failure**

Run:
```bash
cd backend && pytest -q -o addopts= tests/unit/test_editor_service.py tests/integration/test_editor_service.py -k precheck
```

Expected:
- FAIL because current read models only understand pre-check substage as an active queue stage

**Step 3: Implement read-model adjustments**

- Extend precheck/intake log helpers to understand waiting-author AE assignment context
- Make detail cards and workspace row mappers expose:
  - waiting-author resume target
  - current `assistant_editor_id`
  - assignee label text suitable for ME views
- Preserve backward compatibility for existing `pre_check` consumers

**Step 4: Run tests to verify pass**

Run:
```bash
cd backend && pytest -q -o addopts= tests/unit/test_editor_service.py tests/integration/test_editor_service.py -k precheck
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add backend/app/services/editor_service.py backend/app/api/v1/editor_detail_cards.py backend/app/services/editor_service_precheck_workspace_views.py
git commit -m "feat(editor): surface ae ownership during waiting author stage"
```

### Task 4: Add a stable AE assignment entry in manuscript detail

**Files:**
- Modify: `frontend/src/components/AssignAEModal.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/detail-sections.tsx`
- Modify: `frontend/src/services/editor-api/manuscripts.ts`
- Modify: `frontend/src/services/editorService.ts`

**Step 1: Write the failing frontend tests**

Add tests covering:

- manuscript detail shows `Assign AE` or `Change AE` when viewer is ME/Admin and manuscript is non-terminal
- detail page can open `AssignAEModal` for `revision_before_review`
- successful assignment refreshes detail data

**Step 2: Run tests to verify failure**

Run:
```bash
cd frontend && bun run vitest frontend/src/app/(admin)/editor/manuscript/[id]/__tests__ --run
```

Expected:
- FAIL because detail page currently has no AE assignment entry

**Step 3: Implement the detail-page assignment entry**

- Reuse `AssignAEModal`
- Allow state-aware copy:
  - assign in intake
  - reassign in technical
  - assign for post-return follow-up in `revision_before_review`
- Refresh detail context after success

**Step 4: Run tests to verify pass**

Run:
```bash
cd frontend && bun run vitest frontend/src/app/(admin)/editor/manuscript/[id]/__tests__ --run
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add frontend/src/components/AssignAEModal.tsx frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx frontend/src/app/(admin)/editor/manuscript/[id]/detail-sections.tsx frontend/src/services/editor-api/manuscripts.ts frontend/src/services/editorService.ts
git commit -m "feat(frontend): add global ae assignment entry in manuscript detail"
```

### Task 5: Remove the misleading Intake-only lock and expose waiting-author work in ME views

**Files:**
- Modify: `frontend/src/app/(admin)/editor/intake/page.tsx`
- Modify: `frontend/src/components/editor/ManagingWorkspacePanel.tsx`
- Modify: `backend/app/services/editor_service_precheck_workspace_views.py`

**Step 1: Write the failing UI tests**

Add tests covering:

- Intake page no longer hardcodes waiting-author rows as globally “不可操作”
- Managing Workspace has a visible waiting-author bucket for `revision_before_review`
- waiting-author rows show resume target and assignee

**Step 2: Run tests to verify failure**

Run:
```bash
cd frontend && bun run vitest frontend/src/components/editor/__tests__ frontend/src/app/(admin)/editor/intake --run
```

Expected:
- FAIL because current Intake UI renders waiting-author rows as read-only gray placeholders

**Step 3: Implement the ME-facing UI changes**

- Change Intake copy so the page is clearly about intake decisions, not total ownership management
- Add `awaiting_author` bucket in Managing Workspace
- Show:
  - waiting reason
  - resume target (`回 ME` / `回 AE`)
  - AE if already assigned
- Link or action into detail for reassignment

**Step 4: Run tests to verify pass**

Run:
```bash
cd frontend && bun run vitest frontend/src/components/editor/__tests__ frontend/src/app/(admin)/editor/intake --run
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add frontend/src/app/(admin)/editor/intake/page.tsx frontend/src/components/editor/ManagingWorkspacePanel.tsx backend/app/services/editor_service_precheck_workspace_views.py
git commit -m "feat(editor): expose waiting author ae ownership in me views"
```

### Task 6: Add end-to-end regression for the real business scenario

**Files:**
- Modify: `frontend/tests/e2e/specs/precheck_workflow.spec.ts`
- Modify: `frontend/tests/e2e/pages/editor.page.ts`

**Step 1: Write the failing E2E scenario**

Add mocked scenario:

1. ME opens manuscript
2. ME triggers intake return
3. While waiting author, ME assigns AE from detail or ME workspace
4. Author resubmits
5. Manuscript appears in AE workspace, not Intake

**Step 2: Run E2E to verify failure**

Run:
```bash
cd frontend && bun run test:e2e --grep "Pre-check workflow"
```

Expected:
- FAIL because current mocked flow does not cover waiting-author reassignment semantics

**Step 3: Implement the minimal E2E fixture updates**

- Update route mocks for:
  - `revision_before_review`
  - assign-AE during waiting-author stage
  - resubmission routing to AE workspace
- Keep tests deterministic and mocked

**Step 4: Run E2E to verify pass**

Run:
```bash
cd frontend && bun run test:e2e --grep "Pre-check workflow"
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add frontend/tests/e2e/specs/precheck_workflow.spec.ts frontend/tests/e2e/pages/editor.page.ts
git commit -m "test(e2e): cover ae reassignment during waiting author stage"
```

### Task 7: Sync workflow documentation with the new canonical rules

**Files:**
- Modify: `specs/044-precheck-role-hardening/data-model.md`
- Modify: `specs/044-precheck-role-hardening/spec.md`
- Modify: `specs/038-precheck-role-workflow/spec.md`
- Modify: `docs/plans/2026-03-12-precheck-ae-assignment-decoupling-design.md`

**Step 1: Update spec language**

Document explicitly:

- technical return and AE assignment are not mutually exclusive
- `revision_before_review` can carry resume target via `pre_check_status`
- author resubmission returns to ME or AE according to canonical rules

**Step 2: Run a quick grep review**

Run:
```bash
rg -n "不可操作|灰态保留|ME-first intake pre-check before AE assignment|revision_before_review" specs docs frontend backend
```

Expected:
- identify any stale wording that still implies “waiting author means cannot assign AE”

**Step 3: Commit**

```bash
git add specs/044-precheck-role-hardening/data-model.md specs/044-precheck-role-hardening/spec.md specs/038-precheck-role-workflow/spec.md docs/plans/2026-03-12-precheck-ae-assignment-decoupling-design.md
git commit -m "docs(precheck): align ae ownership decoupling rules"
```

Plan complete and saved to `docs/plans/2026-03-12-precheck-ae-assignment-decoupling-implementation-plan.md`. Two execution options:

1. Subagent-Driven (this session) - I dispatch fresh subagent per task, review between tasks, fast iteration
2. Parallel Session (separate) - Open new session with executing-plans, batch execution with checkpoints

Which approach?
