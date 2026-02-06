# Data Model & Contracts

**Feature**: Reviewer Magic Link (Feature 039)
**Date**: 2026-02-06

## Data Model Changes

No new database tables. We utilize the existing `review_assignments` table.

### `review_assignments` (Existing)
- **Updates**:
    - `status`: Transition from `pending` -> `invited` -> `accepted` / `declined`.
    - `invitation_token_sent_at`: (Optional) Timestamp of last invite.

## API Contracts

### 1. Invite Reviewer (Editor)

**Endpoint**: `POST /api/v1/editor/assignments/{id}/invite`
**Access**: Editor/Admin only.

**Request**:
```json
{
  "email_template_id": "optional_template_id",
  "personal_message": "Please review this..."
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "assignment_id": "uuid",
    "status": "invited",
    "sent_to": "reviewer@example.com"
  }
}
```

### 2. Verify Magic Link (Public / Middleware)

**Endpoint**: `POST /api/v1/auth/magic-link/verify`
**Access**: Public (but requires valid JWT in body).

**Request**:
```json
{
  "token": "eyJhGci..."
}
```

**Response (Success)**:
```json
{
  "success": true,
  "data": {
    "valid": true,
    "reviewer_id": "uuid",
    "manuscript_id": "uuid",
    "guest_token": "new_session_token_if_needed"
  }
}
```

**Response (Failure)**:
```json
{
  "success": false,
  "error": "Token expired" | "Invalid signature" | "Assignment cancelled"
}
```

## JWT Payload Specification

```python
class MagicLinkPayload(BaseModel):
    sub: UUID       # Reviewer ID
    aid: UUID       # Assignment ID (shortened key for payload size)
    mid: UUID       # Manuscript ID
    exp: int        # Expiration (Unix timestamp)
    type: str = "magic_link"
```
