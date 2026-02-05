# Implementation Plan: Enhance Manuscripts Process List

**Branch**: `032-enhance-process-list` | **Date**: 2026-02-04 | **Spec**: [specs/032-enhance-process-list/spec.md](spec.md)

## Summary
Upgrade the Editor's "Manuscripts Process" page with URL-driven filtering, high-precision timestamps, and inline "Quick Action" buttons for high-frequency tasks, aligning the UI with the reference PDF.

## Technical Context

**Language/Version**: Python 3.14+, TypeScript 5.x  
**Primary Dependencies**: FastAPI, Shadcn UI (Table, Popover, Dialog), Lucide React  
**Storage**: Supabase (PostgreSQL)  
**Testing**: pytest (filter logic), Playwright (URL state sync)  
**Target Platform**: Web  
**Performance Goals**: List filtering <500ms; Quick actions optimistic update  
**Constraints**: 1600px layout width utilization  
**Scale/Scope**: UI/UX enhancement  

## Constitution Check

- **Glue Coding**: PASSED. Reusing Shadcn components.
- **Test-First**: PASSED. Plan includes verification of filter combinations.
- **Security First**: PASSED. Quick actions enforce same permissions as detail page actions.
- **Continuous Sync**: PASSED. Branch and context updated.

## Project Structure

### Documentation

```text
specs/032-enhance-process-list/
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
│   │   └── editor.py           # Updated list endpoint with filters
frontend/
├── src/
│   ├── app/(admin)/editor/process/page.tsx # Main page update
│   ├── components/editor/
│   │   ├── ProcessFilterBar.tsx    # New component
│   │   ├── ManuscriptActions.tsx   # New component (Icon buttons)
│   │   └── QuickPrecheckModal.tsx  # New component
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | | |
