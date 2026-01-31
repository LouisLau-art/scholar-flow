# Data Model: User Profile

## Database: `public.profiles`

Existing table to be updated/verified.

| Field | Type | Constraint | Description |
|-------|------|------------|-------------|
| `id` | UUID | PK, FK(auth.users) | User Identity |
| `full_name` | Text | Not Null | Display Name |
| `avatar_url` | Text | Nullable | Public URL of avatar |
| `affiliation` | Text | Nullable | University/Organization |
| `title` | Text | Nullable | Dr., Prof., Mr., Ms., etc. |
| `orcid_id` | Text | Nullable | Format: `0000-0000-0000-0000` |
| `google_scholar_url` | Text | Nullable | Valid URL |
| `research_interests` | Text[] | Default `[]` | Array of tags. Max 10 items. |
| `updated_at` | Timestamptz | Default now() | Last update time |

## Storage: `avatars` Bucket

| Path | RLS Policy |
|------|------------|
| `avatars/{user_id}/*` | **Write**: Authenticated User where `id` matches path.<br>**Read**: Public. |

## Validation Rules (Pydantic/Frontend)

1.  **Avatar**:
    *   Size: < 2MB
    *   Type: image/jpeg, image/png, image/webp
2.  **Research Interests**:
    *   Max Items: 10
    *   Max Length: 50 chars per tag
    *   No duplicates (case-insensitive)
3.  **Password**:
    *   Min Length: 8 chars (Supabase default, but enforce in UI)
