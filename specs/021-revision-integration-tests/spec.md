# Feature Specification: Revision & Resubmission Integration Tests

**Feature Branch**: `021-revision-integration-tests`  
**Created**: 2026-02-02  
**Status**: Draft  
**Input**: User provided detailed testing strategy for Revision & Resubmission loop.

## Clarifications

### Session 2026-02-02
- Q: How should the test suite ensure data isolation between test runs? → A: Unique Namespacing (Recommended) - Create unique users/manuscripts per test to allow parallel execution and avoid collision.
- [Auto-Resolved] Auth Strategy: Tests will use Supabase Service Role to programmatically create users and generate valid JWTs for API calls.
- [Auto-Resolved] Storage Strategy: Integration tests will verify database records for file paths but may mock actual Storage API calls to improve speed and stability.
- [Auto-Resolved] Environment: Tests assume a local Supabase instance is running (e.g., via `supabase start`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backend Integration Test Suite (Priority: P1)

As a Developer or QA Engineer, I want to run a comprehensive backend integration test suite so that I can verify the correctness of the Revision & Resubmission logic, data integrity, and security controls without relying on the frontend.

**Why this priority**: The backend logic involves complex state transitions and critical file handling safety. API-level testing is the most efficient way to validate these rules exhaustively.

**Independent Test**: Can be fully tested by running `pytest` on the new test file and verifying all assertions pass against a running database.

**Acceptance Scenarios**:

1. **Given** a submitted manuscript (v1), **When** an Editor requests a revision (Major) and the Author submits a revision (v2), **Then** the manuscript status updates to `resubmitted`, version increments to 2, and the file path updates to the new version.
2. **Given** a resubmitted manuscript (v2), **When** the Editor assigns reviewers, **Then** the new review assignments are linked to `round_number=2`.
3. **Given** a submitted manuscript (v1), **When** an Author attempts to request a revision themselves, **Then** the API returns a 403 Forbidden error (RBAC verification).
4. **Given** a manuscript with an existing file, **When** a revision is uploaded, **Then** the original file remains accessible at its original path (File Safety verification).

---

### User Story 2 - Frontend E2E Test Suite (Priority: P2)

As a Developer or QA Engineer, I want to run an E2E test suite using Playwright so that I can verify the user interface elements for the revision workflow are visible and interactive for the correct user roles.

**Why this priority**: Ensures that the backend capabilities are correctly exposed to the user.

**Independent Test**: Can be tested by running `npx playwright test` and verifying the browser automation completes successfully.

**Acceptance Scenarios**:

1. **Given** a manuscript with `revision_requested` status, **When** the Author logs in and views the Dashboard, **Then** a "Submit Revision" button is visible.
2. **Given** a manuscript with `resubmitted` status, **When** the Editor logs in and views the Pipeline, **Then** the manuscript appears in the "Resubmitted" column/section.
3. **Given** the Submit Revision page, **When** the Author fills the Response Letter using the rich text editor, **Then** the content is successfully submitted and saved.

### Edge Cases

- **Concurrent Revisions**: What happens if an Editor requests a revision while the Author is already submitting one? (Likely blocked by state machine, but test should verify).
- **Invalid State Transitions**: Attempting to request revision on a draft manuscript.
- **Data Consistency**: Verifying `manuscript_versions` table strictly tracks the history even if the main `manuscripts` table is updated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support an automated test suite that simulates the full Revision Lifecycle: Submission -> Revision Request -> Resubmission -> Re-review Assignment.
- **FR-002**: The test suite MUST verify **Data Integrity**, specifically that file paths for previous versions are preserved and not overwritten.
- **FR-003**: The test suite MUST verify **RBAC** enforcement, ensuring only Editors/Admins can request revisions and only Authors can submit them.
- **FR-004**: The test suite MUST verify **State Machine** logic, rejecting invalid transitions (e.g., requesting revision on a draft).
- **FR-005**: The frontend tests MUST verify the visibility of "Submit Revision" actions for Authors when appropriate.
- **FR-006**: The frontend tests MUST verify the visibility of "Resubmitted" indicators for Editors.

- **FR-007**: The test suite MUST use **Unique Namespacing** for test data (e.g., unique email prefixes per test run) to ensure isolation and support parallel execution.

### Key Entities

- **Test Scenarios**: Defined sequences of API calls and assertions.
- **Test Data**: Users (Author, Editor), Manuscripts, Files.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the defined API integration scenarios (Lifecycle, RBAC, File Safety) pass in the CI/CD environment or local test runner.
- **SC-002**: The E2E test suite completes the "Request -> Submit -> Verify" loop without user intervention.
- **SC-003**: Backend tests cover verification of `round_number` incrementing correctly in `review_assignments`.
