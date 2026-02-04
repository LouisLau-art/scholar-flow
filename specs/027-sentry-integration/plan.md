# Technical Plan: Sentry Integration

**Feature Branch**: `027-sentry-integration`
**Goal**: Integrate Sentry for full-stack exception monitoring (Next.js + FastAPI) to support UAT, ensuring no sensitive data leaks and zero impact on system startup reliability.

## 1. Architecture & Design

### 1.1 Frontend (Next.js)
- **Library**: `@sentry/nextjs`
- **Configuration**:
  - `sentry.client.config.ts`: Browser-side error capturing, Replay (1.0 sample rate), Tracing (1.0 sample rate).
  - `sentry.server.config.ts`: Server-side error capturing (Node.js/Edge).
  - `next.config.mjs`: Wrap config with `withSentryConfig` to enable Source Map upload and build-time instrumentation.
- **Privacy**: Sentry SDK's default PII scrubbing + manual checks if needed.
- **Environment**: Distinguish between `development`, `uat` (staging), and `production`.

### 1.2 Backend (FastAPI)
- **Library**: `sentry-sdk`
- **Initialization**:
  - Located in `backend/app/main.py`.
  - **Critical**: Wrapped in `try...except` block to ensure `ImportError` or initialization failure does NOT crash the application (Zero-crash principle).
- **Integrations**:
  - `SqlalchemyIntegration`: For DB query errors.
  - `FastApiIntegration`: Default.
- **Privacy (Scrubbing)**:
  - Implement `before_send` hook to filter sensitive keys: `password`, `token`, `secret`.
  - Ensure request bodies with binary data (PDF uploads) are truncated or excluded.

## 2. Implementation Steps

### Phase 1: Backend Integration
1.  Add `sentry-sdk` to `backend/requirements.txt`.
2.  Implement `init_sentry()` function in `backend/app/core/config.py` (or directly in main) with:
    - `dsn` from env `SENTRY_DSN`.
    - `environment` from env.
    - `traces_sample_rate=1.0`.
    - `before_send` scrubber for passwords.
3.  Call `init_sentry()` in `backend/app/main.py` inside `try/except`.

### Phase 2: Frontend Integration
1.  Install `@sentry/nextjs`.
2.  Create configuration files:
    - `frontend/sentry.client.config.ts`
    - `frontend/sentry.server.config.ts`
    - `frontend/sentry.edge.config.ts`
3.  Update `frontend/next.config.mjs` to use `withSentryConfig`.
4.  Configure `replaysSessionSampleRate: 1.0` in client config.

### Phase 3: Verification
1.  **Startup Test**: Run backend without `SENTRY_DSN` and ensure it starts.
2.  **Error Test**: Create a temporary endpoint `/error` that raises `RuntimeError`.
3.  **Privacy Test**: Send a request with `password` field to the error endpoint and verify Sentry payload does not contain the cleartext password.

## 3. Configuration & Environment Variables

New Environment Variables required (to be added to `.env.example`):
- `SENTRY_DSN` (Backend)
- `NEXT_PUBLIC_SENTRY_DSN` (Frontend)
- `SENTRY_AUTH_TOKEN` (Build time, for source maps)
- `SENTRY_ORG`
- `SENTRY_PROJECT`
