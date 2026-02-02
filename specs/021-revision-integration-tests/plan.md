# Implementation Plan: Revision & Resubmission Integration Tests

**Branch**: `021-revision-integration-tests` | **Date**: 2026-02-02 | **Spec**: [link](spec.md)
**Input**: Feature specification from `/specs/021-revision-integration-tests/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a comprehensive testing strategy for the "Revision & Resubmission" feature, comprising:
1.  **Backend Integration Tests (Pytest)**: Verify state transitions, RBAC, and file safety for the revision loop (Submission -> Revision Request -> Resubmission -> Re-review).
2.  **Frontend E2E Tests (Playwright)**: Verify UI visibility and interaction flow for Authors and Editors.

## Technical Context

**Language/Version**: Python 3.14+ (Backend), TypeScript 5.x (Frontend)
**Primary Dependencies**: FastAPI, Supabase (PostgreSQL), Playwright, Pytest
**Storage**: PostgreSQL (Supabase), Supabase Storage
**Testing**: `pytest` (Backend), `npx playwright test` (Frontend)
**Target Platform**: Web Application
**Project Type**: Web application (backend + frontend)
**Performance Goals**: Tests should run reliably in CI environment.
**Constraints**: Tests must not pollute production data; E2E tests must handle auth correctly.
**Scale/Scope**: Integration tests for core revision workflow; E2E tests for happy path.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Gates
- [x] **Test-First**: This feature explicitly implements the testing strategy for Feature 020.
- [x] **Integration Testing**: Focuses entirely on integration and E2E testing.
- [x] **CLI Interface**: Tests are executable via standard CLI tools (`pytest`, `playwright`).

## Project Structure

### Documentation (this feature)

```text
specs/021-revision-integration-tests/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
└── tests/
    └── integration/
        └── test_revision_cycle.py  # New backend integration test file

frontend/
└── tests/
    └── e2e/
        └── specs/
            └── revision_flow.spec.ts  # New/Updated frontend E2E test file
```

**Structure Decision**: Standard testing directory structure for both backend and frontend.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A       |            |                                     |
