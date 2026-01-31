# Feature Specification: User Acceptance Testing (UAT) & Staging Environment Setup

**Feature Branch**: `019-uat-staging-setup`
**Created**: 2026-01-31
**Status**: Draft
**Input**: User description: "开启 Feature 019: 用户验收测试与预发布环境 (UAT & Staging Setup)..."

## Clarifications

### Session 2026-01-31

- Q: How should the reported UAT feedback be viewed and managed? → A: **Staging Admin Dashboard** - Add a "UAT Feedback" page to the Admin panel (Staging only) to list and view reports.
- Q: How should the database isolation be implemented? → A: **Separate Database** - Use a distinct database instance/name (e.g., `scholarflow_uat`) rather than just a schema, ensuring complete data safety.
- Q: Should the UAT banner be dismissible? → A: **No, Always Fixed** - The banner must remain visible at all times to prevent environment confusion.
- Q: How should the seed script handle existing data? → A: **Wipe and Re-seed** - The script must truncate target tables before inserting data to ensure a deterministic known state.
- Q: Should anonymous users (not logged in) be able to report feedback? → A: **Yes** - Allow anonymous reporting to capture issues like "Cannot Login".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Staging Environment Isolation (Priority: P1)

As a stakeholder (Editor, Investor) or Developer, I need a dedicated Staging environment that is visually distinct and data-isolated, so that I can safely test features without affecting production data or getting confused about which environment I am using.

**Why this priority**: Critical for safety and valid testing. Without isolation, UAT is dangerous. Without visual cues, data loss or confusion is likely.

**Independent Test**: Can be tested by configuring the environment variable `APP_ENV=staging`, verifying the banner appears, and confirming data operations do not appear in the production database.

**Acceptance Scenarios**:

1. **Given** the application is deployed with `APP_ENV=staging`, **When** any page is loaded, **Then** a fixed, **non-dismissible** banner at the bottom displays "Current Environment: UAT Staging (Not for Production)".
2. **Given** the application is deployed with `APP_ENV=production` (or default), **When** any page is loaded, **Then** the staging banner is NOT visible.
3. **Given** the application is configured for Staging, **When** data is created (e.g., a new submission), **Then** the data is persisted in the separate `scholarflow_uat` database, NOT the production database.

---

### User Story 2 - In-App Feedback Collection (Priority: P1)

As a UAT Tester, I want to report issues directly from the application interface with context (URL, severity), so that I don't have to switch tools or manually copy technical details.

**Why this priority**: Essential for capturing feedback efficiently during the UAT phase. Frictionless reporting increases the volume and quality of feedback.

**Independent Test**: Can be tested by clicking the feedback button in Staging, filling the form, and verifying the record exists in the **Admin UAT Feedback list**.

**Acceptance Scenarios**:

1. **Given** I am on any page in the Staging environment (even Login page), **When** I look at the bottom right corner, **Then** I see a floating "🐞 Report Issue" button.
2. **Given** I have opened the feedback dialog, **When** I enter a description, select "Critical" severity, and submit, **Then** the feedback is saved to the system with my current URL and I receive a success confirmation.
3. **Given** I am an Admin in the Staging environment, **When** I visit the "UAT Feedback" page in the Admin panel, **Then** I can see the report I just submitted.

---

### User Story 3 - Demo Data Seeding (Priority: P2)

As a Demo Presenter or Tester, I want to reset the system to a known state with specific edge-case data (e.g., overdue tasks), so that I can reliably demonstrate or test specific workflows without spending hours creating prerequisites manually.

**Why this priority**: Enables consistent testing of complex flows (like "overdue reviewer") that are time-dependent or require multi-step setup.

**Independent Test**: Can be tested by running the seed script and verifying the database contains **only** the specified scenarios (previous data cleared).

**Acceptance Scenarios**:

1. **Given** a staging database with random old data, **When** the demo seed script is executed, **Then** all old business data is cleared and the database is populated with:
    *   3 diverse pending manuscripts.
    *   1 reviewer with an overdue assignment.
    *   1 accepted manuscript pending payment.
2. **Given** the seeded data, **When** I log in as the Editor, **Then** I can immediately find and interact with these specific cases (e.g., send a reminder to the overdue reviewer).

---

### User Story 4 - UAT Playbook (Priority: P2)

As a non-technical stakeholder (Editor/Investor), I want a clear, step-by-step guide (Playbook) for testing the system, so that I verify the right business value without needing to understand the technical architecture.

**Why this priority**: Ensures UAT focuses on high-value business flows rather than random clicking, maximizing the value of the testing phase.

**Independent Test**: Can be verified by having a non-technical person successfully complete a scenario using only the document.

**Acceptance Scenarios**:

1. **Given** I am a business user, **When** I open `docs/UAT_SCENARIOS.md`, **Then** I see clear "Scenario A" and "Scenario B" guides using business language (not tech jargon).
2. **Given** I am following "Scenario A: Handle Academic Misconduct", **When** I perform the steps described, **Then** the system behaves exactly as described in the "Expected Result" section of the guide.

---

### Edge Cases

- What happens if the `scholarflow_uat` database is unreachable? System should fail to start or show a clear database error, rather than falling back to production DB silently.
- What happens if the feedback submission fails (e.g., network error)? User should see a retry option or a friendly error message.
- What happens if `APP_ENV` is set to an invalid value? System should default to Production behavior (secure default) or refuse to start.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support an environment variable `APP_ENV` to distinguish between `staging` and `production`.
- **FR-002**: System MUST display a fixed, **non-dismissible** visual banner on all pages when `APP_ENV=staging`, containing the text "Current Environment: UAT Staging (Not for Production)".
- **FR-003**: System MUST NOT include UAT-specific UI code (banner, feedback widget) in the production build bundle (ensure tree-shaking or conditional rendering that prevents leak).
- **FR-004**: System MUST provide a "Report Issue" floating button in Staging environment only, accessible to both logged-in and anonymous users.
- **FR-005**: System MUST provide a feedback dialog collecting: Description (text), Severity (Low/Medium/Critical), and automatically capturing the current URL.
- **FR-006**: Backend MUST provide an API endpoint to store user feedback in a `uat_feedback` table.
- **FR-007**: Seed script MUST first clear existing business data, then generate specific demo scenarios: 3 pending manuscripts, 1 overdue reviewer, 1 accepted/unpaid manuscript.
- **FR-008**: System MUST isolate Staging data from Production data via a **separate database instance** (e.g., `scholarflow_uat`) configured in Staging env.
- **FR-009**: System MUST provide a "UAT Feedback" list view in the Admin Panel (visible only in Staging environment) to view submitted reports.

### Key Entities

- **UAT Feedback**: Represents a reported issue. Attributes: Description, Severity, Page URL, User ID (**Optional**), Timestamp, Status (New/Triaged).
- **Demo Scenario**: A specific set of data states (e.g., "Overdue Review") generated by the seed script.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Non-technical users can submit a bug report via the widget in under 30 seconds.
- **SC-002**: 100% of feedback submissions in Staging are persisted to the `uat_feedback` table.
- **SC-003**: Production builds contain zero visible traces of the UAT banner or feedback widget code.
- **SC-004**: Seed script successfully resets and populates the 5 required demo entities in under 10 seconds.
- **SC-005**: UAT Playbook covers at least 2 distinct critical business flows (e.g., misconduct handling, finance approval).
