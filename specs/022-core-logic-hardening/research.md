# Research & Decisions

**Feature**: Core Logic Hardening (Financial Gate & Reviewer Privacy)
**Date**: 2026-02-02

## Unknowns & Clarifications

| ID | Question | Status | Decision/Finding |
|----|----------|--------|------------------|
| 1 | How to implement Financial Gate? | Resolved | Use service-level check in `publish_manuscript` API. |
| 2 | How to store confidential comments? | Resolved | Add `confidential_comments_to_editor` column to `review_reports`. |
| 3 | How to handle reviewer attachment? | Resolved | Add `attachment_path` to `review_reports` (private bucket). |
| 4 | How to confirm APC? | Resolved | Add "Confirm APC" dialog in Editor Accept flow; store in `invoices`. |

## Technology Selection

- **Backend**: Python 3.14+ / FastAPI
- **Database**: PostgreSQL (Supabase)
- **Storage**: Supabase Storage (for reviewer attachments)
- **Frontend**: Next.js / React (Strict Mode)

## Implementation Strategy

### 1. Financial Gate
- **Logic**: Strict check `if invoice.status != 'paid' and invoice.amount > 0: raise 403`
- **Location**: `backend/app/api/v1/editor.py` (or service layer)
- **Safety**: Add `# CRITICAL: PAYMENT GATE CHECK` comment.

### 2. Dual Comments & Attachments
- **Schema**:
  ```sql
  ALTER TABLE review_reports ADD COLUMN confidential_comments_to_editor TEXT;
  ALTER TABLE review_reports ADD COLUMN attachment_path TEXT;
  ```
- **Privacy**: Update `get_review` API to filter these fields for authors.

### 3. APC Confirmation
- **UI**: Modal in Editor Dashboard.
- **Data**: Create/Update `invoices` table.

## Constitution Alignment

- **Glue Coding**: Reusing existing Supabase client and auth patterns.
- **Security First**: Enforcing 403 for payment; filtering fields for privacy.
- **Test-First**: Will require backend unit/integration tests for the gate and privacy filter.
