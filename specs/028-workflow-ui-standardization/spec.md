# Feature Specification: Workflow and UI Standardization

**Feature Branch**: `028-workflow-ui-standardization`  
**Created**: 2026-02-04  
**Status**: Draft  
**Input**: User description: "根据《期刊系统整理20260204.pdf》的要求，全面重写稿件处理状态机、优化 Manuscripts Process 表格视图、补齐出版前流水线、并细化审稿人管理逻辑。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Centralized Manuscript Processing (Priority: P1)

As an Editor, I want a unified, sortable, and filterable table view of all manuscripts (Manuscripts Process), so that I can efficiently manage the lifecycle of papers across different journals.

**Why this priority**: Core operational efficiency. Replaces the current fragmented card-based view with a professional management interface.

**Independent Test**: Navigate to the "Manuscripts Process" page, apply a "Journal" filter, and verify the table correctly displays matching manuscripts with high-precision timestamps (YYYY-MM-DD HH:mm).

**Acceptance Scenarios**:

1. **Given** multiple manuscripts in the system, **When** I view the "Manuscripts Process" page, **Then** I see a table with columns: Manuscript ID, Submitted Time, Current Status, Updated Time, and Assign Editor.
2. **Given** the process table, **When** I click a Manuscript ID, **Then** I am redirected to a dedicated details page for that manuscript.
3. **Given** the filter bar, **When** I select a specific Journal and click "Search", **Then** the table updates to show only manuscripts belonging to that journal.

---

### User Story 2 - Comprehensive Lifecycle Management (Priority: P1)

As an Editor, I want the manuscript status machine to follow the standard 12-stage workflow (Pre-check to Published), so that the system accurately reflects the academic publishing process.

**Why this priority**: Structural integrity. Ensures the system covers all necessary steps including post-acceptance activities like layout and proofreading.

**Independent Test**: Advance a manuscript from `Accepted` through `Layout`, `English Editing`, and `Proofreading`, verifying that each state is reachable and correctly logged.

**Acceptance Scenarios**:

1. **Given** an accepted manuscript, **When** the layout phase is initiated, **Then** the status changes to `Layout`.
2. **Given** a manuscript in `Layout`, **When** layout is complete, **Then** it can be moved to `English Editing` or `Proofreading`.
3. **Given** a manuscript in any stage, **When** the status is updated, **Then** the "Updated Time" in the process table reflects the change precisely.

---

### User Story 3 - Refined Reviewer and Owner Management (Priority: P2)

As an Editor, I want to manage a library of reviewers and bind internal owners independently, so that reviewer recruitment and KPI tracking are decoupled and more detailed.

**Why this priority**: Operational compliance and data quality. Addresses the specific request to decouple owner binding from reviewer assignment.

**Independent Test**: Add a new reviewer to the library with full details (Title, Institution, Interests) without sending an invitation, then bind an internal owner to a manuscript separately.

**Acceptance Scenarios**:

1. **Given** the "Add Reviewer" modal, **When** I enter Name, Title, Email, Institution, and Interests and click "Add", **Then** the reviewer is saved to the database but NO invitation email is sent yet.
2. **Given** a manuscript in `Pre-check`, **When** I use the dedicated "Binding Owner" feature, **Then** the Internal Owner is saved and displayed in the process table.

---

### Edge Cases

- **Mixed Status Transitions**: What happens if an editor tries to skip a post-acceptance stage (e.g., skip Layout)? (Assumption: System should allow flexible flow for admins but suggest the standard sequence).
- **Timezone Drift**: How are "精确到小时和分钟" timestamps handled for international editors? (Requirement: All times MUST be stored in UTC and displayed in the user's local timezone or a configured system timezone).
- **Missing Invoice Info**: What happens if an invoice is generated without full metadata? (Requirement: System MUST allow editing `Invoice Info` fields like APC amount and Funding before finalized generation).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement a 12-stage status machine: `Pre-check`, `Under Review`, `Revision` (with Major/Minor flag), `Resubmitted`, `Decision`, `Decision Done`, `Accepted`, `Layout`, `English Editing`, `Proofreading`, `Published`, `Rejected`.
- **FR-002**: The "Pipeline" page MUST be renamed to "Manuscripts Process" and converted to a responsive table layout.
- **FR-003**: The process table MUST include sortable columns for `Manuscript ID`, `Submitted Time` (YYYY-MM-DD HH:mm), `Current Status`, `Updated Time`, and `Assign Editor`.
- **FR-004**: System MUST provide a top-level filter bar with linkage between `Journals` (single select), `Manuscript ID` (text search), `Status` (multi-select), and `Assign Editor`.
- **FR-005**: Manuscript IDs MUST be hyperlinks leading to a dedicated "Manuscript Details" page.
- **FR-006**: The "Manuscript Details" page MUST display: Title, Authors, Funding Info, APC Confirmation status, Manuscript Owner, and Assigned Editor.
- **FR-007**: The details page MUST have distinct sections for file management: `Cover Letter`, `Original Files`, `Peer Review Uploads (Word/PDF)`.
- **FR-008**: System MUST implement an "Invoice Info" editing module on the details page allowing authorized users to edit: Authors, Affiliation, APC amount, and Funding Info.
- **FR-009**: The "Add Reviewer" workflow MUST be updated to a two-step process: 1) Add to library (storing Title, Institution, Interests, Homepage), 2) Search and assign from library.
- **FR-010**: "Internal Owner" binding MUST be a standalone functional block, independent of the reviewer assignment dialog.

### Key Entities

- **Manuscript**: Updated with 12-stage status and metadata for Invoice Info.
- **Reviewer Profile**: Extended with `title`, `institution`, `research_interests` (array), and `homepage`.
- **Process Log**: Records every status transition with precise UTC timestamps.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of manuscripts follow the new 12-stage status machine without state corruption.
- **SC-002**: Page load time for "Manuscripts Process" table with 1000+ entries is under 1.5 seconds.
- **SC-003**: 100% of displayed timestamps match the required `YYYY-MM-DD HH:mm` format.
- **SC-004**: Data consistency: "Updated Time" in the table matches the latest entry in the transition logs.
- **SC-005**: User error reduction: Zero "accidental invitations" during the reviewer library addition phase.
