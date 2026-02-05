# Feature Specification: Enhance Manuscripts Process List with Filters and Actions

**Feature Branch**: `032-enhance-process-list`  
**Created**: 2026-02-04  
**Status**: Draft  
**Input**: User description: "先做 Feature 032 (列表页筛选与快捷操作增强)"

## User Scenarios & Testing *(mandatory)*

## Clarifications

### Session 2026-02-04
- Q: Should Quick Actions be buttons or a menu? → A: Icon Buttons (Maximizes efficiency and utilizes the new 1600px layout).

### User Story 1 - Advanced Filtering (Priority: P1)

As an Editor, I want to filter the manuscripts list by Journal, Status, Editor, and Manuscript ID (search), so that I can quickly locate specific subsets of papers for batch processing or review.

**Why this priority**: Essential for managing large volumes of submissions (PDF P2 requirement).

**Independent Test**: Navigate to `/editor/process`, select a specific journal and status from the dropdowns, and verify that the table only displays matching rows.

**Acceptance Scenarios**:

1. **Given** the process list page, **When** I select "Journal A" from the Journal dropdown, **Then** the list updates to show only manuscripts submitted to Journal A.
2. **Given** the process list page, **When** I select multiple statuses (e.g., "Under Review", "Pending Decision"), **Then** the list shows manuscripts in either of those states.
3. **Given** the process list page, **When** I type a partial Manuscript ID in the search box, **Then** the list filters in real-time or upon enter.

---

### User Story 2 - Quick Actions (Priority: P1)

As an Editor, I want direct access to common actions (Pre-check, APC Confirm, MS Owner Binding) right from the table row, so that I don't have to open the details page for every routine administrative task.

**Why this priority**: Improves operational efficiency (PDF P5 requirement).

**Independent Test**: Locate a manuscript in "Pre-check" status on the list, click the "Pre-check" action button, and complete the quick-pass workflow without leaving the list context (or via a quick modal).

**Acceptance Scenarios**:

1. **Given** a manuscript in `Pre-check` status, **When** I hover over the row actions, **Then** I see a "Pre-check" button.
2. **Given** a manuscript row, **When** I click "MS Owner", **Then** a popover allows me to bind an internal owner.
3. **Given** a manuscript with pending APC, **When** I click "APC Confirm", **Then** a modal allows me to mark it as paid.

---

### User Story 3 - Precision Timing (Priority: P2)

As an Editor, I want to see submission and update timestamps accurate to the minute, so that I can track SLA and turnaround times effectively.

**Why this priority**: PDF P2 explicitly requests "精确到小时和分钟".

**Independent Test**: View the "Submitted Time" and "Updated Time" columns and verify the format follows `YYYY-MM-DD HH:mm`.

**Acceptance Scenarios**:

1. **Given** the manuscript list, **When** I look at the time columns, **Then** the dates are formatted as `2023-10-25 14:30` (24h format).

---

### Edge Cases

- **No Results**: What happens if filters result in zero matches? (Assumption: Show a clear "No manuscripts found" empty state).
- **Concurrent Updates**: What if I try to "Quick Action" a manuscript that another editor just modified? (Assumption: Optimistic UI with error rollback if backend rejects due to version mismatch).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a multi-select filter for `Status` and single-select filters for `Journal` and `Assigned Editor` on the `/editor/process` page.
- **FR-002**: System MUST provide a text search input for `Manuscript ID` and `Title`.
- **FR-003**: The manuscripts table MUST include a "Quick Actions" column containing direct **Icon Buttons** for: `Pre-check` (if applicable), `APC Confirm`, and `MS Owner`.
- **FR-004**: The `Submitted Time` and `Updated Time` columns MUST display timestamps in `YYYY-MM-DD HH:mm` format.
- **FR-005**: Filters MUST be persistent in the URL query parameters (e.g., `?status=under_review&journal=1`) to allow bookmarking.
- **FR-006**: The "Pre-check" quick action MUST open a modal to approve (move to `Under Review`) or reject/revision (move to `Rejected` or `Revision`).

### Key Entities

- **Manuscript**: Filtered by `status`, `journal_id`, `editor_id`, `owner_id`.
- **User Profile**: Used for Editor/Owner filtering options.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Editors can locate a specific manuscript by ID in under 2 seconds.
- **SC-002**: Performing a "Pre-check" approval takes less than 3 clicks from the list view.
- **SC-003**: 100% of timestamps in the table are displayed with minute-level precision.