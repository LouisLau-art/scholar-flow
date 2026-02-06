# Implementation Plan: Pre-check Role Workflow (ME → AE → EIC)

**Branch**: `038-precheck-role-workflow` | **Date**: 2026-02-06 | **Spec**: [specs/038-precheck-role-workflow/spec.md](spec.md)
**Input**: Feature specification from `specs/038-precheck-role-workflow/spec.md`

## Summary

Implement a role-based intake workflow (ME -> AE -> EIC) for manuscripts. This involves adding dedicated queues for Managing Editors (Intake), Assistant Editors (Technical Check), and Editors-in-Chief (Academic Check), along with a new database column to track the assigned AE. The workflow enforces a "no direct reject" policy during pre-check, requiring manuscripts to enter the Decision phase for rejection.

## Technical Context

**Language/Version**: Python 3.14+, TypeScript 5.x
**Primary Dependencies**: FastAPI, Supabase (PostgreSQL), Pydantic
**Storage**: PostgreSQL (`manuscripts` table update, `status_transition_logs` usage)
**Testing**: pytest (Backend), Vitest (Frontend), Playwright (E2E)
**Target Platform**: Web (Next.js + Python API)
**Project Type**: Web Application
**Performance Goals**: <200ms API response for queue listing
**Constraints**: No direct reject from pre-check; MVP minimal changes (Glue Coding).
**Scale/Scope**: <10k manuscripts, standard CRUD + State Machine logic.

## Constitution Check

*GATE: Passed Phase 0 research.*

- **Glue Coding**: Reusing `ManuscriptStatus` logic and `status_transition_logs`.
- **Test-First**: Will create tests for new endpoints and state transitions.
- **Security**: RBAC enforcement for ME/AE/EIC queues.
- **Env & Tooling**: Using `uv` and `bun`.
- **MVP**: No new external services (Sentry/Email reused).

## Project Structure

### Documentation (this feature)

```text
specs/038-precheck-role-workflow/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/          # Update Manuscript model
│   ├── services/        # Add Pre-check service logic
│   └── api/
│       └── v1/
│           └── editor/  # Update Editor endpoints
└── tests/
    ├── integration/     # Test workflow
    └── unit/            # Test state machine

frontend/
├── src/
│   ├── components/      # New/Updated Queue Views
│   ├── pages/           # ME/AE/EIC Dashboards
│   └── services/        # API Client updates
└── tests/
```

**Structure Decision**: Option 2 (Web application)

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A       |            |                                     |