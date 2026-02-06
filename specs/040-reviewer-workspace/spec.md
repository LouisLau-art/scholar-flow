# Feature Specification: Reviewer Workspace

**Feature Branch**: `040-reviewer-workspace`
**Created**: 2026-02-06
**Status**: Draft
**Input**: Feature 040 - Reviewer Workspace. Immersive layout, PDF preview (left), Dual comments (Author/Editor) (right), Decision submission, Security isolation.

## Clarifications

### Session 2026-02-06

- **Q: How should Review Attachments be handled?** → **A: Add attachment upload support to the review form.**
  *(Rationale: Reviewers frequently need to attach annotated PDFs or supplementary files. Adding this now avoids a gap in the review process.)*

- **Q: What is the post-submission access policy?** → **A: Read-only access to their own report.**
  *(Rationale: Reviewers should be able to see what they submitted for reference, but preventing edits ensures data integrity after the decision point.)*

- **Q: How should the UI respond to small screens/mobile?** → **A: Stack layout (PDF hidden or toggleable), Form visible.**
  *(Rationale: While Desktop is P1, a completely broken mobile view is unacceptable. Stacking ensures the form is at least accessible if needed urgent access on mobile.)*

- **Q: What is the behavior for "Warn on Exit" (FR-004 MVP)?** → **A: Browser `beforeunload` event + Form dirty state tracking.**
  *(Rationale: Standard, reliable web pattern for preventing data loss without the complexity of auto-save APIs for MVP.)*

- **Q: Should the "Minimal Header" include any navigation?** → **A: Only "Back to Dashboard" (if logged in) or "Logout/Exit".**
  *(Rationale: Keeps focus on the task while providing a safe exit route.)*

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Immersive Manuscript Viewing (Priority: P1)

As a Reviewer, I want to view the manuscript PDF and review tools side-by-side in a distraction-free interface, so that I can focus entirely on the evaluation without navigating between tabs or windows.

**Independent Test**:
1. Authenticate as a reviewer (via Magic Link or Login).
2. Navigate to the Review Workspace for an assigned manuscript.
3. Verify the global navigation bar and sidebar are hidden.
4. Verify the page is split into a PDF viewer (left) and Action Panel (right).
5. Verify the PDF loads and is readable.
6. **(Clarification)** On mobile, verify layout stacks or toggles PDF visibility.

**Acceptance Scenarios**:
1. **Given** a valid reviewer session, **When** accessing the workspace, **Then** the standard site header/footer are replaced by a minimal reviewer header (showing only Exit/Back).
2. **Given** a manuscript PDF, **When** the page loads, **Then** the PDF is rendered in the left pane (using iframe/PDF.js).

---

### User Story 2 - Dual-Channel Feedback (Priority: P1)

As a Reviewer, I want to provide separate comments for the authors and the editors, so that I can provide constructive feedback to the author while privately flagging sensitive issues (e.g., plagiarism, conflicts) to the editor.

**Independent Test**:
1. Open the Action Panel (right pane).
2. Type text into "Comments for Author".
3. Type text into "Confidential Comments to Editor".
4. **(Clarification)** Upload an attachment (e.g. annotated PDF).
5. Submit the review.
6. Verify in the database (or Editor View) that both fields and attachments are saved correctly.

**Acceptance Scenarios**:
1. **Given** the review form, **When** entering text, **Then** the system accepts distinct input for both channels.
2. **Given** a submitted review, **When** an Author views the feedback, **Then** they ONLY see the "Comments for Author" content.
3. **Given** a submitted review, **When** an Editor views the feedback, **Then** they see BOTH fields.

---

### User Story 3 - Decision Submission (Priority: P1)

As a Reviewer, I want to select a structured recommendation (Accept, Revision, Reject) and submit my review, so that the editor can proceed with the workflow.

**Independent Test**:
1. Fill in required comments.
2. Select a decision (e.g., "Minor Revision") from the dropdown/radio options.
3. Click "Submit Review".
4. Verify the `review_reports` status changes to `submitted`.
5. Verify the user is redirected to a confirmation page.
6. **(Clarification)** Navigate back to the assignment; verify view is Read-Only.

**Acceptance Scenarios**:
1. **Given** an incomplete form (missing mandatory comments), **When** clicking Submit, **Then** validation errors are shown.
2. **Given** a successful submission, **When** the process completes, **Then** the reviewer access switches to read-only mode.
3. **Given** a dirty form (unsaved changes), **When** attempting to close the tab, **Then** a browser warning appears.

---

### User Story 4 - Security & Isolation (Priority: P0)

As a System Admin, I want to ensure the workspace strictly enforces access control based on the active session token, so that reviewers cannot access manuscripts they are not assigned to.

**Independent Test**:
1. Obtain a valid magic link/session for Manuscript A.
2. Attempt to manually change the URL ID to Manuscript B.
3. Verify the system returns a 403 Forbidden or 404 Not Found.

**Acceptance Scenarios**:
1. **Given** a Guest Session for Assignment X, **When** requesting data for Assignment Y, **Then** the API denies access.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Workspace MUST use a dedicated layout that excludes the main application shell, showing only a minimal header with "Exit/Back" action.
- **FR-002**: The system MUST render the manuscript PDF in the browser (Left Column) without requiring an external download step for viewing.
- **FR-003**: The right column MUST contain a form with:
    - `comments_for_author` (Text/Markdown)
    - `confidential_comments_to_editor` (Text/Markdown)
    - `recommendation` (Enum: `accept`, `minor_revision`, `major_revision`, `reject`)
    - **(Clarification)** `attachments` (File Upload, e.g., annotated PDF)
- **FR-004**: The system MUST implement "Warn on Exit" using browser `beforeunload` events when the form is dirty.
- **FR-005**: Submission MUST trigger a status transition of the `review_assignment` to `completed`.
- **FR-006**: The page MUST validte the `assignment_id` against the current user's session (Guest or Authenticated).
- **FR-007**: Upon submission, the interface MUST become Read-Only for that assignment.

### Key Entities

- **ReviewReport**: Stores the feedback content, decision, and attachments.
- **ReviewAssignment**: Links the reviewer to the manuscript and tracks status.
- **Manuscript**: Source of the PDF.

### Assumptions & Dependencies

- **Feature 039** is complete (Magic Link provides the valid session/cookie).
- **PDF Storage**: Files are stored in Supabase Storage and accessible via Signed URL (backend generated).
- **Mobile Support**: MVP uses a stacked layout (PDF toggleable) rather than side-by-side.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Workspace loads (Time to Interactive) in under 2 seconds on standard broadband.
- **SC-002**: 100% of submitted reviews correctly separate "Author" vs "Editor" comments in the database.
- **SC-003**: Unauthorized access attempts (ID modification) are blocked 100% of the time.
- **SC-004**: Reviewer can complete the "Read -> Comment -> Attach -> Submit" flow without leaving the page.
