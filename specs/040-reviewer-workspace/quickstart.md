# Quickstart: Testing Reviewer Workspace

**Feature**: 040-reviewer-workspace

## Prerequisites

1. **Backend**: Running on `http://localhost:8000`
2. **Frontend**: Running on `http://localhost:3000`
3. **Data**: A manuscript in `under_review` with an assigned reviewer.

## Test Data Setup

Run the following script to create a test reviewer and assignment:

```bash
# Generate a test assignment and get a Magic Link
# (Assumes Feature 039 scripts exist or use DB direct)
python scripts/seed_mock_reviewers_auth.py --create-assignment
```

*Output should provide a Magic Link URL: `http://localhost:3000/review/invite?token=...`*

## Manual Test Steps

1. **Access Workspace**:
   - Paste the Magic Link into an Incognito window.
   - Verify redirect to `/reviewer/workspace/[uuid]`.
   - Verify Sidebar/Header are GONE.

2. **View PDF**:
   - Check the Left Panel. PDF should load (dummy PDF if local).

3. **Form Interaction**:
   - Type in "Comments for Author".
   - Reload page (Simulate crash).
   - *Expectation*: Data lost (MVP) OR Warning dialog appears (if `beforeunload` implemented).

4. **Submission**:
   - Fill all fields.
   - Attach a dummy file (if implemented).
   - Click "Submit".
   - Verify redirect to Thank You page.
   - Click "Back" -> Verify Workspace is now Read-Only.

## Automated Tests

```bash
# Run E2E tests for layout
npm run test:e2e specs/reviewer-workspace

# Run Backend API tests
pytest backend/tests/integration/test_reviewer_workspace.py
```
