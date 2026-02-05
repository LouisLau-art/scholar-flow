# Feature Specification: Pre-check Role Workflow (ME → AE → EIC)

**Feature Branch**: `038-precheck-role-workflow`  
**Created**: 2026-02-05  
**Status**: Draft  
**Input**: User description: "Feature 038: Pre-check 角色工作流（ME 分配 AE → AE 技术质检 → EIC 学术初审）+ 可视化待办与时间戳"

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

### User Story 1 - Managing Editor assigns a manuscript to an Assistant Editor (Priority: P1)

As a Managing Editor (ME), I can see newly submitted manuscripts that need pre-check, and assign each manuscript to a specific Assistant Editor (AE). This establishes clear ownership for operational follow-up.

**Why this priority**: Without assignment, pre-check work is ambiguous and falls through the cracks. Assignment is the first step to making the workflow operational and measurable.

**Independent Test**: Create a newly submitted manuscript, open ME pre-check view, assign it to AE A, refresh, and verify AE A sees it in their queue while other AEs do not.

**Acceptance Scenarios**:

1. **Given** a manuscript is newly submitted and unassigned, **When** an ME assigns it to an AE, **Then** the system records the assignment and the AE becomes the operational owner for pre-check actions.
2. **Given** a manuscript is already assigned, **When** an ME reassigns it to a different AE, **Then** the system updates the assignment and keeps an audit trail of the change.

---

### User Story 2 - Assistant Editor completes technical pre-check and moves forward (Priority: P2)

As an Assistant Editor (AE), I can perform a technical pre-check (format/QC) and choose a next step:
- Send to academic pre-check (EIC) if acceptable, or
- Request revision from author, or
- Reject the manuscript (when allowed by policy).

**Why this priority**: This is the core of “administrative vs academic separation”. AE runs the operational checks so the academic editor focuses only on academic merit.

**Independent Test**: With a manuscript assigned to AE, AE performs a pre-check decision and verifies that the manuscript leaves the AE queue and appears in the correct next queue/state.

**Acceptance Scenarios**:

1. **Given** a manuscript is assigned to AE, **When** AE marks “Technical QC Passed” and forwards to academic pre-check, **Then** the manuscript becomes visible in the EIC queue for academic pre-check.
2. **Given** a manuscript fails technical QC, **When** AE requests author revision, **Then** the manuscript becomes visible to the author with a clear request reason and the AE/EIC queues reflect that it is waiting for the author.
3. **Given** a manuscript is clearly unsuitable on non-academic grounds (e.g., missing required materials), **When** AE rejects (if permitted), **Then** the manuscript is marked rejected and no longer appears in active editorial queues.

---

### User Story 3 - Editor-in-Chief performs academic pre-check with final authority for entry to peer review (Priority: P3)

As an Editor-in-Chief (EIC) / academic editor, I can review the manuscript after AE technical QC and make an academic pre-check decision:
- Pass to peer review, or
- Reject, or
- Request revision before external review.

**Why this priority**: The business workflow requires that academic authority is explicit and auditable. This prevents AEs from making academic decisions and aligns with real publishing operations.

**Independent Test**: With a manuscript in EIC pre-check queue, EIC makes a decision and verifies the manuscript transitions into the expected next stage (e.g., ready for reviewer assignment).

**Acceptance Scenarios**:

1. **Given** a manuscript is awaiting academic pre-check, **When** EIC passes it, **Then** it becomes eligible for reviewer invitation and appears in the appropriate “under review / reviewer assignment” workflow.
2. **Given** a manuscript is awaiting academic pre-check, **When** EIC requests revision, **Then** the author is notified and the manuscript is tracked as waiting for author response.
3. **Given** a manuscript is awaiting academic pre-check, **When** EIC rejects it, **Then** it is removed from active queues and the rejection is logged with a reason.

---

### Edge Cases

- **Unassigned manuscript**: AEs cannot act on a manuscript until ME assigns it; system should show a clear “Awaiting assignment” state to ME.
- **Role misuse**: A non-ME cannot assign AEs; a non-EIC cannot perform academic pre-check decisions.
- **Reassignment mid-work**: If reassigned, the new AE sees the full context (notes/files/decisions so far), and the old AE no longer sees it in their action queue.
- **Multiple journals**: If journals exist, assignment and queues must respect journal scope (ME/EIC of Journal A should not manage Journal B).

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: The system MUST support assigning each manuscript in pre-check to a single AE, and allow ME to change that assignment.
- **FR-002**: The system MUST provide role-specific queues/views for ME (assignment), AE (technical QC), and EIC (academic pre-check).
- **FR-003**: The system MUST enforce role permissions so only ME can assign AEs and only EIC can complete academic pre-check decisions.
- **FR-004**: The system MUST record key timestamps for pre-check workflow steps (assignment, QC pass/fail decision, academic pre-check decision).
- **FR-005**: The system MUST keep a clear audit trail for assignment changes and decisions (who, when, what changed, and optional reason).
- **FR-006**: The system MUST ensure manuscript state reflects the workflow so downstream steps (reviewer invitation, author revision) receive consistent inputs.
- **FR-007**: The system MUST prevent “silent state changes” (users must see confirmation that their action succeeded and what changed).
- **FR-008**: The system MUST support optional internal notes during pre-check that are visible to internal staff but not to authors/reviewers.

### Key Entities *(include if feature involves data)*

- **Pre-check Assignment**: The relationship that records which AE is responsible for a manuscript’s technical QC.
- **Pre-check Decision**: A structured record of a QC decision (pass/revision/reject) with reason and timestamp.
- **Academic Pre-check Decision**: A structured record of EIC decision (pass/revision/reject) with reason and timestamp.

### Assumptions & Dependencies

- The system already has “submitted” manuscripts and an editor-facing workflow dashboard.
- Roles ME/AE/EIC exist conceptually; if they are not yet explicitly modeled, the feature will define and enforce them as part of the workflow.
- Existing downstream workflows (reviewer assignment, revision requests) can be triggered once pre-check decisions are made.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: ME can assign an AE to a manuscript in under 30 seconds (median) during UAT.
- **SC-002**: 95%+ of pre-check actions produce an audit entry with actor + timestamp (no “who changed it” ambiguity).
- **SC-003**: AEs can process and forward a manuscript to EIC academic pre-check in under 5 minutes for the happy path (excluding reading the manuscript).
- **SC-004**: EIC can complete an academic pre-check decision after opening the manuscript detail without needing to contact AE for missing context (measured by reduced “where is the info” feedback in UAT).
