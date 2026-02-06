# Implementation Plan: Reviewer Invite Response

**Branch**: `037-reviewer-invite-response` | **Date**: 2026-02-06 | **Spec**: [specs/037-reviewer-invite-response/spec.md](spec.md)
**Input**: Feature specification from `specs/037-reviewer-invite-response/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement the Reviewer Invitation Response flow:
- **UI**: A landing page for Magic Link users to Accept (with Due Date) or Decline (with Reason).
- **Logic**: State transitions for `review_assignments` (`invited` -> `accepted` / `declined`).
- **Timeline**: Audit logging of timestamps (`opened`, `accepted`, `declined`) for Editor visibility.
- **Preview**: Read-only manuscript preview (Abstract/PDF) before accepting.

## Technical Context

**Language/Version**: Python 3.14+ (Backend), TypeScript 5.x (Frontend)
**Primary Dependencies**: `fastapi`, `next.js`
**Storage**: PostgreSQL (`review_assignments`, `manuscript_status_logs`?)
**Testing**: `vitest` (Frontend), `pytest` (Backend logic)
**Target Platform**: Web Application
**Performance Goals**: Page load < 1s.
**Constraints**: Idempotent actions (double-click safety).
**Scale/Scope**: Low volume, high reliability.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Glue Coding**: Reuse `manuscript_preview` component if exists; reuse Shadcn forms.
- **Security First**: 
    - Validate `assignment_id` vs `current_user` (Guest).
    - Ensure `declined` reviewers cannot access PDF anymore.
- **Test-First**: Unit tests for state transitions.
- **Environment**: Use standard Supabase tables.

## Project Structure

### Documentation (this feature)

```text
specs/037-reviewer-invite-response/
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
│   │   └── reviewer.py          # Update: Accept/Decline endpoints
│   └── schemas/
│       └── review.py            # Update: Response schemas

frontend/
├── src/
│   ├── app/(public)/review/invite/      # Update: The "Landing Page"
│   │   ├── page.tsx                     # Main container (Logic: check status)
│   │   ├── accept-form.tsx              # Due Date picker
│   │   └── decline-form.tsx             # Reason picker
│   └── services/reviewer.ts             # API Client
```

**Structure Decision**: Web Application

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | Standard Workflow. |