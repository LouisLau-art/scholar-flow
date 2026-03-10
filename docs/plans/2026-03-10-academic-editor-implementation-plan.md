# Academic Editor Role And Binding Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a formal `academic_editor` role, persist per-manuscript academic assignee/timestamps, and make academic routing default to the same person across later workflow steps.

**Architecture:** Introduce a first-class academic editor assignment on `public.manuscripts`, expand role/scope handling to include `academic_editor`, update technical-check routing to require/select an assignee, and make academic queue/detail views consume the real assignment instead of inferring from AE/EIC roles.

**Tech Stack:** FastAPI, Pydantic v2, Supabase Postgres/Auth, Next.js App Router, React 19, shadcn/ui.

---

### Task 1: Add database fields and scope role support

**Files:**
- Create: `supabase/migrations/20260310xxxxxx_academic_editor_binding.sql`
- Test/verify: `supabase migration list --linked`

**Step 1: Write the migration**

Add to `public.manuscripts`:
- `academic_editor_id uuid null references public.user_profiles(id)`
- `academic_submitted_at timestamptz null`
- `academic_completed_at timestamptz null`

Add indexes:
- `academic_editor_id, status, updated_at desc`
- optional helper index on `journal_id, status, academic_editor_id`

Extend `journal_role_scopes.role` allowed values to include:
- `academic_editor`

**Step 2: Dry-run linked migration parity**

Run:
```bash
supabase db push --linked --dry-run
```

Expected:
- shows the new migration ready to apply

**Step 3: Apply migration**

Run:
```bash
supabase db push --linked
```

Expected:
- migration applies successfully

**Step 4: Commit**

```bash
git add supabase/migrations/20260310xxxxxx_academic_editor_binding.sql
git commit -m "feat(db): add academic editor manuscript binding"
```

### Task 2: Add role model and scope support in backend

**Files:**
- Modify: `backend/app/core/role_matrix.py`
- Modify: `backend/app/core/journal_scope.py`
- Modify: `backend/app/models/user_management.py`
- Modify: `backend/app/api/v1/admin/users.py`
- Test: `backend/tests/unit/test_user_management.py`
- Test: `backend/tests/unit/test_journal_scope.py`

**Step 1: Write the failing tests**

Cover:
- `academic_editor` is accepted as a valid role
- `academic_editor` can be attached to journal scopes
- role matrix grants academic queue/process actions

**Step 2: Run tests to verify failure**

Run:
```bash
cd backend && pytest -q -o addopts= tests/unit/test_user_management.py tests/unit/test_journal_scope.py
```

Expected:
- FAIL because `academic_editor` is not yet part of validation / scope rules

**Step 3: Implement minimal role changes**

- Add `academic_editor` to valid role enumerations
- Add actions:
  - `academic:view_queue`
  - `academic:process`
  - `decision:record_first`
- Allow `academic_editor` in journal scope helpers and validation

**Step 4: Run tests again**

Run:
```bash
cd backend && pytest -q -o addopts= tests/unit/test_user_management.py tests/unit/test_journal_scope.py
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add backend/app/core/role_matrix.py backend/app/core/journal_scope.py backend/app/models/user_management.py backend/app/api/v1/admin/users.py backend/tests/unit/test_user_management.py backend/tests/unit/test_journal_scope.py
git commit -m "feat(auth): add academic editor role and scope support"
```

### Task 3: Require academic editor selection when AE routes to academic

**Files:**
- Modify: `backend/app/api/v1/editor_common.py`
- Modify: `backend/app/services/editor_service_precheck_workspace_decisions.py`
- Test: `backend/tests/unit/test_editor_service.py`
- Test: `backend/tests/integration/test_precheck_workflow.py`

**Step 1: Write the failing tests**

Cover:
- `decision=academic` without `academic_editor_id` returns 422
- `decision=academic` with eligible academic editor writes:
  - `academic_editor_id`
  - `academic_submitted_at`
  - `pre_check_status='academic'`
- when manuscript already has `academic_editor_id`, resubmitting academic path can preserve it unless changed

**Step 2: Run tests to verify failure**

Run:
```bash
cd backend && pytest -q -o addopts= tests/unit/test_editor_service.py tests/integration/test_precheck_workflow.py -k academic
```

Expected:
- FAIL because request model/service do not yet handle `academic_editor_id`

**Step 3: Implement minimal changes**

- Extend `TechnicalCheckRequest` with `academic_editor_id: UUID | None`
- In `submit_technical_check()`:
  - enforce `academic_editor_id` for `decision=academic`
  - validate selected profile has role `academic_editor` or `editor_in_chief`
  - validate journal scope compatibility
  - write `academic_editor_id` and `academic_submitted_at`

**Step 4: Run tests again**

Run:
```bash
cd backend && pytest -q -o addopts= tests/unit/test_editor_service.py tests/integration/test_precheck_workflow.py -k academic
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add backend/app/api/v1/editor_common.py backend/app/services/editor_service_precheck_workspace_decisions.py backend/tests/unit/test_editor_service.py backend/tests/integration/test_precheck_workflow.py
git commit -m "feat(precheck): bind academic editor on academic routing"
```

### Task 4: Make academic queue use real assignee

**Files:**
- Modify: `backend/app/services/editor_service_precheck_workspace_decisions.py`
- Modify: `backend/app/services/editor_service.py`
- Modify: `backend/app/api/v1/editor_precheck.py`
- Test: `backend/tests/integration/test_editor_process.py`
- Test: `backend/tests/integration/test_editor_timeline.py`

**Step 1: Write the failing tests**

Cover:
- `academic_editor` only sees manuscripts where `academic_editor_id == self`
- `editor_in_chief/admin` can still see all academic queue rows
- detail/process cards use `academic_editor_id` as current assignee during `pre_check/academic`

**Step 2: Run tests to verify failure**

Run:
```bash
cd backend && pytest -q -o addopts= tests/integration/test_editor_process.py tests/integration/test_editor_timeline.py -k academic
```

Expected:
- FAIL because queue/detail still infer academic ownership from EIC role and AE fields

**Step 3: Implement minimal queue/detail changes**

- Filter academic queue by `academic_editor_id` for `academic_editor`
- Keep `editor_in_chief/admin` global access
- In process/detail role queue helpers, use `academic_editor_id` for academic stage assignee
- Surface `academic_submitted_at` / `academic_completed_at`

**Step 4: Run tests again**

Run:
```bash
cd backend && pytest -q -o addopts= tests/integration/test_editor_process.py tests/integration/test_editor_timeline.py -k academic
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add backend/app/services/editor_service_precheck_workspace_decisions.py backend/app/services/editor_service.py backend/app/api/v1/editor_precheck.py backend/tests/integration/test_editor_process.py backend/tests/integration/test_editor_timeline.py
git commit -m "feat(editor): use academic editor assignment in queue and detail views"
```

### Task 5: Persist academic completion and carry binding into later workflow

**Files:**
- Modify: `backend/app/services/editor_service_precheck_workspace_decisions.py`
- Modify: `backend/app/services/decision_service.py`
- Test: `backend/tests/integration/test_decision_workspace.py`
- Test: `backend/tests/unit/test_decision_service_access.py`

**Step 1: Write the failing tests**

Cover:
- `submit_academic_check(review)` writes `academic_completed_at`
- `submit_academic_check(decision_phase)` writes `academic_completed_at`
- later decision context exposes the persisted `academic_editor_id` and timestamps

**Step 2: Run tests to verify failure**

Run:
```bash
cd backend && pytest -q -o addopts= tests/integration/test_decision_workspace.py tests/unit/test_decision_service_access.py -k academic
```

Expected:
- FAIL because timestamps/context are not yet persisted from real fields

**Step 3: Implement minimal persistence/context changes**

- In `submit_academic_check()` write `academic_completed_at = now()`
- Keep `academic_editor_id` intact on transition to `under_review` / `decision`
- Expose academic assignment info in decision context/detail payloads where relevant

**Step 4: Run tests again**

Run:
```bash
cd backend && pytest -q -o addopts= tests/integration/test_decision_workspace.py tests/unit/test_decision_service_access.py -k academic
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add backend/app/services/editor_service_precheck_workspace_decisions.py backend/app/services/decision_service.py backend/tests/integration/test_decision_workspace.py backend/tests/unit/test_decision_service_access.py
git commit -m "feat(decision): preserve academic editor binding through workflow"
```

### Task 6: Add frontend academic editor picker and defaulting

**Files:**
- Modify: `frontend/src/types/user.ts`
- Modify: `frontend/src/types/precheck.ts`
- Modify: `frontend/src/services/editor-api/manuscripts.ts`
- Modify: `frontend/src/services/editorService.ts`
- Modify: `frontend/src/components/editor/AEWorkspacePanel.tsx`
- Test: `frontend/src/tests/services/editor/precheck.api.test.ts`
- Test: `frontend/src/components/editor/AEWorkspacePanel.test.tsx`

**Step 1: Write the failing tests**

Cover:
- technical check modal shows academic editor picker when `decision=academic`
- submit payload includes `academic_editor_id`
- if manuscript already has academic editor, picker defaults to that person
- `academic` option cannot submit without a selected assignee

**Step 2: Run tests to verify failure**

Run:
```bash
cd frontend && bun run test:run src/tests/services/editor/precheck.api.test.ts src/components/editor/AEWorkspacePanel.test.tsx
```

Expected:
- FAIL because current modal has no picker or payload field

**Step 3: Implement minimal UI changes**

- Add `academic_editor_id` to request typing
- Reuse existing searchable picker pattern
- Load candidate academic editors (scope-compatible internal users)
- Show the picker only for `decision=academic`
- Require selection before submit

**Step 4: Run tests again**

Run:
```bash
cd frontend && bun run test:run src/tests/services/editor/precheck.api.test.ts src/components/editor/AEWorkspacePanel.test.tsx
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add frontend/src/types/user.ts frontend/src/types/precheck.ts frontend/src/services/editor-api/manuscripts.ts frontend/src/services/editorService.ts frontend/src/components/editor/AEWorkspacePanel.tsx frontend/src/tests/services/editor/precheck.api.test.ts frontend/src/components/editor/AEWorkspacePanel.test.tsx
git commit -m "feat(frontend): add academic editor picker for academic routing"
```

### Task 7: Show academic editor in academic queue and manuscript detail

**Files:**
- Modify: `frontend/src/app/(admin)/editor/academic/page.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/detail-sections.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/helpers.ts`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/types.ts`
- Test: `frontend/src/app/(admin)/editor/manuscript/[id]/__tests__/helpers.reviewer-summary.test.ts`
- Test: `frontend/tests/e2e/specs/precheck_workflow.spec.ts`

**Step 1: Write the failing tests**

Cover:
- academic queue displays real academic assignee
- manuscript detail displays `Academic Editor`, `Academic Submitted`, `Academic Completed`
- pre-check role queue uses academic assignee during academic stage

**Step 2: Run tests to verify failure**

Run:
```bash
cd frontend && bun run test:run 'src/app/(admin)/editor/manuscript/[id]/__tests__/helpers.reviewer-summary.test.ts'
cd frontend && bun run test:e2e tests/e2e/specs/precheck_workflow.spec.ts
```

Expected:
- FAIL because detail and queue still infer academic stage ownership

**Step 3: Implement minimal rendering changes**

- Display academic assignee in queue rows
- Add academic editor/timestamps to detail sections
- Ensure helper mapping uses backend-provided academic fields

**Step 4: Run tests again**

Run:
```bash
cd frontend && bun run test:run 'src/app/(admin)/editor/manuscript/[id]/__tests__/helpers.reviewer-summary.test.ts'
cd frontend && bun run test:e2e tests/e2e/specs/precheck_workflow.spec.ts
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add 'frontend/src/app/(admin)/editor/academic/page.tsx' 'frontend/src/app/(admin)/editor/manuscript/[id]/detail-sections.tsx' 'frontend/src/app/(admin)/editor/manuscript/[id]/helpers.ts' 'frontend/src/app/(admin)/editor/manuscript/[id]/types.ts' 'frontend/src/app/(admin)/editor/manuscript/[id]/__tests__/helpers.reviewer-summary.test.ts' frontend/tests/e2e/specs/precheck_workflow.spec.ts
git commit -m "feat(frontend): show academic editor assignment in queue and detail"
```

### Task 8: Update docs and progress trackers

**Files:**
- Modify: `docs/plans/2026-03-09-workstream-progress-notes.md`
- Modify: `docs/plans/2026-03-10-open-work-items.md`
- Modify: `docs/WORKFLOW_ASSERTIONS.md`

**Step 1: Record completed behavior**

Document:
- new role
- manuscript academic binding fields
- default carry-forward behavior
- queue access semantics

**Step 2: Run quick repo checks**

Run:
```bash
git diff --check
cd backend && uvx ruff check . --select=E9,F63,F7,F82
cd frontend && bun run lint && bunx tsc --noEmit
```

Expected:
- PASS

**Step 3: Commit**

```bash
git add docs/plans/2026-03-09-workstream-progress-notes.md docs/plans/2026-03-10-open-work-items.md docs/WORKFLOW_ASSERTIONS.md
git commit -m "docs(workflow): record academic editor binding model"
```
