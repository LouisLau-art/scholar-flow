# Quickstart: Final Decision Workspace (Feature 041)

## Setup
1. Apply migrations for `decision_letters` and `decision-attachments` storage policies.
2. Ensure one manuscript has at least one `submitted` review report.
3. Prepare test users for three role cases:
   - `editor_in_chief`
   - manuscript `assigned_editor`
   - unrelated editor/user (should be denied)

## Integration Scenarios

### 1. Making a Decision (Happy Path)
- Navigate to `/editor/decision/{manuscript_id}`.
- Review the side-by-side reports.
- Click "Generate Letter Draft".
- Edit the Markdown letter.
- Click "Submit Final Decision".
- Verify manuscript status changes (e.g., `accept -> approved`).
- Verify author receives in-app notification.
- Verify decision letter is visible to author after final submit.

### 2. Saving a Draft
- Edit the decision letter partially.
- Click "Save Draft".
- Refresh the page and verify the content persists.
- Verify author cannot read this draft.

### 3. Handling Conflicts
- Open the same decision workspace in two tabs.
- Save a draft in Tab 1.
- Try to save a draft in Tab 2.
- Expect an "Outdated Version" error due to optimistic locking.

### 4. Reject Stage Gate
- Attempt reject when manuscript is not in `decision`/`decision_done`.
- Expect backend rejection (422/validation error).
- Move manuscript to decision stage and retry reject.
- Expect success and status becomes `rejected`.

### 5. Attachment Visibility
- Upload attachment in decision workspace.
- Before final submit: verify author cannot download.
- After final submit: verify author can get signed URL and download.
