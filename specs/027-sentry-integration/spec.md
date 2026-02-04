# Feature Specification: Sentry Integration

**Feature Branch**: `027-sentry-integration`  
**Created**: 2026-02-03  
**Status**: Draft  
**Input**: User description: "开启 Feature 027: 全栈异常监控集成 (Sentry Integration)..."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Proactive Error Identification (Priority: P1)

As an Administrator, I want to be automatically notified of runtime errors in the UAT and production environments, so that I can fix bugs before users report them.

**Why this priority**: Essential for maintaining system stability during UAT and providing high-quality support.

**Independent Test**: Trigger a known error (e.g., a dummy "test error" button or endpoint) and verify it appears in the Sentry dashboard with full stack traces and session replay.

**Acceptance Scenarios**:

1. **Given** the system is running, **When** a frontend runtime exception occurs, **Then** Sentry captures the error and records the user session for playback.
2. **Given** the system is running, **When** a backend API or database error occurs, **Then** Sentry captures the error with relevant transaction traces.
3. **Given** an error is reported in Sentry, **When** I view the issue, **Then** I see the original source code lines (via Source Maps) rather than minified code.

---

### User Story 2 - Resilient System Startup (Priority: P1)

As a Developer, I want the system to start normally even if the Sentry service is unavailable or misconfigured, so that monitoring does not become a single point of failure.

**Why this priority**: Fundamental reliability requirement ("Zero-crash principle").

**Independent Test**: Set an invalid Sentry DSN or disconnect network during startup and verify that the application still boots successfully and serves requests.

**Acceptance Scenarios**:

1. **Given** an invalid Sentry configuration, **When** the backend starts up, **Then** the system logs a warning but continues to initialize other services and starts the web server.
2. **Given** a network failure during frontend initialization, **When** a user loads the page, **Then** the application remains functional even if monitoring is inactive.

---

### User Story 3 - Privacy Protection (Priority: P2)

As a User, I want my sensitive information (passwords, manuscript content) to be excluded from monitoring logs, so that my data remains private and compliant with security standards.

**Why this priority**: Critical for security and data privacy compliance.

**Independent Test**: Perform a login and upload a manuscript, then verify in Sentry that password fields are masked and PDF contents are not transmitted as part of the error context.

**Acceptance Scenarios**:

1. **Given** a login attempt with an error, **When** Sentry captures the event, **Then** the `password` field in the request body is scrubbed or masked.
2. **Given** a manuscript processing error, **When** Sentry logs the event, **Then** no raw PDF bytes or sensitive document content is included in the attachment or context.

---

### Edge Cases

- **Quota Exhaustion**: How does the system behave when the Sentry event quota is reached? (Assumption: Sentry SDK handles this gracefully; system continues to run without reporting).
- **Offline Mode**: If the user's browser is behind a strict firewall blocking Sentry, the application must still work perfectly.
- **SSR vs. Client Errors**: Both Server-Side Rendering (SSR) errors and client-side browser errors must be captured.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST integrate Sentry monitoring for both Frontend (Next.js) and Backend (FastAPI).
- **FR-002**: Frontend MUST capture 100% of session replays (`replaysSessionSampleRate: 1.0`) and 100% of performance traces (`tracesSampleRate: 1.0`) during the UAT/development phase.
- **FR-003**: Frontend MUST automatically upload Source Maps to Sentry during the build process to enable un-minified stack traces.
- **FR-004**: Backend MUST initialize Sentry at startup in `main.py` with support for `SqlalchemyIntegration` to monitor database-related errors.
- **FR-005**: System MUST implement a "Zero-crash" initialization: Sentry setup failures MUST NOT prevent the application from starting or functioning.
- **FR-006**: System MUST explicitly filter/scrub sensitive data, specifically `password` fields and PDF binary content, from all outgoing Sentry events.
- **FR-007**: System MUST provide environment-aware reporting (e.g., tagging events with `environment: uat` or `environment: production`).

### Key Entities

- **Monitoring Context**: Includes metadata like environment, user ID (non-sensitive), release version, and tags.
- **Sentry Event**: The data packet containing error details, traces, and replays.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of unhandled exceptions in the application are successfully reported to Sentry.
- **SC-002**: 0% of application startup failures are caused by Sentry initialization errors.
- **SC-003**: Frontend stack traces in Sentry consistently point to actual `.ts`/`.tsx` source files and line numbers.
- **SC-004**: Verification confirms that no clear-text passwords or PDF contents are found in the Sentry issue dashboard after 100 test events.
- **SC-005**: Session replays are available for 100% of reported frontend errors during the UAT period.