# Tasks: Sentry Integration

## Backend Implementation
- [ ] Add `sentry-sdk` to `backend/requirements.txt` <!-- id: 0 -->
- [ ] Create `backend/app/core/sentry_init.py` with `init_sentry` logic and privacy scrubbers (`before_send`) <!-- id: 1 -->
- [ ] Integrate `init_sentry` into `backend/app/main.py` with `try-catch` block (Zero-crash) <!-- id: 2 -->
- [ ] Add `SENTRY_DSN` to `backend/.env.example` and `backend/app/core/config.py` <!-- id: 3 -->

## Frontend Implementation
- [ ] Install `@sentry/nextjs` in `frontend/` <!-- id: 4 -->
- [ ] Create `frontend/sentry.client.config.ts` (Replay: 1.0, Traces: 1.0) <!-- id: 5 -->
- [ ] Create `frontend/sentry.server.config.ts` <!-- id: 6 -->
- [ ] Create `frontend/sentry.edge.config.ts` <!-- id: 7 -->
- [ ] Update `frontend/next.config.mjs` with `withSentryConfig` <!-- id: 8 -->
- [ ] Update `frontend/.env.example` with `NEXT_PUBLIC_SENTRY_DSN` <!-- id: 9 -->

## Verification
- [ ] **Test**: Verify Backend starts successfully with INVALID or MISSING DSN <!-- id: 10 -->
- [ ] **Test**: Trigger manual backend exception and verify Sentry capture <!-- id: 11 -->
- [ ] **Test**: Trigger manual frontend exception and verify Sentry capture + Replay <!-- id: 12 -->
- [ ] **Privacy Check**: Inspect Sentry event JSON to confirm `password` fields are scrubbed <!-- id: 13 -->
