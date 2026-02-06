# Implementation Plan: Reviewer Workspace

**Branch**: `040-reviewer-workspace` | **Date**: 2026-02-06 | **Spec**: [specs/040-reviewer-workspace/spec.md](spec.md)
**Input**: Feature specification from `specs/040-reviewer-workspace/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a dedicated "Reviewer Workspace" that provides a distraction-free, immersive environment for reviewing manuscripts.
- **Layout**: Minimal header (Exit only), hidden sidebar, split-screen (PDF left, Action Panel right).
- **Core Features**:
    - Browser-based PDF rendering (iframe/PDF.js).
    - Dual-channel feedback form (Author vs. Editor).
    - Decision submission (Accept/Revision/Reject).
    - File attachment support for annotated reviews.
- **Security**: Strict session validation (Guest/Auth) ensuring access only to assigned manuscripts.
- **Data Safety**: "Warn on Exit" protection for unsaved changes.

## Technical Context

**Language/Version**: Python 3.14+ (Backend), TypeScript 5.x (Frontend)
**Primary Dependencies**: `react-pdf` or native iframe (Frontend), `fastapi` (Backend)
**Storage**: Supabase Storage (for PDF retrieval + Attachment upload), PostgreSQL (Metadata)
**Testing**: `vitest` (Frontend components), `playwright` (E2E layout/flow), `pytest` (Backend logic)
**Target Platform**: Vercel (Frontend), Hugging Face Spaces (Backend)
**Project Type**: Web Application
**Performance Goals**: Workspace load < 2s; PDF rendering < 3s.
**Constraints**: Mobile support via stacked layout; MVP auto-save via `beforeunload`.
**Scale/Scope**: Single page app logic; high interaction density.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Glue Coding**: Reuse existing PDF storage logic; reuse `shadcn/ui` components for form.
- **Security First**: 
    - Verify `assignment_id` ownership in backend API.
    - Signed URLs for PDF/Attachment access.
    - Read-only mode enforcement post-submission.
- **Test-First**: Unit tests for form validation; E2E for split-screen layout.
- **Environment**: Use existing Supabase buckets (`manuscripts`, `review-attachments` from Feat 033).

## Project Structure

### Documentation (this feature)

```text
specs/040-reviewer-workspace/
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
│   ├── api/v1/endpoints/
│   │   └── reviewer.py          # New: Workspace data aggregation & submission
│   └── schemas/
│       └── review.py            # Review submission schema

frontend/
├── src/
│   ├── app/(reviewer)/layout.tsx        # New: Immersive Layout (No sidebar)
│   ├── app/(reviewer)/workspace/[id]/   # New: Workspace Page
│   │   ├── page.tsx                     # Main container
│   │   ├── pdf-viewer.tsx               # Left panel
│   │   └── action-panel.tsx             # Right panel (Form)
│   └── components/ui/                   # Reuse existing components
```

**Structure Decision**: Web Application (Next.js App Router + FastAPI)

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | Standard CRUD + Layout variation. |