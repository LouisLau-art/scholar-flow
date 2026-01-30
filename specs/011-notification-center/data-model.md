# Data Model: Notification Center

**Feature Branch**: `011-notification-center`
**Date**: 2026-01-30

## Entities

### 1. Notifications
**Table**: `public.notifications`

| Field | Type | Constraint | Description |
|-------|------|------------|-------------|
| id | uuid | PK, Default: gen_random_uuid() | Unique ID |
| user_id | uuid | FK -> auth.users | Recipient |
| manuscript_id | uuid | FK -> manuscripts, Nullable | Context link |
| type | text | Not Null | `submission`, `review_invite`, `decision`, `chase`, `system` |
| title | text | Not Null | Short header for UI |
| content | text | Not Null | Body text |
| is_read | boolean | Default: false | Read status |
| created_at | timestamptz | Default: now() | Creation time |

**RLS Policies**:
- `SELECT`: Users can only see their own notifications (`auth.uid() == user_id`).
- `UPDATE`: Users can only update `is_read` on their own notifications.
- `INSERT`: Service role only (Backend).

### 2. Review Assignments (Extension)
**Table**: `public.review_assignments`

| Field | Type | Constraint | Description |
|-------|------|------------|-------------|
| last_reminded_at | timestamptz | Nullable | Last time an auto-chase email was sent |

**Notes**:
- Used for idempotency of the auto-chasing job.

## Validation Rules
- `title` length < 255 chars.
- `content` length < 2000 chars.
- `type` must be one of the allowed enum values.

## State Transitions
- **In-App**: `is_read: false` -> (User clicks) -> `is_read: true`.
- **Auto-Chase**: `last_reminded_at: null` -> (Cron Job runs) -> `last_reminded_at: <now>`.
