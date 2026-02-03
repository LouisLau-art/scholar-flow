# Research: Production Email Service

## Decisions & Rationale

### 1. Email Provider: Resend
**Decision**: Use [Resend](https://resend.com) via its official Python SDK (`resend`).
**Rationale**:
- **Modern & Developer-Friendly**: Superior DX compared to raw SMTP or legacy providers like SendGrid/SES.
- **Observability**: Built-in dashboard for tracking sent/failed emails.
- **Protocol**: HTTP-based API is generally more reliable and faster than blocking SMTP calls in an async environment.
- **Glue Coding**: Fits the "use managed services" philosophy of the project.

### 2. Async Execution: FastAPI BackgroundTasks
**Decision**: Use `fastapi.BackgroundTasks` for offloading email sending.
**Rationale**:
- **Simplicity**: No need for a separate worker process (Celery) or message broker (Redis), keeping deployment simple (Cloud Run/HF Spaces friendly).
- **Sufficiency**: For low-to-medium volume (transactional only), in-process background tasks are sufficient.
- **Resilience**: While BackgroundTasks are not persistent (lost on crash), the "critical path" (DB transaction) is prioritized. We will implement retries within the task to handle transient network issues.

### 3. Retry Logic: Tenacity
**Decision**: Use the `tenacity` library to wrap the `resend.Emails.send` call.
**Rationale**:
- **Granular Control**: Allows defining exponential backoff (e.g., wait 2s, 4s, 8s) and stopping after max attempts (e.g., 3).
- **Separation of Concerns**: Keeps the retry logic declarative and separate from the business logic.

### 4. Template Engine: Jinja2
**Decision**: Continue using `jinja2` (already in `mail.py`).
**Rationale**:
- **Consistency**: The project already uses Jinja2; no need to introduce a new dependency.
- **Flexibility**: Powerful enough for all transactional email needs (HTML + Text fallback).

### 5. Secure Tokens: ItsDangerous
**Decision**: Use `itsdangerous.URLSafeTimedSerializer`.
**Rationale**:
- **Standard**: The de facto standard for generating secure, time-limited tokens in the Python ecosystem (used by Flask, etc.).
- **Stateless**: Tokens verify themselves without needing a DB lookup for "token validity" (though we still check if the assignment exists).
- **Expiration**: Built-in support for `max_age` (7 days).

## Implementation Details

### Configuration
New Environment Variables needed in `backend/.env` (and `config.py`):
- `RESEND_API_KEY`: The API key.
- `EMAIL_SENDER`: The "From" address (e.g., `onboarding@resend.dev` or custom domain).

### Data Model
New `EmailLog` entity (mapped to `email_logs` table in Supabase):
- `id`: UUID (PK)
- `recipient`: String
- `subject`: String
- `template_name`: String
- `status`: Enum (sent, failed, pending_retry)
- `provider_id`: String (Resend ID)
- `error_message`: Text (nullable)
- `retry_count`: Integer
- `created_at`: Timestamptz

### Workflows
1.  **Trigger**: Controller calls `email_service.send_email_background()`.
2.  **Dispatch**: `BackgroundTasks.add_task` queues the execution.
3.  **Execution**:
    - Render Jinja2 template.
    - Attempt send via Resend (wrapped in `tenacity`).
    - **On Success**: Write "sent" record to `email_logs`.
    - **On Final Failure**: Write "failed" record to `email_logs` (swallow exception to not crash worker).
