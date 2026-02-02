# Research: Notification Center

**Feature Branch**: `011-notification-center`
**Date**: 2026-01-30
**Input**: Feature spec.md and user clarifications

## 1. Email Sending (Backend)

- **Decision**: Python Standard Library `smtplib` + `email.mime`
- **Rationale**: 
  - Matches the "Glue Coding" and "Simple & Explicit" principles.
  - Avoids introducing a heavy third-party dependency (like FastAPI-Mail) for basic transactional email needs.
  - Provides full control over SMTP handshake and error handling.
- **Alternatives Considered**: 
  - **FastAPI-Mail**: Rejected to keep dependency tree light.
  - **Supabase Auth SMTP**: Rejected as it is locked to Auth events only.

## 2. In-App Realtime Notifications (Frontend)

- **Decision**: Supabase Realtime (Client-side Subscription)
- **Rationale**: 
  - Native Supabase feature, no extra infrastructure required.
  - Provides true "push" experience for the red dot.
  - Significantly better UX than polling.
- **Implementation Pattern**:
  - `useEffect` hook in `SiteHeader` or a global `NotificationProvider`.
  - Listen for `INSERT` on `public.notifications` table filter by `user_id`.

## 3. Auto-Chasing Scheduler (Background)

- **Decision**: Internal API Endpoint triggered by Cron
- **Rationale**: 
  - Since we don't have a persistent Celery worker, an HTTP endpoint is the standard way to trigger jobs in serverless/containerized environments.
  - Can be triggered by GitHub Actions (Cron) or an external uptime monitor service in MVP.
- **Security**: Protected by `X-Admin-Key` header (Environment Variable).
- **Idempotency**: Relies on `last_reminded_at` column in `review_assignments`.

## 4. Email Templating

- **Decision**: Jinja2
- **Rationale**: 
  - De facto standard for Python templating.
  - Allows separating HTML structure from Python logic.
  - Robust XSS protection (auto-escaping) by default.
- **Structure**: Templates stored in `backend/app/templates/emails/`.
