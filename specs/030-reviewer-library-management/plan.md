# Implementation Plan: Reviewer Library Management

**Branch**: `030-reviewer-library-management` | **Date**: 2026-02-04 | **Spec**: [specs/030-reviewer-library-management/spec.md](spec.md)

## Summary
Decouple reviewer data entry from manuscript assignment. Expand `user_profiles` to include academic metadata (Title, Homepage) and provide a centralized management interface for Editors.

## Technical Context

**Language/Version**: Python 3.14+, TypeScript 5.x  
**Primary Dependencies**: FastAPI, Supabase-py, Next.js, Shadcn UI  
**Storage**: Supabase (PostgreSQL) - `user_profiles` table extension  
**Testing**: pytest (unit/integration), Playwright (E2E)  
**Target Platform**: Web  
**Performance Goals**: <500ms for library search (1,000+ entries)  
**Constraints**: No invitation email sent during "Add to Library"  
**Scale/Scope**: Academic identities and workflow management  

## Constitution Check

- **Glue Coding**: PASSED. Reusing existing `user_profiles` schema and Supabase Auth.
- **Test-First**: PASSED. Planning integration tests for user creation and assignment emails.
- **Security First**: PASSED. Using service role for administrative user creation; role checks for library access.
- **Continuous Sync**: PASSED. Branch created; context files updated.

## Project Structure

### Documentation (this feature)

```text
specs/030-reviewer-library-management/
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
│   ├── api/v1/editor.py         # Library search & add endpoints
│   ├── services/
│   │   └── reviewer_service.py  # User creation & profile logic
│   └── models/
│       └── profile.py           # Title/Homepage fields
└── supabase/
    └── migrations/              # DB extension (Title/Homepage)

frontend/
├── src/
│   ├── app/(admin)/editor/reviewers/ # Library management page
│   ├── components/editor/
│   │   ├── ReviewerLibraryList.tsx
│   │   ├── AddReviewerModal.tsx
│   │   └── ReviewerAssignmentSearch.tsx # Integrated in Manuscript details
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Immediate Auth User Creation | Allows system-wide identity reuse | Temporary tables lead to orphaned data and syncing issues |