# Test Data Model

**Purpose**: Defines the entities and states used within the integration test suite. This is not the production database schema, but the abstraction layer used by tests.

## 1. Test User
A wrapper around Supabase Auth User + User Profile.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Auth ID (and Profile ID). |
| `email` | String | Unique test email (e.g., `test_editor_{uuid}@example.com`). |
| `role` | String | 'editor', 'author', 'reviewer'. |
| `token` | String | Valid JWT for API calls. |

## 2. Test Manuscript
A wrapper around the Manuscript entity to track test state.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Manuscript ID. |
| `author_id` | UUID | Owner. |
| `status` | String | Current status in DB. |
| `version` | Integer | Current version number. |
| `file_path` | String | Current file path in storage (mocked). |

## 3. Test Revision Request
Tracks the parameters used to trigger a revision.

| Field | Type | Description |
|---|---|---|
| `manuscript_id` | UUID | Target manuscript. |
| `decision_type` | String | 'major' / 'minor'. |
| `comment` | String | Editor's instructions. |
| `round` | Integer | Expected round number. |
