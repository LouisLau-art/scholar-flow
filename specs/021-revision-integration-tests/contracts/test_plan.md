# Test Plan: Revision Integration

## 1. Backend Integration Tests (`test_revision_cycle.py`)

### Test Scenario 1: Standard Revision Loop
**Goal**: Verify happy path from submission to re-review.
1. **Setup**: Create Author, Editor, Manuscript (v1).
2. **Step**: Editor requests revision (Major).
3. **Assert**:
   - `manuscript.status` == 'revision_requested'
   - `revisions` table has row with `round=1, status=pending`
   - `manuscript_versions` has v1 snapshot
4. **Step**: Author uploads v2.
5. **Assert**:
   - `manuscript.status` == 'resubmitted'
   - `manuscript.version` == 2
   - `revisions` row `status=submitted`
6. **Step**: Editor assigns reviewers.
7. **Assert**: `review_assignments` has `round_number=2`.

### Test Scenario 2: RBAC Enforcement
**Goal**: Verify permissions.
1. **Setup**: Create Author, Editor, Random User.
2. **Step**: Random User tries to request revision on Author's manuscript.
3. **Assert**: 403 Forbidden.
4. **Step**: Author tries to request revision on own manuscript.
5. **Assert**: 403 Forbidden.
6. **Step**: Editor tries to submit revision for Author.
7. **Assert**: 403 Forbidden.

### Test Scenario 3: File Safety
**Goal**: Verify v1 file is preserved.
1. **Setup**: Manuscript v1 with `file_path="uid/v1_test.pdf"`.
2. **Step**: Author submits v2 with `file_path="uid/v2_test.pdf"`.
3. **Assert**:
   - `manuscript.file_path` == "uid/v2_test.pdf"
   - `manuscript_versions` (v1 record) `file_path` == "uid/v1_test.pdf"
   - Both DB records exist.

## 2. Frontend E2E Tests (`revision_flow.spec.ts`)

### Test Scenario 1: Author Visibility
1. **Login**: Author.
2. **Navigate**: Dashboard.
3. **Assert**: "Submit Revision" button visible for `revision_requested` item.
4. **Action**: Click Submit. Verify Form loads.

### Test Scenario 2: Editor Visibility
1. **Login**: Editor.
2. **Navigate**: Dashboard.
3. **Assert**: "Resubmitted" column contains the manuscript.
4. **Assert**: "Revision Requested" column contains waiting items.
