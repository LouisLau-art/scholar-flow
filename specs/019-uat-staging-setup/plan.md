# Implementation Plan: User Acceptance Testing (UAT) & Staging Environment Setup

**Branch**: `019-uat-staging-setup` | **Date**: 2026-01-31 | **Spec**: [specs/019-uat-staging-setup/spec.md](spec.md)
**Input**: Feature specification from `/specs/019-uat-staging-setup/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature establishes a dedicated Staging environment for User Acceptance Testing (UAT) with strict data and code isolation from Production. It introduces:
1.  **Environment Isolation**: `NEXT_PUBLIC_APP_ENV` configuration to conditionally render UAT tools.
2.  **UAT Tools**: A fixed visual banner and a "Report Issue" feedback widget (Staging only).
3.  **Data Safety**: Integration with a separate Supabase project/instance for Staging.
4.  **Demo Readiness**: A deterministic seeding script to wipe and repopulate the Staging DB with specific business scenarios.

## Technical Context

**Language/Version**: Python 3.10+ (FastAPI), TypeScript 5.x (Next.js 14.2)
**Primary Dependencies**: 
- Backend: `fastapi`, `supabase`, `pydantic`
- Frontend: `next`, `react` (18), `lucide-react`, `sonner` (Shadcn UI)
**Storage**: Supabase (PostgreSQL) - Separate Project for Staging
**Testing**: 
- Backend: `pytest`
- Frontend: `vitest` (Unit), `playwright` (E2E)
**Target Platform**: Linux server (Backend), Vercel/Node (Frontend)
**Project Type**: Web Application (Next.js Frontend + FastAPI Backend)
**Performance Goals**: Seed script < 10s execution time. Feedback submission < 1s latency.
**Constraints**: Zero code leakage of UAT widget to Production bundle (Tree-shaking).
**Scale/Scope**: Low volume (UAT users only).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Principles Analysis

-   **Library-First**: The Seed Script will be a standalone Python module/library (`backend/scripts/seed_staging.py`). The Feedback Widget is a self-contained Component (`frontend/src/components/uat/`).
-   **CLI Interface**: The seed script will be executable via CLI (`python -m scripts.seed_staging`).
-   **Test-First**: 
    -   **Backend**: Tests for the feedback API endpoint (`test_feedback.py`).
    -   **Frontend**: Component tests for the Widget (visibility toggling based on env).
    -   **E2E**: Playwright test verifying Banner exists in Staging mode.
-   **Integration Testing**: Verify Seed Script actually populates DB correctly. Verify Feedback API writes to DB.
-   **Observability**: The Feedback feature *is* an observability tool.

### Gate Evaluation

-   [x] **Requirement Clarity**: Spec defines clear scenarios and acceptance criteria.
-   [x] **Technical Feasibility**: Stack supports env vars and conditional builds.
-   [x] **Risk Assessment**: High risk of data pollution if isolation fails → Mitigated by Separate Project decision.

## Project Structure

### Documentation (this feature)

```text
specs/019-uat-staging-setup/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api_v1_system.yaml
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/v1/endpoints/
│   │   └── system.py        # New: Feedback endpoint
│   ├── models/
│   │   └── feedback.py      # New: Feedback entity
│   └── schemas/
│       └── feedback.py      # New: Pydantic models
├── scripts/
│   └── seed_staging.py      # New: Reset & Seed script
└── tests/
    └── api/
        └── test_system.py   # New: API tests

frontend/
├── src/
│   ├── components/
│   │   └── uat/             # New: UAT specific components
│   │       ├── EnvironmentBanner.tsx
│   │       └── FeedbackWidget.tsx
│   └── lib/
│       └── env.ts           # Update: Ensure strict typing for APP_ENV
└── tests/
    ├── e2e/
    │   └── uat.spec.ts      # New: Verify banner/widget presence
    └── components/
        └── FeedbackWidget.test.tsx
```

**Structure Decision**: Standard "Web application" split. New components in `frontend/src/components/uat` to isolate them easily. New script in `backend/scripts/` for admin tasks.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Separate Supabase Project | Data Safety | Schema isolation in same DB is prone to leakage (PostgREST exposes public schema by default) and accidental deletions. |
