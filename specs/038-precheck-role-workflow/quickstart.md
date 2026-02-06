# Quickstart: Pre-check Role Workflow

## Prerequisites
- Backend running (`uvicorn main:app`).
- Frontend running (`bun run dev`).
- Logged in as a user with appropriate roles (`managing_editor`, `assistant_editor`, `editor_in_chief`).

## Usage Flows

### 1. ME Intake
1. Login as ME.
2. Go to `/editor/intake`.
3. See manuscripts in `pre_check/intake`.
4. Click "Assign AE", select an AE from list.
5. Manuscript moves to `pre_check/technical`.

### 2. AE Technical Check
1. Login as the assigned AE.
2. Go to `/editor/workspace`.
3. See assigned manuscript.
4. Perform check (view files, etc.).
5. Click "Submit Check" (Pass).
6. Manuscript moves to `pre_check/academic`.

### 3. EIC Academic Check
1. Login as EIC.
2. Go to `/editor/academic`.
3. See manuscript.
4. Click "Decision".
   - "Send to Review" -> Status `under_review`.
   - "Reject/Decide" -> Status `decision`.

## Database Verification
```sql
SELECT id, status, pre_check_status, assistant_editor_id FROM manuscripts WHERE id = '...';
```
