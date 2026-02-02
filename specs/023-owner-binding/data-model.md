# Data Model: Owner Binding

**Purpose**: Defines schema changes for tracking manuscript ownership.

## 1. Manuscript Entity Updates

| Field | Type | Description |
|---|---|---|
| `owner_id` | UUID (FK) | Reference to `auth.users` (and implicitly `user_profiles`). Nullable. |

**Constraints**:
- `owner_id` must reference a valid user.
- Application-level validation ensures referenced user has `editor` or `admin` role.

## 2. Internal Owner (Virtual Entity)

Represents the staff member assigned to a manuscript. Sourced from `user_profiles`.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | User ID. |
| `full_name` | String | Display name. |
| `roles` | JSONB | Must contain "editor" or "admin". |
