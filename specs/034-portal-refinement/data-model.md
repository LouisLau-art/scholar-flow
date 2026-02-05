# Data Model: Refine Portal Home and Navigation

## Entities

### Journal Metadata (Config-driven)
Static configuration representing the journal's identity.

| Field | Type | Description |
|---|---|---|
| `title` | string | Journal Name |
| `issn` | string | ISSN (e.g., 2073-4433) |
| `impact_factor` | string | Impact Factor Placeholder (e.g., 3.2) |
| `description` | string | Short academic summary |

### Published Manuscript (Read-only View)
Projection of the `manuscripts` table for the public homepage.

| Field | Type | Requirement |
|---|---|---|
| `id` | uuid | Link to article page |
| `title` | string | Full title |
| `authors` | string[] | Formatted list |
| `abstract` | string | Truncated (e.g., first 300 chars) |
| `published_at` | timestamptz | Display date (YYYY-MM-DD) |

## State Transitions
None. This feature is primarily read-only for the homepage.
