# Implementation Plan: Reviewer Invitation & Magic Link

**Branch**: `039-reviewer-magic-link` | **Date**: 2026-02-06 | **Spec**: [specs/039-reviewer-magic-link/spec.md](spec.md)
**Input**: Feature specification from `specs/039-reviewer-magic-link/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a secure, stateless authentication mechanism for reviewers using "Magic Links".
- **Core Concept**: Stateless JWT token (HS256) embedded in an email link.
- **Flow**:
    1. Editor searches Reviewer Library and sends invite.
    2. Backend generates JWT containing `assignment_id` and `reviewer_id`.
    3. Reviewer clicks link (`.../review/invite?token=...`).
    4. Frontend middleware intercepts, validates via backend, and sets a scoped guest session cookie.
    5. Reviewer accesses specific manuscript without password.

## Technical Context

**Language/Version**: Python 3.14+ (Backend), TypeScript 5.x (Frontend)
**Primary Dependencies**: `pyjwt` (new), `fastapi`, `next.js`, `supabase-js`
**Storage**: None (Stateless JWT); status updates to `review_assignments` table.
**Testing**: `pytest` (backend crypto/logic), `vitest` (frontend middleware logic), `playwright` (E2E flow).
**Target Platform**: Linux server (Backend), Vercel (Frontend).
**Project Type**: Web Application.
**Performance Goals**: Instant token generation; Middleware validation < 50ms.
**Constraints**: 14-day expiration; Scoped access only to assigned manuscript.
**Scale/Scope**: Low volume (hundreds of invites), high security criticality.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Glue Coding**: Usage of standard `pyjwt` library; standard Next.js Middleware patterns.
- **Security First**: 
    - JWT signed with backend `SECRET_KEY` (HS256).
    - Scoped Session (Guest mode) ensures isolation from main user session.
    - No PII in token payload (IDs only).
- **Test-First**: Unit tests for Token Generator/Validator are mandatory before integration.
- **Environment**: Keys managed via `.env` (`SECRET_KEY` reuse or new `JWT_SECRET`).

## Project Structure

### Documentation (this feature)

```text
specs/039-reviewer-magic-link/
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
│   ├── core/
│   │   └── security.py          # JWT generation/validation logic
│   ├── api/v1/endpoints/
│   │   ├── auth.py              # New: /auth/magic-link/verify
│   │   └── editor.py            # Update: /invite to send email
│   └── templates/email/
│       └── invitation.html      # Email template

frontend/
├── src/
│   ├── middleware.ts            # Update: Handle /review/invite route
│   ├── app/(public)/review/     # Reviewer Workspace
│   └── services/auth.ts         # Guest session handling
```

**Structure Decision**: Standard Web Application (Next.js + FastAPI)

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | Stateless JWT is the simplest secure approach (vs DB tokens). |