# Feature Specification: Comprehensive QA & E2E Regression

**Feature Branch**: `016-qa-regression`  
**Created**: Fri Jan 30 2026  
**Status**: Draft  
**Input**: User description: "Feature 016: Comprehensive QA & E2E Regression..."

## Clarifications

### Session 2026-01-30
- Q: Test Data Strategy? → A: Ephemeral DB Reset (reset and seed fresh data before suite runs).
- Q: DOI Mocking Level? → A: Service-Level Mock (mock CrossrefClient in Python).
- Q: Browser Coverage? → A: Chromium Only (for speed and stability).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Author Critical User Journey (Priority: P1)

As an Author, I need to register, submit a manuscript, and track its status so that I can publish my work without technical blockers.

**Why this priority**: Authors are the primary content creators. If they cannot submit, the platform fails completely. This flow exercises registration, authentication, file upload, and database persistence.

**Independent Test**: Can be tested independently by running the "Author Flow" E2E script which covers registration -> login -> submission -> dashboard check.

**Acceptance Scenarios**:

1. **Given** I am a new user on the registration page, **When** I sign up with valid credentials, **Then** I am redirected to the dashboard and see a welcome message.
2. **Given** I am a logged-in author, **When** I submit a new manuscript (fill metadata, upload PDF), **Then** I see the submission in my "My Submissions" list with status "Pending".
3. **Given** I am viewing a submitted manuscript, **When** I check the details page, **Then** I see the correct title, abstract, and file preview link.

---

### User Story 2 - Editor Critical User Journey (Priority: P1)

As an Editor, I need to assign reviewers, make decisions, and publish articles so that the peer review process can conclude successfully.

**Why this priority**: Editors drive the workflow forward. This flow exercises RBAC (Editor role), reviewer assignment logic, state transitions, and the new publishing triggers (DOI).

**Independent Test**: Can be tested independently by simulating an Editor login, locating a pending submission, assigning a reviewer (mocked), and moving the status to "Published".

**Acceptance Scenarios**:

1. **Given** I am an Editor viewing a pending submission, **When** I assign a reviewer, **Then** the submission status updates (if applicable) and an assignment record is created.
2. **Given** I am an Editor, **When** I submit an "Accept" decision, **Then** the manuscript status changes to "Published" and I see a success confirmation.
3. **Given** an article is published, **When** I check the DOI audit logs (admin view), **Then** I see a "DOI Registration" task was triggered.

---

### User Story 3 - CMS Content Management (Priority: P2)

As an Editor/Admin, I need to create and manage portal pages so that I can update site content without code changes.

**Why this priority**: This validates the integration of the recently merged Feature 013 (CMS). It ensures the new database tables and API endpoints interact correctly with the frontend.

**Independent Test**: Can be tested by creating a page in the admin panel and verifying it loads at the public URL.

**Acceptance Scenarios**:

1. **Given** I am an Admin in the CMS dashboard, **When** I create a new page with title "About Us" and slug "about-us", **Then** the page is saved and listed in the page management table.
2. **Given** a published CMS page "about-us", **When** a public user visits `/journal/about-us`, **Then** they see the content I authored.
3. **Given** I edit a menu item in the CMS, **When** I refresh the public site header, **Then** the navigation updates to reflect my changes.

---

### User Story 4 - DOI Registration Integration (Priority: P2)

As a System Admin, I need to ensure published articles automatically register DOIs so that the platform meets academic indexing standards.

**Why this priority**: Validates the integration of Feature 015 (DOI/OAI-PMH). It checks the async worker queue and database triggers.

**Independent Test**: Can be tested by triggering a publish event and checking the `doi_registrations` table. **Note**: The Crossref external API MUST be mocked at the service level (`CrossrefClient`) to avoid external dependencies during E2E runs.

**Acceptance Scenarios**:

1. **Given** a manuscript is newly published, **When** the background worker runs, **Then** a DOI registration XML is generated and sent to the (mocked) Crossref API.
2. **Given** a successful DOI registration, **When** I view the article public page, **Then** the DOI is displayed in the metadata section.
3. **Given** a simulated Crossref failure, **When** the worker retries, **Then** the system logs the error and increments the retry count in `doi_tasks`.

---

### User Story 5 - AI Matchmaker Integration (Priority: P3)

As an Editor, I need to see AI-suggested reviewers so that I can quickly find relevant experts.

**Why this priority**: Validates the integration of Feature 012 (AI Matchmaker). Checks if the Python backend's TF-IDF/ML service is correctly accessible from the frontend workflow.

**Independent Test**: Can be tested by opening the "Assign Reviewer" modal and verifying that the "Recommended" tab loads data.

**Acceptance Scenarios**:

1. **Given** I am assigning a reviewer to a manuscript, **When** I open the assignment modal, **Then** I see a list of reviewers with "Match Score" values.
2. **Given** the backend ML service is running, **When** I view the recommendations, **Then** the system does not return 500 errors or timeout.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support the complete "Author Submission Flow" (Register -> Login -> Submit -> Dashboard) without errors.
- **FR-002**: The system MUST support the complete "Editor Workflow" (Assign -> Review -> Decide -> Publish) without errors.
- **FR-003**: The system MUST persist CMS pages to the database and serve them at public URLs matching their slugs.
- **FR-004**: The system MUST automatically create a `doi_registration` record when a manuscript transitions to "Published" status.
- **FR-005**: The system MUST provide an Admin Dashboard view to monitor DOI registration status (Success/Pending/Failed).
- **FR-006**: The system MUST display AI-generated reviewer match scores in the assignment interface.
- **FR-007**: The E2E test suite MUST be able to run in a CI environment (headless mode) and locally (headed mode). It MUST use Chromium as the primary browser target.
- **FR-008**: The system MUST correctly handle database migrations from both Feature 013 and 015 without data loss or schema conflicts.
- **FR-009**: The system MUST display standardized error messages (toast notifications) for failed actions across all modules.
- **FR-010**: The test environment MUST support a "Clean State" mechanism to reset the database and seed reference data (users, journals) before the E2E suite executes.

### Key Entities

- **Manuscript**: The core entity flowing through the system.
- **User (Author/Editor/Reviewer)**: The actors performing actions in the E2E tests.
- **CMS Page**: Content entity managed by the new CMS module.
- **DOI Registration**: Entity linking a manuscript to its external DOI status.
- **Test Artifacts**: Screenshots, videos, and trace files generated by Playwright failures.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of defined Critical User Journeys (Author, Editor, CMS, DOI) pass in the automated Playwright suite.
- **SC-002**: The E2E test suite runs to completion in under 10 minutes (to ensure CI viability).
- **SC-003**: Zero "Critical" or "High" severity bugs remain in the integrated master branch.
- **SC-004**: Backend Unit/Integration test coverage for core services (DOI, CMS, Workflow) is >80%.
- **SC-005**: All UI pages are responsive and render without layout breakage on standard mobile and desktop viewports (verified via Chromium emulation).
