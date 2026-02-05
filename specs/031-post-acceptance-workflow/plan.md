# Implementation Plan: Enhance Post-Acceptance Workflow

**Branch**: `031-post-acceptance-workflow` | **Date**: 2026-02-04 | **Spec**: [specs/031-post-acceptance-workflow/spec.md](spec.md)

## Summary
Implement explicit status control buttons on the Manuscript Details page to guide manuscripts through the post-acceptance lifecycle (`Layout` -> `English Editing` -> `Proofreading` -> `Published`), enforcing Payment and optional Production gates.

## Technical Context

**Language/Version**: Python 3.14+, TypeScript 5.x  
**Primary Dependencies**: FastAPI, Shadcn UI  
**Storage**: Supabase (PostgreSQL) - `manuscripts.status`, `invoices` table  
**Testing**: pytest (gate logic), Playwright (E2E flow)  
**Target Platform**: Web  
**Performance Goals**: Instant feedback (<200ms) on button clicks  
**Constraints**: Payment Gate is mandatory; Production Gate is env-configurable  
**Scale/Scope**: Workflow logic extension  

## Constitution Check

- **Glue Coding**: PASSED. Reusing existing status machine and UI components.
- **Test-First**: PASSED. Plan includes validation tests for gates.
- **Security First**: PASSED. Gates are enforced at the API level, not just frontend.
- **Continuous Sync**: PASSED. Branch and context updated.

## Project Structure

### Documentation

```text
specs/031-post-acceptance-workflow/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
└── tasks.md (Next phase)
```

### Source Code

```text
backend/
├── app/
│   ├── api/v1/
│   │   └── editor.py           # New production endpoints
│   └── services/
│       └── production_service.py # Logic for next/prev stage & gates
frontend/
├── src/
│   ├── components/editor/
│   │   └── ProductionStatusCard.tsx # New UI component
│   └── app/(admin)/editor/manuscript/[id]/page.tsx # Integration
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Dedicated Service Layer | Encapsulates complex gate logic | Mixing into generic `update_status` creates maintenance nightmare |