# Feature Specification: Core Logic Hardening (Financial Gate & Reviewer Privacy)

**Feature Branch**: `022-core-logic-hardening`
**Created**: 2026-02-02
**Status**: Draft
**Input**: Feature 022: Implement Financial Gate, APC Confirmation, Dual Review Comments, and Privacy Controls.

## Clarifications

### Session 2026-02-02
- Q: Who can see the reviewer's uploaded attachment? → A: **Confidential (Editor Only)**. Given the "Reviewer Privacy" goal and single attachment slot, it is restricted to the Editor to prevent accidental leakage.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reviewer Submits Dual-Channel Feedback (Priority: P1)

As a Reviewer, I want to provide separate comments for the author and the editor, so I can be constructive to the author while being candid with the editor.

**Why this priority**: Addresses critical privacy and functionality gaps in the review process.

**Independent Test**: Can be tested by submitting a review as a Reviewer and verifying the data persistence and visibility permissions.

**Acceptance Scenarios**:

1. **Given** a Reviewer is on the review submission page, **When** they view the form, **Then** they see two distinct text areas: "Comments to Author" (required) and "Confidential Comments to Editor" (optional, marked as confidential).
2. **Given** a Reviewer has a marked-up PDF, **When** they upload it via the new attachment field, **Then** the file is successfully uploaded and linked to the review report as a **confidential attachment**.
3. **Given** a submitted review with confidential comments and an attachment, **When** the Author views the review feedback, **Then** they see ONLY the "Comments to Author" and CANNOT access the confidential comments or the attachment.

### User Story 2 - Editor Sets APC and Faces Financial Gate (Priority: P1)

As an Editor, I want to confirm the Article Processing Charge (APC) upon acceptance and be prevented from publishing until payment is received, ensuring financial compliance.

**Why this priority**: Fixes a critical security/business loophole ("The Financial Gate").

**Independent Test**: Can be tested by accepting a manuscript, setting APC, trying to publish immediately (fail), and trying to publish after payment (success).

**Acceptance Scenarios**:

1. **Given** an Editor is accepting a manuscript, **When** they click "Accept", **Then** a "Confirm APC" dialog appears allowing them to modify the default amount.
2. **Given** an APC amount is confirmed, **When** the decision is finalized, **Then** an Invoice record is created or updated with status 'unpaid'.
3. **Given** a manuscript with an 'unpaid' invoice (and amount > 0), **When** the Editor views the dashboard, **Then** the "Publish" button is disabled (greyed out) with a tooltip "Waiting for Payment".
4. **Given** a manuscript with an 'unpaid' invoice, **When** an API call to `publish_manuscript` is made, **Then** the system throws a 403 "Payment Required" error.
5. **Given** the invoice status updates to 'paid', **When** the Editor views the dashboard, **Then** the "Publish" button is enabled.

---

### Edge Cases

- **Zero APC**: If Editor sets APC to 0, the Financial Gate should allow publishing (Invoice status might be 'paid' or 'waived', or check `amount > 0`).
- **Data Leakage**: Attempting to fetch `review_reports` via API as an Author must sanitize the response payload.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support two distinct comment fields for reviews: `comments` (for Author) and `confidential_comments_to_editor`.
- **FR-002**: System MUST allow Reviewers to upload a file attachment (e.g., annotated PDF) with their review.
- **FR-003**: API responses for Authors MUST EXCLUDE `confidential_comments_to_editor` and the `attachment_path` (file is confidential to Editor).
- **FR-004**: Editor's "Accept" workflow MUST include a mandatory step to confirm or modify the APC amount.
- **FR-005**: System MUST create or update the confirmed APC amount in an `invoices` table linked to the manuscript.
- **FR-006**: The `publish_manuscript` backend endpoint MUST query the `invoices` table before execution.
- **FR-007**: The `publish_manuscript` endpoint MUST return 403 Forbidden if `invoice.status != 'paid'` AND `invoice.amount > 0`.
- **FR-008**: The payment check logic in code MUST be annotated with `# CRITICAL: PAYMENT GATE CHECK`.
- **FR-009**: The Editor Dashboard MUST visually disable the "Publish" action for unpaid manuscripts.

### Key Entities

- **ReviewReport**: Updated with `confidential_comments_to_editor` (text), `attachment_path` (text).
- **Invoice**: Accessed during publication check.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of publication attempts for unpaid manuscripts (with APC > 0) are rejected by the backend.
- **SC-002**: API tests verify that `confidential_comments_to_editor` and attachments are never returned to a user with 'Author' role.
- **SC-003**: Editors can successfully modify the default APC amount during the acceptance flow.
