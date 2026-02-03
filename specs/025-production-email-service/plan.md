# Implementation Plan: Production Email Service

**Branch**: `025-production-email-service` | **Date**: 2026-02-03 | **Spec**: [specs/025-production-email-service/spec.md](spec.md)
**Input**: Feature specification from `specs/025-production-email-service/spec.md`

## Summary

Implement a production-grade transactional email service using the Resend SDK to replace mock `print()` statements. Key components include asynchronous email dispatch (FastAPI BackgroundTasks) to ensure <200ms API latency, a centralized `email_logs` audit table in Supabase, Jinja2-based HTML templating for consistent branding, and secure, time-bound (7-day) signed tokens for reviewer access links.

## Technical Context

**Language/Version**: Python 3.14+ (Backend)
**Primary Dependencies**: `resend` (Email SDK), `fastapi.BackgroundTasks` (Async dispatch), `tenacity` (Retry logic), `jinja2` (Templating), `itsdangerous` (Secure tokens).
**Storage**: Supabase (PostgreSQL) - New `email_logs` table.
**Testing**: `pytest` with `resend` mocking; integration tests for async flow.
**Target Platform**: Linux (Hugging Face Spaces / Vercel).
**Project Type**: Web application (Backend-heavy integration).
**Performance Goals**: API response (TTFB) < 200ms for email-triggering actions.
**Constraints**: 90% recovery of transient failures via retries; 7-day token expiration.
**Scale/Scope**: Transactional emails (Invite, Status, Invoice); < 10 templates.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Glue Coding**: PASSED. Utilizing `resend` SDK and `jinja2` avoids building custom email delivery or templating engines.
- **Test-First**: PASSED. Plan includes independent testing strategies for async tasks and token validation.
- **Security First**: PASSED. Reviewer links use signed tokens with expiration; sensitive email body content is NOT logged.
- **MVP Scope**: PASSED. Moves from mock to production-ready for critical flows (invites, invoices) as required for "Post-Acceptance" robustness.
- **Environment**: PASSED. Compatible with current Cloud Supabase and HF Spaces setup.

## Project Structure

### Documentation (this feature)

```text
specs/025-production-email-service/
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
├── app/
│   ├── core/
│   │   ├── config.py           # Add RESEND_API_KEY
│   │   ├── mail.py             # Email service implementation (Resend + Retries)
│   │   └── templates/          # Jinja2 email templates
│   │       ├── base.html
│   │       ├── reviewer_invite.html
│   │       ├── status_update.html
│   │       └── invoice.html
│   └── models/
│       └── email_log.py        # New SQLAlchemy/SQLModel for email_logs
└── tests/
    └── integration/
        └── test_email_service.py
```

**Structure Decision**: Standard Backend extension. New service module (`mail.py`) in `core` to be accessible globally; templates stored in `core/templates`; new model in `models`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | | |