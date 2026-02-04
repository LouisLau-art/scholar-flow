# Implementation Plan: Workflow and UI Standardization

**Branch**: `028-workflow-ui-standardization` | **Date**: 2026-02-04 | **Spec**: [specs/028-workflow-ui-standardization/spec.md](spec.md)
**Input**: Feature specification from `/specs/028-workflow-ui-standardization/spec.md`

## Summary
Implement a 12-stage manuscript lifecycle status machine and replace the existing card-based pipeline with a high-precision, filterable data table ("Manuscripts Process"). This includes creating a dedicated manuscript details page with integrated file management and editable invoice metadata.

## Technical Context

**Language/Version**: Python 3.14+, TypeScript 5.x (Next.js 14 App Router)  
**Primary Dependencies**: FastAPI, Shadcn UI (Data Tables), date-fns  
**Storage**: Supabase (PostgreSQL) - Updated status enum + new audit table  
**Testing**: pytest (Backend), Vitest (Frontend), Playwright (E2E flow)  
**Target Platform**: Web application (Linux/Vercel/HF Spaces)
**Project Type**: Web  
**Performance Goals**: <1.5s initial load for process table; <200ms status transition response  
**Constraints**: UTC timestamp storage; Zero state corruption across 12 stages  
**Scale/Scope**: Unified management for all manuscripts and reviewers  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Glue Coding**: PASSED. Utilizing Shadcn UI for tables and date-fns for time formatting.
- **Test-First**: PASSED. Plan includes unit, integration, and E2E coverage for the new lifecycle.
- **Security First**: PASSED. Invoice info editing gated by role-based permissions.
- **Continuous Sync**: PASSED. Worktree used to isolate Feature 028 from concurrent tasks.

## Project Structure

### Documentation (this feature)

```text
specs/028-workflow-ui-standardization/
├── plan.md              # This file
├── research.md          # Decisions on status machine and table architecture
├── data-model.md        # Extended Manuscript and Reviewer entities
├── quickstart.md        # Code snippets for status and filters
├── contracts/           # OpenAPI schema for new process endpoints
└── tasks.md             # (To be generated next)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/v1/
│   │   └── editor.py           # Updated endpoints for process table and metadata
│   ├── services/
│   │   └── editorial_service.py # Core logic for 12-stage transitions
│   └── models/
│       └── manuscript.py       # Updated status enum
└── tests/

frontend/
├── src/
│   ├── app/editor/process/     # New "Manuscripts Process" page
│   ├── app/editor/manuscript/  # New dedicated details page [id]
│   ├── components/editor/      # ManuscriptTable and InvoiceInfo form
│   └── services/               # Updated API hooks for process list
└── tests/
```

**Structure Decision**: Web application extension. Updating existing `editor` modules in both frontend and backend to support tabular views and detailed metadata management.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | | |