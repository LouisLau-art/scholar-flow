# Quickstart: Revision & Resubmission

## 1. Setup Database
Run the migration script to add versioning tables.

```bash
# This will be generated in Phase 2
python scripts/run_migration.py
```

## 2. Requesting a Revision (Editor)

1.  Log in as Editor.
2.  Go to Manuscript Detail.
3.  Click "Make Decision" -> "Request Revision".
4.  Select "Major" or "Minor" and add comments.
5.  Status changes to `revision_requested`.

## 3. Submitting a Revision (Author)

1.  Log in as Author.
2.  See "Revision Requested" on Dashboard.
3.  Click "Submit Revision".
4.  Upload new PDF + Enter Response Letter.
5.  Status changes to `resubmitted`.

## 4. Re-Review

1.  Editor sees `resubmitted` manuscript.
2.  Goes to Detail -> "Manage Reviewers".
3.  Assigns reviewers (assignments created with `round_number=2`).
4.  Status changes to `under_review`.
