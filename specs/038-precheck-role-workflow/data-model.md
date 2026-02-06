# Data Model: Pre-check Role Workflow

## Entities

### Manuscripts (Updated)
**Table**: `public.manuscripts`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `assistant_editor_id` | UUID | No | FK to `user_profiles.id`. The AE assigned to perform technical check. |
| `pre_check_status` | TEXT | No | Sub-status for PRE_CHECK. Values: `intake`, `technical`, `academic`. Default: `intake`. |

### User Profiles (Reference)
**Table**: `public.user_profiles`

| Field | Type | Description |
|-------|------|-------------|
| `roles` | TEXT[] | Contains `managing_editor`, `assistant_editor`, `editor_in_chief`. |

## Enums

### Pre-check Status
- `intake`: Managing Editor (ME) Queue. Initial state for new submissions.
- `technical`: Assistant Editor (AE) Queue. After ME assigns AE.
- `academic`: Editor-in-Chief (EIC) Queue. After AE completes technical check.

### Manuscript Status (Existing)
- `pre_check`: Master status for all above sub-statuses.
- `decision`: Used for rejection routing.

## State Transitions (Pre-check Phase)

1. **Submission**: `(draft)` -> `status=pre_check`, `pre_check_status=intake`.
2. **ME Assignment**: `pre_check_status=intake` -> `pre_check_status=technical`, `assistant_editor_id={ae_id}`.
3. **AE Completion**: `pre_check_status=technical` -> `pre_check_status=academic`.
4. **EIC Decision (Pass)**: `pre_check_status=academic` -> `status=under_review` (or `minor_revision`).
5. **EIC Decision (Route to Reject)**: `pre_check_status=academic` -> `status=decision`.

*Note: Any stage can request revision (`minor_revision`/`major_revision`), which returns to `resubmitted`.*
*After `resubmitted`, it should logically return to the stage that requested it, or start over at `intake`?*
*Assumption: Resubmitted goes to `intake` or `technical` based on who requested. MVP: Resubmitted -> `status=resubmitted`. Next step logic handles where it goes.*
