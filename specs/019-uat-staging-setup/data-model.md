# Data Model: User Acceptance Testing (UAT) & Staging Environment Setup

## Entities

### UAT Feedback
Represents a user-submitted issue or feedback report captured in the Staging environment.

**Table**: `uat_feedback`

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| `id` | `UUID` | Yes | Primary Key | Default: `gen_random_uuid()` |
| `description` | `TEXT` | Yes | The user's feedback text | Min length: 5 chars |
| `severity` | `VARCHAR(20)` | Yes | Severity level | Enum: `low`, `medium`, `critical` |
| `url` | `TEXT` | Yes | URL where feedback was submitted | Valid URL format |
| `user_id` | `UUID` | No | ID of the submitting user (if logged in) | FK to `auth.users.id` |
| `status` | `VARCHAR(20)` | Yes | Status of the report | Default: `new`. Enum: `new`, `triaged`, `resolved`, `ignored` |
| `created_at` | `TIMESTAMPTZ` | Yes | Timestamp of submission | Default: `now()` |

## Relationships

- **UAT Feedback** `(0..*)` -> `(1)` **User** (`user_id`): A user can submit multiple feedback reports. Anonymous feedback is allowed (user_id is NULL).

## Demo Scenarios (Logical)

These are not persistent entities but pre-defined states created by the seed script.

1. **Pending Manuscript**: A manuscript in `submitted` state with no assigned editor.
2. **Overdue Review**: A review assignment where `due_date` is in the past and `status` is `pending`.
3. **Unpaid Acceptance**: A manuscript in `accepted` state where `apc_status` is `pending_payment`.
