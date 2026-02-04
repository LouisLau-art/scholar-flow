# Feature Specification: Automated Invoice PDF

**Feature Branch**: `026-automated-invoice-pdf`  
**Created**: 2026-02-03  
**Status**: Draft  
**Input**: User description: "开启 Feature 026: 自动化 PDF 账单引擎..."

## Clarifications

### Session 2026-02-03 (Auto-Resolved per User Instruction)

- Q: What event triggers invoice PDF generation? → A: When the manuscript is accepted (status becomes `approved`).
- Q: What is the invoice number format? → A: Human-readable `INV-{YYYY}-{invoice_id_short}` (stable, unique).
- Q: How is regeneration handled? → A: Regenerate replaces the existing invoice document while keeping the same invoice record and payment status.
- Q: Where does “Bank Details” come from? → A: System-configured payment instructions (single journal-level configuration for MVP).
- Q: How is invoice download secured? → A: Authenticated download for the manuscript author and internal roles only (no public access).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Invoice Generation (Priority: P1)

As the System (or Editor), I want a professional invoice PDF to be automatically generated when a manuscript is accepted, so that the author has a formal document to initiate payment.

**Why this priority**: Core functionality. Without the PDF, the "financial gate" cannot be professionally enforced.

**Independent Test**: Trigger the "acceptance" workflow for a test manuscript and verify an invoice document is generated, stored, and referenced by the invoice record.

**Acceptance Scenarios**:

1. **Given** a manuscript is accepted, **When** the acceptance is recorded, **Then** the system automatically generates an invoice document for that manuscript.
2. **Given** an invoice document is generated, **When** the process completes, **Then** the system stores the document and associates it with the manuscript’s invoice record.
3. **Given** a generated invoice, **When** inspected, **Then** it contains: Invoice Number, Issue Date, Author Name, Manuscript ID, Amount, and Bank Details.

---

### User Story 2 - Author Invoice Download (Priority: P1)

As an Author, I want to download the PDF invoice from my dashboard, so that I can process the payment with my institution.

**Why this priority**: Essential for the user to pay.

**Independent Test**: Log in as an author of an accepted manuscript and click the "Download Invoice" action.

**Acceptance Scenarios**:

1. **Given** a manuscript is accepted and the invoice exists, **When** the Author views the manuscript details/dashboard, **Then** they see a "Download Invoice" action.
2. **Given** the Author triggers "Download Invoice", **When** the download begins, **Then** the browser downloads a valid `.pdf` file.

---

### User Story 3 - Admin/Editor Regeneration (Priority: P2)

As an Editor/Admin, I want to regenerate the invoice document if invoice details change (e.g., amount), so that the author always sees the latest official invoice.

**Why this priority**: Avoids manual PDF creation when business details change; keeps records consistent.

**Independent Test**: Adjust the invoice amount for an accepted manuscript and trigger regeneration; verify the stored invoice document updates while remaining associated with the same invoice record.

**Acceptance Scenarios**:

1. **Given** an invoice exists for a manuscript, **When** an Editor/Admin triggers regeneration, **Then** the system replaces the stored invoice document for that invoice.
2. **Given** regeneration completes, **When** the Author downloads the invoice again, **Then** they receive the regenerated document reflecting the updated details.

### Edge Cases

- **No Duplicates**: Re-accepting the same manuscript (or repeated clicks) should not create duplicate invoices for one manuscript.
- **Generation Failure**: If invoice generation fails, the system records a visible error state and allows retry; acceptance should not permanently block the manuscript.
- **Missing Metadata**: If Author Name is missing, the invoice uses a safe fallback (e.g., author email) without breaking generation.
- **Access Control**: A different author must not be able to download someone else’s invoice.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically generate an invoice document when a manuscript is accepted.
- **FR-002**: System MUST assign a unique, stable, human-readable invoice identifier (Invoice Number) for each invoice record (format: `INV-{YYYY}-{invoice_id_short}`).
- **FR-003**: The invoice document MUST include: Invoice Number, Issue Date, Author Name, Manuscript ID, Amount, and Bank Details.
- **FR-004**: System MUST store the invoice document durably and maintain a stable reference to it on the invoice record.
- **FR-005**: Authors MUST be able to download their own invoice document from the app UI.
- **FR-006**: Editors/Admins MUST be able to download invoice documents for manuscripts they can access.
- **FR-007**: Editors/Admins MUST be able to regenerate the invoice document for an existing invoice record.
- **FR-008**: System MUST prevent duplicate invoice records for the same manuscript.
- **FR-009**: System MUST restrict invoice document download to authorized users (Author of the manuscript and internal roles).
- **FR-010**: System MUST surface invoice generation failures to internal users in a debuggable way (e.g., error message and retry capability).

### Key Entities

- **Invoice Record**: A billing record linked to a single manuscript, including amount, payment status, invoice identifier, and a reference to the invoice document.
- **Invoice Document**: The downloadable PDF representation of the invoice record.
- **Payment Instructions**: Bank transfer details shown on the invoice document (and optionally in the UI).

### Assumptions

- The product already has a concept of “manuscript accepted” that is recorded reliably (no manual backfills required for MVP testing).
- An invoice amount exists at acceptance time (either configured default or editor-confirmed) and becomes the source of truth for the invoice document.
- Bank details/payment instructions are provided by the journal/business side (system-level configuration for MVP) and can be updated without changing historical payment status.

### Dependencies

- Existing payment gate logic relies on invoice status; this feature must not break that status flow.
- Author identity data (name/email) is available for display on the invoice document.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of accepted manuscripts have an invoice document generated within 60 seconds of acceptance.
- **SC-002**: Invoice PDFs open successfully in standard PDF viewers and contain all required fields.
- **SC-003**: Authors can download their invoice in ≤ 2 clicks from their dashboard/manuscript view.
- **SC-004**: Regenerating an invoice document does not create duplicate invoice records and does not corrupt payment status.
