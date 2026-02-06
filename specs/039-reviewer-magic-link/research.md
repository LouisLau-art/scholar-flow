# Research: JWT & Magic Link Best Practices

**Feature**: Reviewer Magic Link (Feature 039)
**Date**: 2026-02-06

## 1. Token Format & Library

### Decision
Use **HS256 (HMAC-SHA256)** JWTs via `pyjwt` library.

### Rationale
- **Simplicity**: No need for asymmetric keys (RS256) since only our backend generates and verifies tokens.
- **Performance**: HS256 is faster than RSA/ECDSA.
- **Library**: `pyjwt` is the standard, well-maintained Python library for JWTs.

### Implementation Details
- **Secret**: Reuse `SUPABASE_SERVICE_ROLE_KEY` or `SECRET_KEY` (if available in `.env`) as the signing key.
- **Payload**:
  ```json
  {
    "sub": "reviewer_uuid",
    "assignment_id": "uuid",
    "manuscript_id": "uuid",
    "exp": 1735689600, // 14 days from now
    "type": "magic_link"
  }
  ```

## 2. Frontend Session Handling

### Decision
Use a **Scoped Guest Cookie** (`scholarflow_guest_token`).

### Rationale
- **Isolation**: Prevents conflict if the user (e.g., an editor) is already logged in with their main account.
- **Middleware Support**: Next.js Middleware can easily read cookies to allow/deny access to `/review/*` routes.
- **Persistence**: Cookies persist across browser restarts (unlike memory), useful if reviewer returns later.

### Alternatives Considered
- **Local Storage**: Cannot be read by Middleware (SSR issues).
- **Session Storage**: Lost on tab close.

## 3. Email Delivery

### Decision
Use existing `app.services.email_service` (assuming SMTP/SendGrid setup).

### Pattern
- Create `invitation.html` Jinja2 template.
- Inject `magic_link_url`.
- Send asynchronously via BackgroundTasks.

## 4. Revocation Strategy

### Decision
**Hybrid Validation** (Stateless Token + DB Check).

### Logic
- Although JWT is stateless, the `verify` endpoint MUST check the `review_assignments` table status.
- If `status == 'cancelled'`, reject the token even if the signature is valid.
- This balances performance (crypto verification first) with business logic consistency (revocation).
