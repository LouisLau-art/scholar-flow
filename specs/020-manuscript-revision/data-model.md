# Data Model: Revision & Resubmission

## Entity Relationships

`Manuscript` (1) --- (N) `ManuscriptVersion`
`Manuscript` (1) --- (N) `Revision`
`Manuscript` (1) --- (N) `ReviewAssignment`

## 1. Manuscripts Table (Update)

| Field | Type | Description |
|---|---|---|
| `version` | Integer | **New**. Current active version number. Default: 1. |
| `status` | String | Updated enums: `revision_requested`, `resubmitted`. |

## 2. Manuscript Versions Table (New)

Stores immutable snapshots of the manuscript content.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary Key. |
| `manuscript_id` | UUID | FK to Manuscripts. |
| `version_number` | Integer | 1, 2, 3... |
| `file_path` | String | Path in Storage (e.g., `id/v1_file.pdf`). |
| `title` | String | Snapshot of title. |
| `abstract` | Text | Snapshot of abstract. |
| `created_at` | Timestamp | When this version was submitted. |

## 3. Revisions Table (New)

Tracks the "Request for Revision" cycle.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary Key. |
| `manuscript_id` | UUID | FK to Manuscripts. |
| `round_number` | Integer | 1 (first revision request), 2... |
| `decision_type` | String | `major`, `minor`. |
| `editor_comment` | Text | Instructions from Editor. |
| `response_letter` | Text | Author's response (Rich Text). Null until submitted. |
| `status` | String | `pending` (waiting for author), `submitted` (author responded). |
| `created_at` | Timestamp | When Editor requested revision. |
| `submitted_at` | Timestamp | When Author submitted revision. |

## 4. Review Assignments Table (Update)

| Field | Type | Description |
|---|---|---|
| `round_number` | Integer | **New**. Default: 1. Tracks which round this review belongs to. |

## State Machine

1.  **Initial**: `submitted` (v1) -> `under_review` (Round 1)
2.  **Revision Request**:
    -   Editor calls `POST /editor/revisions`.
    -   Manuscript status -> `revision_requested`.
    -   New `Revision` record created (Round 1).
    -   `manuscripts` version stays at 1 (Author hasn't submitted v2 yet).
3.  **Resubmission**:
    -   Author calls `POST /manuscripts/{id}/revisions`.
    -   New PDF uploaded.
    -   New `ManuscriptVersion` (v2) created.
    -   `manuscripts` status -> `resubmitted`.
    -   `manuscripts` version -> 2.
    -   `Revision` (Round 1) status -> `submitted`, `response_letter` updated.
4.  **Re-Review**:
    -   Editor assigns reviewers.
    -   New `ReviewAssignment` records created with `round_number` = 2.
    -   Manuscript status -> `under_review`.
