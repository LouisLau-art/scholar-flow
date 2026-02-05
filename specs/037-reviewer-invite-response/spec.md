# Feature Specification: Reviewer Invitation Response & Timeline

**Feature Branch**: `037-reviewer-invite-response`  
**Created**: 2026-02-05  
**Status**: Draft  
**Input**: User description: "Feature 037: 审稿邀请接受/拒绝 + 截止时间选择 + 全流程时间戳（invited/opened/accepted/declined/submitted）"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Reviewer can accept/decline an invitation with a due date (Priority: P1)

As a Reviewer, I can open an invitation link, preview the manuscript, and clearly choose **Accept** or **Decline**.
If I accept, I can select a due date within an allowed window so the editorial team can manage timelines.
If I decline, I can provide a decline reason so the team can improve future matching and quickly move on.

**Why this priority**: This unblocks the real-world review workflow. Without an explicit Accept/Decline step and a due date, the system cannot reliably manage reviewer commitments, reminders, or editorial expectations.

**Independent Test**: Create a single review invitation, open it as the reviewer, accept with a due date (or decline with a reason), and verify the invitation status and timeline updates are visible to the editor.

**Acceptance Scenarios**:

1. **Given** a reviewer has a valid invitation link, **When** they open it, **Then** they can preview the manuscript and see clear Accept/Decline actions.
2. **Given** the reviewer clicks **Accept**, **When** they pick a due date within the allowed window and confirm, **Then** the system records the acceptance and due date, and the reviewer can proceed to submit a review.
3. **Given** the reviewer clicks **Decline**, **When** they select a decline reason (and optional note) and confirm, **Then** the system records the decline and prevents review submission for that invitation.
4. **Given** the reviewer tries to set a due date outside the allowed window, **When** they confirm, **Then** the system rejects the selection with a clear message and keeps the invitation unaccepted.

---

### User Story 2 - Editor sees invitation timeline and reviewer commitment status (Priority: P2)

As an Editor, I can see each invited reviewer's current commitment state and key timestamps (invited/opened/accepted/declined/submitted), so I can decide whether to wait, follow up, or invite someone else.

**Why this priority**: Editors need operational visibility. A simple status count is not enough in UAT; timeline visibility reduces confusion and prevents duplicated assignments.

**Independent Test**: For a manuscript with at least one invitation, change the invitation state via User Story 1 and verify the editor UI shows the updated status, due date, and timestamps.

**Acceptance Scenarios**:

1. **Given** an editor views a manuscript detail page, **When** there are reviewer invitations, **Then** the editor can see each reviewer with a single, unambiguous current state and key timestamps.
2. **Given** a reviewer accepts or declines, **When** the editor refreshes the manuscript detail, **Then** the timeline reflects the change without duplicate reviewer counts.
3. **Given** a reviewer accepted with a due date, **When** the due date is approaching or passes, **Then** the editor can clearly see it is due/overdue (visual emphasis).

---

### User Story 3 - Invitation link safety and idempotent actions (Priority: P3)

As a Reviewer, I should never end up in a confusing or broken state if I click the same invitation multiple times, or if the invitation has already been accepted/declined/submitted.

**Why this priority**: In real usage, links are re-opened, forwarded, or clicked from multiple devices. The system must behave safely and predictably to reduce support burden during UAT.

**Independent Test**: Use a single invitation link and repeat Accept/Decline actions; verify the system does not create duplicates and always shows the current state.

**Acceptance Scenarios**:

1. **Given** an invitation is already accepted, **When** the reviewer re-opens the link, **Then** the page shows the accepted state and does not allow re-accepting with a second commitment.
2. **Given** an invitation is already declined, **When** the reviewer re-opens the link, **Then** the page shows the declined state and does not allow submitting a review.
3. **Given** a review is already submitted for the invitation, **When** the reviewer re-opens the link, **Then** the page clearly indicates the review is complete.

---

### Edge Cases
- **Expired or invalid link**: Reviewer sees a friendly message and cannot access manuscript content.
- **Timezone ambiguity**: Due dates are displayed consistently (date + time and timezone label) to both reviewers and editors.
- **Re-invitation**: If an editor invites the same person again, the system avoids “double counting” and clarifies which invitation is active.
- **Concurrent actions**: If the reviewer clicks Accept twice quickly, the system records a single acceptance (idempotent behavior).

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST provide a reviewer-facing invitation page that supports Accept and Decline actions for a specific invitation.
- **FR-002**: System MUST allow reviewers to preview the manuscript before choosing Accept/Decline.
- **FR-003**: If a reviewer accepts, the system MUST require selecting a due date within an allowed window (default window: 7–10 days from acceptance) and record it.
- **FR-004**: If a reviewer declines, the system MUST require a decline reason from a predefined list and allow an optional free-text note.
- **FR-005**: System MUST persist invitation lifecycle timestamps at least for: invited, opened, accepted, declined, review_submitted.
- **FR-006**: System MUST expose the invitation lifecycle state and timestamps to authorized editors in the manuscript detail view.
- **FR-007**: The system MUST prevent duplicate commitments and duplicate reviewer counts (idempotent Accept/Decline, no double assignment for the same invitation).
- **FR-008**: The system MUST ensure that invitation links do not leak manuscript content to unauthorized users (invalid/expired link yields no content).
- **FR-009**: The system MUST support a configurable allowed due-date window, with a safe default if not configured.
- **FR-010**: The system MUST log invitation state transitions for audit/debugging (who/when/what changed).

### Key Entities *(include if feature involves data)*

- **Review Invitation**: A time-bounded invitation that links a reviewer to a manuscript review request (state, timestamps, due date).
- **Invitation Timeline**: The ordered set of key timestamps that explain what happened and when (invited/opened/accepted/declined/submitted).
- **Decline Reason**: A structured classification of why a reviewer declined (plus optional note).

### Assumptions & Dependencies

- The system already has a way to create reviewer invitations for a manuscript and to identify the invited reviewer when they open the link.
- Editors are internal roles allowed to view reviewer invitation states and timelines for manuscripts they can access.
- The reviewer review submission form exists; acceptance is a prerequisite to submitting a review (unless explicitly bypassed by internal staff for support/debug).

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: Reviewers can accept or decline an invitation in under 60 seconds (median) on a standard desktop browser.
- **SC-002**: 95%+ of Accept actions result in a valid due date stored within the allowed window (no invalid dates persisted).
- **SC-003**: Editors can see each reviewer’s current invitation state and timeline within 5 seconds of page load (p95) during UAT.
- **SC-004**: Reduce duplicate reviewer assignment incidents (same reviewer counted twice for the same manuscript) to near zero in UAT.
