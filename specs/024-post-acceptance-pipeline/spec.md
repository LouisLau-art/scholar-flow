# Feature Specification: Post-Acceptance Pipeline

**Feature Branch**: `024-post-acceptance-pipeline`
**Created**: 2026-02-03
**Status**: Draft
**Input**: User description: "开启 Feature 024: 录用后出版流水线 (Post-Acceptance Pipeline)..."

## Clarifications

### Session 2026-02-03 (Auto-Resolved per User Instruction)
- **Q: Invoice Amount Source?** → **A: Fixed System Default.** The APC amount is a configurable system constant (e.g., $1000 USD) for this MVP phase, applied to all accepted manuscripts.
- **Q: DOI Format Suffix?** → **A: UUID Segment.** The DOI suffix will use the first 8 characters of the manuscript UUID for uniqueness without requiring a separate sequence counter (e.g., `10.xxxx/scholarflow.2026.a1b2c3d4`).
- **Q: Production Role?** → **A: Shared Permissions.** No new "Production Editor" DB role. Existing "Editor" and "Admin" roles will have permission to upload final PDFs.
- **Q: File Re-upload Policy?** → **A: Overwrite.** Uploading a new final PDF replaces the active `final_pdf_path` reference immediately. Old files may remain in storage but are no longer linked.

## User Scenarios & Testing

### User Story 1 - Financial Gate & Payment (Priority: P1)

As an Author, I need to receive an invoice upon acceptance and have my payment confirmed so that my article can proceed to publication.

**Why this priority**: Financial viability is the core "business gate" (Constitution: Financial Loop). Without payment, publication cannot occur.

**Independent Test**: Can be tested by moving a manuscript to `approved` state, verifying invoice generation, downloading it as Author, and manually marking it as `paid` as an Admin, then verifying the status update.

**Acceptance Scenarios**:

1.  **Given** a manuscript is moved to `approved` status, **When** the transition occurs, **Then** an Invoice record is automatically created with status `pending`, amount set to System Default APC, and a notification email is sent to the author.
2.  **Given** an `approved` manuscript, **When** the Author visits their dashboard, **Then** they see a "Download Invoice" button and static "Payment Instructions".
3.  **Given** an unpaid invoice, **When** a Finance Admin (or Editor) marks it as `paid` in the system, **Then** the invoice status updates to `paid`, and the system records the revenue against the inviting editor.

---

### User Story 2 - Production File Management (Priority: P2)

As a Production Editor (or Admin), I need to upload the final typeset PDF so that the publication has a high-quality asset for readers.

**Why this priority**: The "raw" submission PDF is not suitable for final publication. This step ensures the "product" is ready.

**Independent Test**: Upload a PDF to the new "Production Upload" slot and verify the final PDF file is stored and linked to the manuscript.

**Acceptance Scenarios**:

1.  **Given** an `approved` manuscript, **When** an Editor/Admin uses the "Production Upload" interface to upload a file, **Then** the file is saved to secure storage, and the manuscript records the presence of the final PDF (overwriting any previous reference).
2.  **Given** a manuscript without a final PDF, **When** an Editor attempts to Publish, **Then** the system prevents the action.

---

### User Story 3 - One-Click Publication & DOI (Priority: P1)

As an Editor, I want to publish the manuscript with a single click after all gates are met, automatically generating a DOI and notifying the author.

**Why this priority**: This is the final integration step that makes the article public and "real" (DOI).

**Independent Test**: Ensure the "Publish Online" button is only active when gates are met. Click it, and verify status changes to `published`, publication timestamp is set, DOI is mocked, and email is sent.

**Acceptance Scenarios**:

1.  **Given** a manuscript where the invoice is NOT paid OR the final PDF is missing, **When** the Editor views the "Publish Online" action, **Then** the button is disabled or returns a validation error upon click.
2.  **Given** a manuscript where the invoice is paid AND the final PDF is present, **When** the Editor clicks "Publish Online", **Then**:
    *   The manuscript status becomes `published`.
    *   The publication timestamp is recorded.
    *   A DOI is generated (format: `10.xxxx/scholarflow.{year}.{uuid_short}`) and saved.
    *   An "Article Published" email is sent to the author.

---

### User Story 4 - Public Access & Discovery (Priority: P3)

As a Reader, I want to see the newly published article on the homepage and search results so that I can access the research.

**Why this priority**: Completes the loop for the end-user (reader).

**Independent Test**: Publish an article and verify it appears in the "Latest Articles" list on the frontend.

**Acceptance Scenarios**:

1.  **Given** a `published` article, **When** a user visits the homepage, **Then** the article appears in the "Latest Articles" section.
2.  **Given** a `published` article, **When** a user searches for it, **Then** it appears in the results.

### Edge Cases

- **Invoice Cancellation**: If an article is withdrawn after invoice generation but before payment, the invoice status must be manually updated to `cancelled`.
- **Re-upload**: Production Editor needs to replace the final PDF after upload. System allows overwrite.
- **Payment Reversal**: If a payment is marked `paid` in error, Admin must have capability to revert invoice status to `pending`.

## Requirements

### Functional Requirements

- **FR-001**: System MUST automatically generate an Invoice record when a manuscript status changes to `approved` (via DB trigger or service).
- **FR-002**: System MUST allow Authors to download a PDF representation of the Invoice.
- **FR-003**: System MUST provide an interface for Admins/Editors to mark an Invoice as `paid`.
- **FR-004**: System MUST allow Admins/Editors to upload a final PDF file for a manuscript, replacing any existing final PDF.
- **FR-005**: The publication action MUST validate that the associated invoice is in a `paid` state.
- **FR-006**: The publication action MUST validate that a final PDF file has been uploaded.
- **FR-007**: The publication action MUST generate a DOI string (format: `10.xxxx/scholarflow.{year}.{8_char_uuid}`) and save it.
- **FR-008**: The publication action MUST send a "Publication Notification" email to the author.
- **FR-009**: The frontend "Latest Articles" component MUST query only `published` manuscripts, sorted by publication date descending.
- **FR-010**: System MUST record the inviting editor (`owner_id`) association with the Revenue/Invoice for KPI tracking.

### Key Entities

- **Invoice**: Represents the financial transaction. Attributes: `id`, `manuscript_id`, `amount` (default constant), `status` ('pending', 'paid', 'cancelled'), `created_at`, `paid_at`.
- **Manuscript (Enhanced)**: Added attributes: `final_pdf_path` (reference to file), `doi` (unique identifier), `published_at` (timestamp), `owner_id` (existing but reinforced).

## Success Criteria

### Measurable Outcomes

- **SC-001**: Authors can download their invoice within 5 seconds of the manuscript being approved.
- **SC-002**: Editors are physically unable (UI disabled + API error) to publish an article without Payment and Final PDF.
- **SC-003**: Published articles appear on the homepage within 1 minute of the "Publish" action.
- **SC-004**: 100% of published articles have a valid DOI format recorded.