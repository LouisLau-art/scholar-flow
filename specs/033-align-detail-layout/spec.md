# Feature Specification: Align Manuscript Detail Page Layout

**Feature Branch**: `033-align-detail-layout`  
**Created**: 2026-02-04  
**Status**: Draft  
**Input**: User description: "Feature 033: 详情页布局深度对齐 (Align Detail Page Layout) 核心目标: 1. Header 信息重组 (Title, Authors, Funding, APC Status, Owner, Assigned Editor). 2. 文件区域分三块 (Cover Letter, Original File, Peer Review Upload). 3. Invoice Info 位于页面底部独立的表格区域 + Edit 按钮. 4. Owner 绑定独立的 Card."

## User Scenarios & Testing *(mandatory)*

## Clarifications

### Session 2026-02-04
- Q: Are Peer Review files visible to authors? → A: Editor Only (Raw files are internal; authors receive feedback via decision letters).

### User Story 1 - Header Information Alignment (Priority: P1)

As an Editor, I want to see a consolidated header on the manuscript details page containing Title, Authors, Funding, APC Status, Owner, and Assigned Editor, so that I have all critical metadata at a glance before processing the submission.

**Why this priority**: Corrects the primary information hierarchy to match the editorial workflow (PDF P4).

**Independent Test**: Open a manuscript details page and verify that Title, Authors, Funding, APC Status, Owner, and Editor are all visible in the top section.

**Acceptance Scenarios**:

1. **Given** a manuscript with funding info, **When** I view the details page, **Then** the Funding field is displayed in the header.
2. **Given** a manuscript, **When** I look at the top card, **Then** I see both the "Internal Owner" and "Assigned Editor" clearly distinguished.

---

### User Story 2 - Structured File Sections (Priority: P1)

As an Editor, I want to access submission files in three distinct sections (Cover Letter, Original File, Peer Review Upload), so that I can easily differentiate between author submissions and reviewer materials.

**Why this priority**: Essential for file management and review process integrity (PDF P4).

**Independent Test**: Navigate to the "Files" tab/section and verify three distinct containers/cards exist with the correct titles.

**Acceptance Scenarios**:

1. **Given** the file section, **When** I look for the Cover Letter, **Then** it is in its own dedicated card.
2. **Given** the Peer Review section, **When** I click "Upload", **Then** I can upload Word or PDF files specifically for peer review usage.

---

### User Story 3 - Bottom Invoice Management (Priority: P2)

As an Editor, I want to manage Invoice Information (Authors, Affiliation, APC Amount, Funding) in a dedicated table at the bottom of the page, so that financial data is separated from editorial content but easily accessible for updates.

**Why this priority**: Strict alignment with PDF P6 layout requirement.

**Independent Test**: Scroll to the bottom of the details page and verify the Invoice Info table exists with an "Edit" button.

**Acceptance Scenarios**:

1. **Given** the bottom of the page, **When** I click the "Edit" button in the Invoice Info section, **Then** a modal opens allowing me to modify the APC amount and funding details.

---

### Edge Cases

- **Missing Data**: What if a manuscript has no Funding info? (Assumption: Show "None" or hide the field, avoiding empty gaps).
- **Long Authors List**: How to handle 50+ authors in the header? (Assumption: Truncate with "Show more" or a scrollable container).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Manuscript Details page header MUST display: Title, Authors, Funding, APC Status, Internal Owner, and Assigned Editor.
- **FR-002**: The file management area MUST be divided into three distinct visual containers: "Cover Letter", "Original Manuscript", and "Peer Review Files".
- **FR-003**: The "Peer Review Files" container MUST provide an upload interface supporting `.doc`, `.docx`, and `.pdf` formats, and its contents MUST be visible ONLY to Editors and Admins (not Authors).
- **FR-004**: The Invoice Information section MUST be located at the bottom of the page layout.
- **FR-005**: The Invoice Information section MUST display: Authors (Billable), Affiliation, APC Amount, and Funding Information.
- **FR-006**: The Invoice Information section MUST include an "Edit" button that triggers a modification modal (reusing Feature 029 logic).
- **FR-007**: The "Internal Owner" and "Assigned Editor" MUST be displayed as separate entities in the header (or a dedicated sidebar card if space permits, per PDF P4).

### Key Entities

- **Manuscript**: Metadata (Title, Abstract, etc.).
- **Invoice**: Linked financial data.
- **Files**: Categorized by type (Cover Letter, Manuscript, Review).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Editors can find the "Funding" information in the header in under 1 second (visual scan).
- **SC-002**: Uploading a peer review file takes fewer than 3 clicks.
- **SC-003**: The page layout matches the visual structure of reference PDF P4 and P6 (verified by design review).