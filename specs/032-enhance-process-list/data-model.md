# Data Model: Enhance Manuscripts Process List

## Entities

### Manuscript (Read Model)
The list view requires a joined projection.

| Field | Type | Source |
|---|---|---|
| `id` | UUID | manuscripts |
| `title` | Text | manuscripts |
| `status` | Enum | manuscripts |
| `submitted_at` | TIMESTAMPTZ | manuscripts (created_at) |
| `updated_at` | TIMESTAMPTZ | manuscripts |
| `journal_name` | Text | journals.title |
| `editor_name` | Text | user_profiles.full_name |
| `owner_name` | Text | user_profiles.full_name |

## Query Parameters (Filters)
These map directly to API/DB queries.

| Param | Type | Description |
|---|---|---|
| `q` | String | Search term for ID/Title |
| `status` | List<String> | Comma-separated status values |
| `journal` | UUID | Journal ID |
| `editor` | UUID | User ID |

## Validation Rules
- `status`: Must be valid `ManuscriptStatus` enum values.
- `q`: Trimmed, max length 100 chars.
