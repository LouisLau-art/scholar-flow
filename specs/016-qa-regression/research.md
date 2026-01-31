# Phase 0 Research: QA & E2E Regression (Feature 016)

## 1. Playwright Setup & DB Reset Strategy

### Current Status
- **Setup**: `frontend/playwright.config.ts` exists and is configured for localhost:3000.
- **DB Handling**:
  - No global DB reset mechanism exists.
  - Integration tests (`backend/tests/integration`) use a `test_manuscript` fixture that inserts and then attempts to delete data.
  - No `conftest.py` in `backend` root (only in `tests` and `tests/integration`), meaning no global backend test configuration is automatically loaded for the running app in E2E.

### Missing Components
- **DB Reset Helper**: There is no script or API endpoint to wipe/reset the database to a clean state between E2E test runs. This is critical for reliable regression testing.
- **Seeding**: No unified seeding script to populate the DB with standard test users (Author, Editor, Reviewer) and initial state.

### Decision
Implement a **Test-Only API Endpoint** (`POST /api/v1/internal/reset-db`) to handle DB reset.

### Rationale
- **Speed**: Truncating tables via an API call is faster than restarting containers or running external scripts that need to reconnect.
- **Simplicity**: Playwright can easily make an API call in the `globalSetup` or `beforeAll` hook.
- **Control**: The endpoint can be guarded by an environment variable (`ENABLE_TEST_ENDPOINTS=true`) to prevent accidental use in production.

### Alternatives Considered
- **External SQL Script**: Running `psql` or `supabase db reset` externally. *Cons*: Slower, requires external tools/credentials availability in the test runner environment.
- **Direct DB Connection in Playwright**: Connecting to Postgres directly from Node.js (Playwright). *Cons*: Duplicates DB connection logic and config; frontend tests shouldn't necessarily know about backend DB internals.

---

## 2. Service-Level Mocking Strategy (CrossrefClient)

### Current Status
- `CrossrefClient` (`backend/app/services/crossref_client.py`) mixes "Mock" methods (for Similarity Check) and real `httpx` logic (for DOI Deposit).
- `DOIWorker` (`backend/app/core/doi_worker.py`) instantiates `DOIService` which instantiates `CrossrefClient`.
- `DOIService` reads configuration from environment variables.

### Problem
- E2E tests run against a compiled/running backend. We cannot easily inject Python mocks (like `unittest.mock`) into a running process from the outside.
- `CrossrefClient` makes real HTTP calls to `https://api.crossref.org` (or similar) in its `submit_deposit` method.

### Decision
Use **Configuration-Based URL Overrides** combined with a **Lightweight Mock Server** (or "Mock Mode").

**Strategy Details**:
1.  **Integration Tests**: Use `respx` or `unittest.mock` to patch `httpx.AsyncClient` or `CrossrefClient` methods directly.
2.  **E2E Tests**:
    - Configure `CROSSREF_API_URL` env var to point to a **local mock server** (e.g., `http://localhost:4000/crossref`).
    - OR: Implement a `CROSSREF_MOCK_MODE=true` env var in `CrossrefClient` that causes it to bypass `httpx` and return canned responses.

**Recommendation**: **"Mock Mode" Flag** (`CROSSREF_MOCK_MODE=true`).
- **Why**: It's simpler to implement for Phase 0/MVP than maintaining a separate mock server process. The `CrossrefClient` already has legacy "Mock" methods; verifying the "Mock Mode" behavior is consistent is easier.
- **Implementation**: In `submit_deposit`, check `self.config.mock_mode` (or env var). If true, return a success XML response immediately.

### Rationale
- Avoids external dependencies (Crossref API) during tests.
- "Mock Mode" is self-contained within the backend, reducing infrastructure complexity for CI/CD.

---

## 3. DB Schema & Referential Integrity (013 + 015)

### Findings
- **Merged Schema**:
  - `manuscripts` (013)
  - `review_reports` (013)
  - `invoices` (013)
  - `doi_registrations` (015) (`supabase/migrations/20260130210000_doi_registration.sql`)
  - `doi_tasks` (015)
  - `doi_audit_log` (015)

### Integrity Checks
| Relationship | Constraint | Status | Action Required |
| :--- | :--- | :--- | :--- |
| `manuscripts` → `auth.users` | `author_id`, `editor_id` | **Missing ON DELETE** | **Critical**: Define behavior (CASCADE or SET NULL). Default is NO ACTION (error). |
| `review_reports` → `manuscripts` | `ON DELETE CASCADE` | ✅ OK | |
| `invoices` → `manuscripts` | `ON DELETE CASCADE` | ✅ OK | |
| `doi_registrations` → `manuscripts` | `ON DELETE CASCADE` | ✅ OK | |
| `doi_tasks` → `doi_registrations` | `ON DELETE CASCADE` | ✅ OK | |
| `doi_audit_log` → `doi_registrations` | `ON DELETE SET NULL` | ✅ OK | |
| `doi_audit_log` → `auth.users` | `created_by` | **Missing ON DELETE** | **Risk**: If user deleted, log fails. Suggest `SET NULL`. |

### Decision
1.  **Fix Missing FK Constraints**: Create a migration to add `ON DELETE SET NULL` for `doi_audit_log.created_by`.
2.  **Clarify User Deletion Policy**: For `manuscripts.author_id`, `NO ACTION` (prevent deletion of users who have submissions) is likely the safest default for data integrity, but for a test environment, it makes cleanup harder.
    - *Refinement for QA*: The DB Reset script must delete `manuscripts` *before* deleting `auth.users` to avoid FK violations.

### Missing Tables in `schema.sql`
- The `backend/app/core/schema.sql` file is outdated (v1.4.0) and does not include 015 changes.
- **Action**: Update `schema.sql` or rely solely on Supabase migrations as the source of truth.
