# Next 16 Stabilization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fully align the frontend with `Next.js 16.1.6` so the repository is no longer in a half-upgraded state, while preserving a fast, low-risk rollback path.

**Architecture:** Keep the current App Router structure and stabilize in thin slices: first create a rollback anchor and toolchain guard, then align framework dependencies, then audit all dynamic route consumers and build/lint/test scripts, and only then merge feature work on top. The implementation must treat “rollback in one revert commit” as a first-class requirement.

**Tech Stack:** Next.js 16.1.6, React 19, React DOM 19, Bun, TypeScript, ESLint CLI, Vitest, Playwright, Vercel, Hugging Face Spaces.

---

## Priority

This plan should execute **before** any additional reviewer-facing feature work. Recent bugs already showed that `Next 16` route param semantics can break reviewer flows if the framework layer stays half-migrated.

## Current Audit Snapshot

The current repo is not just "stale docs"; it has active `Next 16` migration debt:

1. **Build-blocking route typing issue**: `frontend/src/app/review/[token]/page.tsx` still passes `params.token` through legacy assumptions, and `bun run build` now fails with `Type 'ParamValue' is not assignable to type 'string'`.
2. **Deprecated runtime convention still present**: `frontend/src/middleware.ts` is still using the old `middleware` convention, while `Next 16` warns to move to `proxy`.
3. **Invalid config remains in tree**: `frontend/next.config.mjs` still carries an invalid `experimental.instrumentationHook` assumption for the current toolchain.
4. **Async request API audit is incomplete**: pages like `frontend/src/app/(public)/review/error/page.tsx` still read `searchParams` synchronously, which is inconsistent with the async request API migration path.

This means the upgrade work is not theoretical. The repository already contains concrete breakpoints that must be fixed before feature work continues.

## Official Guidance Anchors (Context7)

Official `Next.js 16.1.6` guidance confirms the following migration constraints:

- `params` and `searchParams` must be handled via the async request API migration pattern in page entries and metadata functions.
- `cookies()` and `headers()` must follow the async request API migration path as well.
- `middleware` has been renamed to `proxy`, and Next provides a codemod for this migration.
- `eslint-config-next` must be upgraded in lockstep with the framework version.
- Next provides codemods such as `next-async-request-api` and `middleware-to-proxy`; use those before hand-editing scattered pages.

## Rollback Rule

- Create a git tag before any dependency change, for example `pre-next16-full-align`.
- Keep the upgrade as a short series of isolated commits:
  - guardrails
  - dependency alignment
  - route param fixes
  - docs/tooling sync
- Do not bundle reviewer product changes into the same commits.
- If preview deploys fail, revert the upgrade commits as a block and redeploy.

### Task 1: Freeze a Rollback Anchor

**Files:**
- Modify: `README.md`
- Create: `docs/plans/2026-03-06-next16-stabilization-notes.md`

**Step 1: Record the pre-upgrade baseline**

Capture:
- current `frontend/package.json`
- current deployment SHAs
- current CI status
- current known incompatibilities:
  - `next=16.1.6`
  - `react=18`
  - `react-dom=18`
  - `eslint-config-next=14.2.0`

**Step 2: Create the rollback tag**

Run:

```bash
git tag pre-next16-full-align
git push origin pre-next16-full-align
```

Expected: the tag exists locally and remotely.

**Step 3: Commit the baseline note**

```bash
git add docs/plans/2026-03-06-next16-stabilization-notes.md
git commit -m "docs: record pre-next16 stabilization baseline"
```

### Task 2: Add a Toolchain Alignment Guard

**Files:**
- Create: `frontend/scripts/check-next-toolchain.mjs`
- Modify: `frontend/package.json`
- Modify: `.github/workflows/ci.yml`

**Step 1: Write the failing guard**

The script should fail when:
- `next` major does not match `eslint-config-next` major
- `next >= 15` while `react` or `react-dom` are still `< 19`

Example assertion shape:

```js
if (nextMajor >= 15 && reactMajor < 19) {
  throw new Error("Next 15+ requires React 19+ alignment")
}
```

**Step 2: Run it before dependency changes**

Run:

```bash
cd frontend && node scripts/check-next-toolchain.mjs
```

Expected: FAIL against the current repository state.

**Step 3: Wire it into scripts and CI**

Add:

```json
"audit:next-toolchain": "node scripts/check-next-toolchain.mjs"
```

Run it in CI after install and before build.

**Step 4: Commit**

```bash
git add frontend/scripts/check-next-toolchain.mjs frontend/package.json .github/workflows/ci.yml
git commit -m "test(frontend): add next toolchain alignment guard"
```

### Task 3: Align Core Framework Dependencies

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/bun.lock`

**Step 1: Update dependency versions together**

Target set:
- `next@16.1.6`
- `react@19`
- `react-dom@19`
- `eslint-config-next@16`
- matching `@types/react`
- matching `@types/react-dom`

Use Bun only:

```bash
cd frontend
bun add next@16.1.6 react@latest react-dom@latest
bun add -d eslint-config-next@latest @types/react@latest @types/react-dom@latest
```

**Step 2: Run the guard**

```bash
cd frontend && bun run audit:next-toolchain
```

Expected: PASS.

**Step 3: Run lint and typecheck**

```bash
cd frontend && bun run lint
cd frontend && bunx tsc --noEmit
```

Expected: identify new breakages caused by the dependency alignment only.

**Step 4: Commit**

```bash
git add frontend/package.json frontend/bun.lock
git commit -m "build(frontend): align next16 with react19 toolchain"
```

### Task 4: Audit All Client Dynamic Routes

**Files:**
- Modify: `frontend/src/app/(reviewer)/reviewer/workspace/[id]/page.tsx`
- Modify: `frontend/src/app/(public)/review/assignment/[assignmentId]/page.tsx`
- Modify: `frontend/src/app/(public)/review/error/page.tsx`
- Modify: `frontend/src/app/review/[token]/page.tsx`
- Modify: `frontend/src/app/dashboard/author/manuscripts/[id]/page.tsx`
- Audit: every `frontend/src/app/**/page.tsx` client page using route params

**Step 1: Produce the route-param inventory**

Run:

```bash
rg -n "params\\.(id|slug|token|assignmentId)|searchParams\\.|cookies\\(|headers\\(|export default function .*\\{ params \\}" frontend/src/app -g 'page.tsx'
```

**Step 2: Run the official async-request codemod first**

Use the official codemod before manual cleanup:

```bash
cd frontend && bunx @next/codemod@latest next-async-request-api .
```

Review all codemod leftovers and comments before committing.

**Step 3: Convert any remaining legacy usages**

For client pages, use one of:
- `useParams()` from `next/navigation`
- or React `use(props.params)` if that pattern is preferred consistently

Do not mix styles within the same feature area.

Pay special attention to:
- `frontend/src/app/review/[token]/page.tsx`
- `frontend/src/app/(public)/review/error/page.tsx`
- any page still coercing `ParamValue` directly into `string`

**Step 4: Add or extend tests for any bug-prone dynamic routes**

Minimum targets:
- reviewer workspace route
- magic review assignment route
- author manuscript timeline route

**Step 5: Run targeted regression checks**

```bash
cd frontend && bun run test:run src/components/ReviewerDashboard.test.tsx
cd frontend && bun run lint
```

**Step 6: Commit**

```bash
git add frontend/src/app frontend/src/components
git commit -m "fix(frontend): complete next16 dynamic route migration"
```

### Task 5: Reconcile Tooling and Build Assumptions

**Files:**
- Modify: `frontend/src/middleware.ts`
- Create: `frontend/src/proxy.ts`
- Modify: `frontend/next.config.mjs`
- Modify: `frontend/package.json`
- Modify: `frontend/scripts/check-route-budgets.mjs`
- Modify: any Next-specific audit scripts that still assume 14-era manifest shapes

**Step 1: Run build under the aligned stack**

```bash
cd frontend && bun run build
```

Current expected blocker before fixes:
- `review/[token]/page.tsx` param typing / async request API mismatch

**Step 2: Fix only framework-related build regressions**

Examples:
- run the official proxy migration codemod:

```bash
cd frontend && bunx @next/codemod@latest middleware-to-proxy .
```

- rename `middleware` convention to `proxy`
- remove invalid `experimental.instrumentationHook` assumptions
- replace any stale `skipMiddlewareUrlNormalize` usage with `skipProxyUrlNormalize`
- route manifest path changes
- lint command behavior
- cache/build output assumptions
- metadata and route convention warnings

**Step 3: Re-run route budget and custom audits**

```bash
cd frontend && bun run audit:route-budgets
cd frontend && bun run audit:dialog-onopenchange
cd frontend && bun run audit:ui-guidelines
```

**Step 4: Commit**

```bash
git add frontend/next.config.mjs frontend/package.json frontend/scripts
git commit -m "chore(frontend): align next16 build and audit tooling"
```

### Task 6: Run Product Smoke Tests on Reviewer and Submission Flows

**Files:**
- Modify if needed: `frontend/tests/e2e/*`
- Modify if needed: `frontend/src/components/ReviewerDashboard.test.tsx`
- Modify if needed: `frontend/src/tests/SubmissionForm.test.tsx`

**Step 1: Cover critical UAT paths**

Minimum smoke set:
- reviewer `Start Review`
- reviewer invite page open / accept / decline
- author submit manuscript
- author submit revision
- editor manuscript detail open

**Step 2: Execute focused tests**

```bash
cd frontend && bun run test:run src/components/ReviewerDashboard.test.tsx src/tests/SubmissionForm.test.tsx
cd frontend && bun run test:e2e --grep "review|submit|editor"
```

**Step 3: Fix only confirmed regressions introduced by the upgrade**

Do not mix unrelated UX changes into this task.

**Step 4: Commit**

```bash
git add frontend/tests frontend/src
git commit -m "test(frontend): add smoke coverage for next16 critical flows"
```

### Task 7: Sync Documentation and Version Signals

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: any badges or docs still saying `Next.js 14`

**Step 1: Update the visible version signals**

Replace stale references to:
- `Next.js 14`

With the actual aligned stack:
- `Next.js 16.1.6`
- `React 19`

**Step 2: Add a short migration note**

Document:
- why the upgrade happened
- the route param semantic change
- the rollback tag name

**Step 3: Commit**

```bash
git add README.md AGENTS.md
git commit -m "docs: sync project docs to next16 stack"
```

### Task 8: Preview Deploy, Validate, and Promote

**Files:**
- No source change required unless regressions appear

**Step 1: Push the isolated upgrade series**

```bash
git push origin main
```

**Step 2: Wait for CI and preview deploy**

Confirm:
- `ScholarFlow CI`
- frontend build
- preview deployment health

**Step 3: Manual smoke in preview**

Required pages:
- `/dashboard`
- reviewer workspace route
- reviewer invite route
- `/submit`
- `/submit-revision/[id]`
- `/editor/manuscript/[id]`

**Step 4: If preview fails, rollback fast**

```bash
git revert <upgrade-commit-range>
git push origin main
```

**Step 5: If preview passes, promote and record outcome**

Save final notes to:
- `docs/plans/2026-03-06-next16-stabilization-notes.md`

**Step 6: Commit final notes**

```bash
git add docs/plans/2026-03-06-next16-stabilization-notes.md
git commit -m "docs: record next16 stabilization rollout results"
```

Plan complete and saved to `docs/plans/2026-03-06-next16-stabilization-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?

## References

- Next.js v16.1.6 upgrade docs via Context7:
  - `version-16.mdx`
  - `version-15.mdx` (async request API migration still relevant when landing on 16)
  - `codemods.mdx`
