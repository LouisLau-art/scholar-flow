# Feature Specification: Manuscript Details and Invoice Info Management

**Feature Branch**: `029-manuscript-details-invoice`  
**Created**: 2026-02-04  
**Status**: Draft  
**Input**: User description: "好的 咱们不着急 咱们一次只做一个任务 就按你说的 做User Story 2 (详情页与 Invoice Info)"

## User Scenarios & Testing *(mandatory)*

## Clarifications

### Session 2026-02-04
- Q: Should we use a modal or an inline form for editing the invoice information? → A: Modal (Focuses editing and prevents accidental changes).
- Q: Should the "Authors" field in invoice info be free-text or linked to user profiles? → A: Free-text (Allows flexible formatting for official invoice documents).
- Q: Should the APC amount support multiple currencies? → A: Fixed USD (Standardizing on USD as per project requirements).
- Q: Are the document sections visible to the authors? → A: Restricted (Peer Review Reports section is Editor-only on this specific details page).
- Q: Should changes to invoice metadata be audited? → A: Yes (All edits must be logged in the Status Transition/Audit Log).

### User Story 1 - Centralized Document Management (Priority: P1)

As an Editor, I want the manuscript details page to organize documents into distinct sections (Cover Letter, Original Manuscript, and Peer Review Reports), so that I can quickly access the files needed for evaluation and publication.

**Why this priority**: Core operational efficiency. Replaces the current unstructured file links with a professional, organized workspace as required by PDF P4-P5.

**Independent Test**: Navigate to a manuscript's details page and verify that files are grouped into the three specified categories and are downloadable.

**Acceptance Scenarios**:

1. **Given** a manuscript with all required files, **When** I view its details page, **Then** I see three clearly labeled sections: "Cover Letter", "Original Manuscript", and "Peer Review Reports (Word/PDF)".
2. **Given** a specific file section, **When** I click a file link, **Then** the corresponding file is downloaded or opened in a new tab.

---

### User Story 2 - Invoice Info and Metadata Editing (Priority: P1)

As an Editor, I want to be able to edit a manuscript's invoice-related metadata (Authors, Affiliation, APC Amount, and Funding Info), so that the information used for generating the final invoice is accurate.

**Why this priority**: Financial accuracy and compliance. Ensures that the system-generated invoices reflect the latest metadata as required by PDF P6.

**Independent Test**: Edit the "APC Amount" for a manuscript on its details page and verify the updated amount is persisted and displayed.

**Acceptance Scenarios**:

1. **Given** a manuscript details page, **When** I click the "Edit Invoice Info" button, **Then** a form appears allowing me to modify Authors, Affiliation, APC Amount, and Funding Info.
2. **Given** the invoice info form, **When** I save the changes, **Then** the new metadata is persisted to the database and displayed on the details page.

---

### User Story 3 - High-Level Manuscript Metadata Display (Priority: P2)

As an Editor, I want a clear header on the details page showing essential manuscript information (Title, Authors, Owner, and APC Status), so that I have immediate context when opening any paper.

**Why this priority**: Improves user experience and provides quick context for administrative tasks.

**Independent Test**: Open a manuscript details page and verify the header displays the correct Title, Primary Authors, and Current APC status.

**Acceptance Scenarios**:

1. **Given** a manuscript details page, **When** the page loads, **Then** a header section displays the Title, Author list, Internal Owner, and a clear "Paid/Unpaid" indicator for APC.

---

### Edge Cases

- **Missing File Sections**: What happens if a manuscript is missing a specific file type (e.g., no Peer Review Word file)? (Assumption: The section should show a "Not Uploaded" placeholder rather than being hidden).
- **Invalid APC Amount**: What happens if an editor enters a non-numeric value for APC Amount? (Requirement: System must validate numeric input and show a user-friendly error).
- **Unauthorized Editing**: What happens if a non-editor tries to access the invoice info edit endpoint? (Requirement: System must enforce role-based access control and return a 403 error).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated "Manuscript Details" page accessible via Manuscript ID link.
- **FR-002**: The details page MUST implement three distinct file management sections: `Cover Letter`, `Original Manuscript`, and `Peer Review Reports` (supporting both Word and PDF formats).
- **FR-003**: System MUST implement an "Invoice Info" section displaying: Authors (Free-text), Affiliation, APC Amount (Fixed USD), and Funding Info.
- **FR-004**: System MUST allow Editors and Admins to edit the fields in the "Invoice Info" section via a modal dialog.
- **FR-005**: All metadata changes in the Invoice Info section MUST be persisted to the `invoice_metadata` JSONB column and logged in the system audit trail.
- **FR-006**: The page header MUST prominently display: Title, Primary Authors, Manuscript Owner, Assigned Editor, and APC Payment Status.
- **FR-007**: System MUST support downloading all associated manuscript files directly from their respective sections, respecting role-based visibility (Peer Review Reports are Editor-only).
- **FR-008**: System MUST display the "Updated Time" of the manuscript precisely (YYYY-MM-DD HH:mm) in the metadata section.

### Key Entities

- **Manuscript**: The primary entity, now requiring structured file associations and `invoice_metadata`.
- **User Profile**: Referenced for the Owner and Editor roles displayed in the header.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of manuscript details pages display the three required file sections.
- **SC-002**: Metadata edits (Authors, APC, etc.) are saved successfully in under 500ms.
- **SC-003**: 100% of invoice-related fields are editable for users with `editor` or `admin` roles.
- **SC-004**: Zero data loss when switching between different manuscripts' details pages.