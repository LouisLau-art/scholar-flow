# Implementation Plan: Core Logic Hardening (Financial Gate & Reviewer Privacy)

**Branch**: `022-core-logic-hardening` | **Date**: 2026-02-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/022-core-logic-hardening/spec.md`

## Summary

This feature implements critical business logic hardening:
1. **Financial Gate**: Enforcing payment before publication via backend 403 checks and frontend UI states.
2. **Reviewer Privacy**: Adding "Confidential Comments" and "Attachments" for reviewers, strictly hidden from authors.
3. **APC Confirmation**: Allowing editors to confirm/discount prices upon acceptance.

## Technical Context

**Language/Version**: Python 3.14+, TypeScript 5.x (Strict)
**Primary Dependencies**: FastAPI, Pydantic, Supabase-py
**Storage**: Supabase (PostgreSQL), Supabase Storage
**Testing**: Pytest (Backend), Playwright (E2E)
**Target Platform**: Linux server
**Project Type**: Web application
**Performance Goals**: <200ms API response for gate checks
**Constraints**: Hard blocking of unpaid publications; strict data privacy for review comments.
**Scale/Scope**: Core workflow logic update; touches 3 endpoints and 2 tables.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Glue Coding**: Reusing Supabase Auth/DB.
- [x] **Test-First**: Will write gate tests first.
- [x] **Security First**: Financial Gate is a security feature.
- [x] **Strict Mode**: Frontend updates will be type-safe.

## Project Structure

### Documentation (this feature)

```text
specs/022-core-logic-hardening/
├── plan.md              # This file
├── research.md          # Implementation decisions
├── data-model.md        # Schema updates
├── quickstart.md        # Testing guide
├── contracts/           # OpenAPI specs
└── tasks.md             # Task list
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/v1/
│   │   ├── editor.py    # Publish & Decision updates
│   │   └── reviews.py   # Submit review updates
│   ├── models/          # Schema updates
│   └── services/        # Logic updates
└── tests/
    ├── integration/     # Gate tests
    └── unit/

frontend/
├── src/
│   ├── app/dashboard/editor/ # Publish button & APC modal
│   └── app/review/           # Review form updates
```

**Structure Decision**: Standard ScholarFlow architecture (Backend/Frontend split).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |