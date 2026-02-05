# Implementation Plan: Align Manuscript Detail Page Layout

**Branch**: `033-align-detail-layout` | **Date**: 2026-02-04 | **Spec**: [specs/033-align-detail-layout/spec.md](spec.md)

## Summary
Refactor the Manuscript Details page (`/editor/manuscript/[id]`) to strictly match the visual hierarchy defined in the reference PDF (P4/P6). This involves regrouping header metadata, creating a 3-column file area, and moving invoice management to a dedicated bottom panel.

## Technical Context

**Language/Version**: TypeScript 5.x (Next.js)  
**Primary Dependencies**: Tailwind CSS (Grid), Shadcn UI (Card, Dialog)  
**Storage**: Supabase (Read-only mostly, Write for Uploads)  
**Testing**: Playwright (Visual layout check)  
**Target Platform**: Web (Desktop optimized)  
**Performance Goals**: Cumulative Layout Shift (CLS) < 0.1  
**Constraints**: Must reuse existing `Feature 029` backend logic where possible.  
**Scale/Scope**: UI Refactor  

## Constitution Check

- **Glue Coding**: PASSED. Reusing Shadcn components.
- **Test-First**: PASSED. Plan implies verifying presence of new sections.
- **Security First**: PASSED. Peer review file visibility restricted to editor (frontend logic + backend RLS if applicable).
- **Continuous Sync**: PASSED. Branch and context updated.

## Project Structure

### Documentation

```text
specs/033-align-detail-layout/
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
frontend/
├── src/
│   ├── app/(admin)/editor/manuscript/[id]/page.tsx # Main Layout
│   ├── components/editor/
│   │   ├── ManuscriptHeader.tsx    # New Component
│   │   ├── FileSectionCard.tsx     # New Component (Generic)
│   │   ├── InvoiceInfoPanel.tsx    # New Component (Bottom)
│   │   └── UploadReviewFile.tsx    # New Component
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New Components | Isolate layout logic | Putting everything in `page.tsx` is unmaintainable |