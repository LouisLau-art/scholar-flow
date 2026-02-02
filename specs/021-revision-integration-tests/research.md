# Research: Revision & Resubmission Integration Tests

## 1. Test Data Strategy

**Decision**: Use programmatic data seeding via Supabase Service Role Client within Pytest fixtures.

**Rationale**:
- **Speed**: Direct DB insertion is faster than going through API for setup.
- **Control**: Allows creating precise states (e.g., a manuscript in `revision_requested` state directly) without running the full workflow every time.
- **Isolation**: Each test can create its own isolated data set (users, manuscripts).

**Alternatives Considered**:
- **SQL Seed Files**: Good for static data, but inflexible for dynamic test scenarios needing unique IDs.
- **API-based Setup**: Slower and couples tests to other API endpoints (e.g., create user API), which might fail independently.

## 2. Authentication in Tests

**Decision**: Generate valid JWTs for test users using a helper function that interacts with Supabase Auth (GoTrue) or mocks the token signature if the backend uses a local secret for validation.

**Rationale**:
- **Realism**: Tests RBAC logic properly.
- **Simplicity**: Once a helper is written, `client.post(..., headers={"Authorization": f"Bearer {token}"})` is standard.

## 3. Storage Mocking vs. Real

**Decision**: For *Integration* tests, mock the Supabase Storage client calls but verify the *database* updates (file paths).

**Rationale**:
- **Stability**: Avoids network flakes or local storage service dependency issues during CI.
- **Focus**: The critical logic is the *path generation* (v1 vs v2) and *database record* (manuscript_versions), not the actual byte transfer to S3/MinIO.
- **Implementation**: Patch `app.services.revision_service.supabase_admin.storage` or similar.

## 4. E2E Test Strategy

**Decision**: Use Playwright with a "Test Data Seeder" approach.

**Rationale**:
- **Pre-conditions**: E2E tests should not rely on a fragile chain of UI actions to set up state (e.g., don't manually register a user just to test revision submission).
- **Flow**: Seed a user and manuscript -> Login -> execute revision flow -> verify.

## 5. Unknowns Resolved

- **Data Seeding**: Confirmed use of Supabase Service Role.
- **Auth**: Confirmed use of JWT generation/mocking.
- **File Safety**: Verified by checking DB records for `file_path`.
