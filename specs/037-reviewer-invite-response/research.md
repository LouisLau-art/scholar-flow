# Research: Invite Response Decisions

**Feature**: Reviewer Invite Response (Feature 037)
**Date**: 2026-02-06

## 1. Accept/Decline Logic Location

### Decision
**Backend API (`reviewer.py`)**.

### Rationale
- **Security**: State transitions (`invited` -> `accepted`) must be validated on server (check ownership, check current status).
- **Idempotency**: Backend can handle race conditions (double submission) better than frontend.
- **Audit**: Easier to log timestamps/audit trails in one place.

## 2. Due Date Window

### Decision
**Default 14 days**, configurable via `invited_at` + `review_due_days`.

### Rationale
- **Constraint**: Spec mentions "default window 7-10 days", but Feature 039/040 implies 14 days. We will stick to **14 days** as the system standard for MVP, but allow the Editor to override this *during invitation* (if implemented) or use a system config.
- **UI**: Date picker should restrict selection to `[Today, Today + 30 days]`.

## 3. Decline Reasons

### Decision
**Enum List** (Hardcoded in Frontend/Backend or DB Table).

### List
- "Busy / No time"
- "Conflict of Interest"
- "Outside field of expertise"
- "Other" (Requires text note)

### Rationale
- **Simplicity**: No need for dynamic management of reasons for MVP.

## 4. Page Flow

### Decision
**Single Page (`/review/invite`) with States**.

### Flow
1. **Loading**: Verify Token.
2. **Status Check**:
   - If `accepted`: Redirect to Workspace (Feature 040).
   - If `declined`: Show "Thank You / Declined" static message.
   - If `invited`: Show Preview + Action Buttons.
3. **Action**:
   - Accept -> Show Due Date Modal -> Submit -> Redirect Workspace.
   - Decline -> Show Reason Modal -> Submit -> Show Declined Message.
