# Data Model: Reviewer Library Management

## Entities

### User Profile (Extended)
Standardizes the profile to support academic identities.

| Field | Type | Description |
|---|---|---|
| `title` | Text | Enum: Prof., Dr., Mr., Ms., etc. |
| `homepage_url` | Text | URL to personal/institutional page |
| `full_name` | Text | Existing field |
| `affiliation` | Text | Existing field |
| `research_interests` | Text[] | Existing field |
| `is_reviewer_active` | Boolean | Flag to hide from library search (default: true) |

## Relationships
- **User Profile** (1) <---> (N) **Review Assignment**

## Validation Rules
- `homepage_url`: Must be a valid HTTP/HTTPS URL if provided.
- `title`: Must be one of the predefined academic titles.
- `email`: Must be unique in `auth.users`.

## State Transitions
1. **Library Entry**: User record created in `auth.users` + `user_profiles` (if not exists). `is_reviewer` (if added as a flag) or simply presence in the system.
2. **Assignment**: `review_assignments` record created. Status set to `invited`. Email triggered.
