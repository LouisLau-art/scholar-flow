# Data Model & Contracts

**Feature**: Reviewer Invite Response (Feature 037)
**Date**: 2026-02-06

## Data Model

### `review_assignments` (Existing)
- **Updates**:
  - `status`: `invited` -> `accepted` | `declined`
  - `accepted_at`: Timestamp (New)
  - `declined_at`: Timestamp (New)
  - `due_date`: Date (New/Existing - populated on accept)
  - `decline_reason`: Text/Enum (New)

## API Contracts

### 1. Get Invitation Details

**Endpoint**: `GET /api/v1/reviewer/assignments/{assignment_id}/invite`
**Access**: Reviewer (Guest/Auth)

**Response**:
```json
{
  "manuscript": {
    "title": "...",
    "abstract": "..."
  },
  "status": "invited", // or accepted, declined
  "due_date_default": "2026-02-20"
}
```

### 2. Accept Invitation

**Endpoint**: `POST /api/v1/reviewer/assignments/{assignment_id}/accept`
**Access**: Reviewer

**Request**:
```json
{
  "due_date": "2026-02-20"
}
```

**Response**:
```json
{
  "success": true,
  "redirect": "/reviewer/workspace/..."
}
```

### 3. Decline Invitation

**Endpoint**: `POST /api/v1/reviewer/assignments/{assignment_id}/decline`
**Access**: Reviewer

**Request**:
```json
{
  "reason": "busy",
  "note": "Sorry!"
}
```

**Response**:
```json
{
  "success": true
}
```
