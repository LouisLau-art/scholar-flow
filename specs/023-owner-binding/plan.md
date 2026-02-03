# Implementation Plan: Owner Binding

**Branch**: `023-owner-binding` | **Date**: 2026-02-02 | **Spec**: [link](spec.md)
**Input**: Feature specification from `/specs/023-owner-binding/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement the "Owner Binding" feature to allow Editors/Admins to assign an internal owner (KPI owner) to a manuscript. This involves:
1.  **Database**: Adding `owner_id` to `manuscripts` table.
2.  **Backend**: Updating API endpoints to expose and update `owner` information, with RBAC validation.
3.  **Frontend**: Adding an owner selection combobox to the Manuscript Detail sidebar and an "Owner" column to the Editor Pipeline list.

## Technical Context

**Language/Version**: Python 3.14+ (Backend), TypeScript 5.x (Frontend)
**Primary Dependencies**: FastAPI, Supabase (PostgreSQL/Auth), Next.js, Shadcn UI
**Storage**: PostgreSQL (Supabase)
**Testing**: `pytest` (Backend), `npx playwright test` (Frontend)
**Target Platform**: Web Application
**Project Type**: Web application (backend + frontend)
**Performance Goals**: Owner update confirmation < 2s; List view refresh < 1s.
**Constraints**: Must strictly validate that assigned owners have internal staff roles (editor/admin).
**Scale/Scope**: Core workflow enhancement; low data volume impact (one UUID per manuscript).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Gates
- [x] **Glue Coding**: Reusing Shadcn combobox and existing API patterns.
- [x] **Test-First**: Will implement backend integration tests for RBAC and Frontend E2E for UI flow.
- [x] **Security First**: Critical RBAC check on `owner_id` assignment (must be staff).
- [x] **Environment**: Using standard Cloud Supabase context.

## Project Structure

### Documentation (this feature)

```text
specs/023-owner-binding/
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
└── src/
    ├── api/v1/
    │   └── manuscripts.py  # Update GET/PATCH
    └── services/
        └── manuscript_service.py # Core logic

frontend/
└── src/
    ├── components/
    │   ├── editor/
    │   │   ├── OwnerCombobox.tsx # New component
    │   │   └── ManuscriptSidebar.tsx # Integration point
    │   └── EditorPipeline.tsx # Update list columns
```

**Structure Decision**: Standard feature extension within existing backend/frontend directories.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A       |            |                                     |
