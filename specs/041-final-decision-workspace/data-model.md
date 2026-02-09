# Data Model: Final Decision Workspace (Feature 041)

## Entities

### Decision Letter (`public.decision_letters`)
Stores decision draft/final content and associated conclusion for a manuscript version.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID | Primary Key |
| `manuscript_id` | UUID | Foreign Key to `manuscripts` |
| `manuscript_version` | INT | Version of the manuscript this decision applies to |
| `editor_id` | UUID | Foreign Key to `user_profiles` (the decision maker) |
| `content` | TEXT | The body text of the decision letter |
| `decision` | TEXT | Conclusion: `accept`, `reject`, `major_revision`, `minor_revision` |
| `status` | TEXT | `draft` or `final` |
| `attachment_paths` | TEXT[] | Supabase Storage paths for decision attachments |
| `created_at` | TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | Last update time (used for optimistic locking) |

## Validation Rules
- `manuscript_id` and `editor_id` are required.
- `content` is required for `status='final'`.
- `decision` must be one of the allowed values.
- `updated_at` must match the version in the database when updating a `draft`.
- `reject` submission is only valid when workflow stage is `decision` or `decision_done`.
- author can read decision letter and attachments only when `status='final'`.

## Relationships
- `manuscripts` (1) : (N) `decision_letters`
- `user_profiles` (1) : (N) `decision_letters` (as Editor)

## Access Rules
- Write access: `editor_in_chief`, manuscript `assigned_editor`, `admin`.
- Author read access: final decision letter and final attachments only.

## Storage Rules
- Decision attachments are stored in Supabase bucket `decision-attachments`.
- Attachment URLs are returned by backend signed-url endpoints only.
