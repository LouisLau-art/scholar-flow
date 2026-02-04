# Implementation Plan: Manuscript Details and Invoice Info Management

**Branch**: `029-manuscript-details-invoice` | **Date**: 2026-02-04 | **Spec**: [specs/029-manuscript-details-invoice/spec.md](spec.md)
**Input**: Feature specification from `/specs/029-manuscript-details-invoice/spec.md`

## Summary
Implement a professional, organized manuscript details page that groups files into three functional sections (Cover Letter, Original, Peer Review) and provides an editor-only modal for managing invoice-related metadata (`invoice_metadata`).

## Technical Context

**Language/Version**: Python 3.14+, TypeScript 5.x (Next.js 14 App Router)  
**Primary Dependencies**: FastAPI, Shadcn UI (Card, Dialog, Button), date-fns  
**Storage**: Supabase (PostgreSQL) - `manuscripts.invoice_metadata` JSONB  
**Testing**: pytest (Backend), Vitest (Frontend), Playwright (E2E)  
**Target Platform**: Web (Linux/Vercel/HF Spaces)
**Project Type**: Web  
**Performance Goals**: <500ms for metadata save; responsive file layout at 1600px width  
**Constraints**: Peer Review files must be restricted to Editor/Admin roles  
**Scale/Scope**: Manuscript-level metadata and file handling  

## Constitution Check

- **Glue Coding**: PASSED. Reusing Shadcn UI components for the details page layout and modal forms.
- **Test-First**: PASSED. Plan includes verification of metadata persistence and role-based file visibility.
- **Security First**: PASSED. Invoice editing is gated by role checks; file downloads use signed URLs.
- **Continuous Sync**: PASSED. Branch `029-manuscript-details-invoice` is active.

## Project Structure

### Documentation (this feature)

```text
specs/029-manuscript-details-invoice/
├── plan.md              # This file
├── research.md          # UI layout decisions and audit strategy
├── data-model.md        # JSONB structure for invoice info
├── quickstart.md        # API usage and component examples
├── contracts/           # OpenAPI schema for details and update endpoints
└── tasks.md             # (Next phase)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/v1/
│   │   └── editor.py           # New GET details and PUT invoice-info endpoints
│   └── services/
│       └── editorial_service.py # Logic for audit logging and metadata updates
└── tests/

frontend/
├── src/
│   ├── app/(admin)/editor/manuscript/[id]/ # New details page route
│   ├── components/editor/
│   │   ├── ManuscriptDetailsHeader.tsx
│   │   ├── FileSectionGroup.tsx
│   │   └── InvoiceInfoModal.tsx
└── tests/
```

**Structure Decision**: Web application extension. Building on the `editor` domain in both frontend and backend.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | | |