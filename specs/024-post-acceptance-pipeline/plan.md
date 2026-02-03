# Implementation Plan - Post-Acceptance Pipeline

**Feature**: `024-post-acceptance-pipeline`
**Status**: Phase 0 (Research)

## Technical Context

### Unknowns & Risky Areas

- **Invoice PDF Generation**: We need a library to generate PDFs from Python/FastAPI.
- **Production File Storage**: Where to store the final PDFs? (Supabase Storage bucket `manuscripts` seems appropriate, maybe a subfolder `production/`?)
- **Email Templates**: Need specific wording for "Payment Required" and "Article Published" emails.
- **DOI Generation Library**: How to generate the checksum/format programmatically? (Though mock logic is requested, we should structure it correctly).

### Dependencies

- **Supabase Storage**: For final PDF upload.
- **Supabase Auth**: For role-based access control (Admin/Editor).
- **Email Service**: Existing `email_service.py` needs extension.
- **Database**: New `invoices` table and migration for `manuscripts` columns.

## Constitution Check

| Principle | Status | Notes |
| :--- | :--- | :--- |
| **I. Glue Coding** | ✅ | Using existing Supabase services and Python libraries (ReportLab/WeasyPrint) for PDFs. |
| **II. Test-First** | ✅ | Integration tests will cover the full pipeline (approve -> pay -> publish). |
| **III. Security** | ✅ | Production upload restricted to Editor/Admin. Payment gate enforced on Publish API. |
| **IV. Sync & Commit** | ✅ | Will commit frequently. |
| **V. Env & Tools** | ✅ | Using standard Python/TS stack. |

## Phase 0: Outline & Research

### Research Tasks

- [ ] Select Python PDF generation library (ReportLab vs WeasyPrint vs FPDF).
- [ ] Define DB Schema changes (`invoices` table, `manuscripts` columns).
- [ ] Define API Endpoints for Invoice and Publish actions.

### Research Findings (to be populated in research.md)

- **PDF Lib**: ReportLab is robust for transactional documents like invoices.
- **Storage**: Use `manuscripts` bucket, path `production/{uuid}.pdf`.
- **DOI Mock**: Use standard prefix `10.5555/` for test/mock data.

## Phase 1: Design & Contracts

### Data Model

- **New Table**: `invoices`
    - `id` (UUID, PK)
    - `manuscript_id` (UUID, FK)
    - `amount` (Decimal/Int - stored as cents or standard unit)
    - `status` (Enum: pending, paid, cancelled)
    - `created_at`, `updated_at`, `paid_at`
- **Manuscript Updates**:
    - `final_pdf_path` (Text, nullable)
    - `doi` (Text, nullable, unique)
    - `published_at` (Timestamp, nullable)
    - `owner_id` (UUID, FK to users - already exists but need to ensure it's used)

### API Contracts

- `POST /webhooks/manuscripts/approved` (Internal/Trigger): Generate Invoice.
- `GET /manuscripts/{id}/invoice`: Download PDF.
- `POST /invoices/{id}/pay` (Admin): Mark as paid.
- `POST /manuscripts/{id}/production-file`: Upload final PDF.
- `POST /manuscripts/{id}/publish`: Execute publication.

## Phase 2: Implementation

### Backend

1.  **Migration**: Create SQL migration for schema changes.
2.  **Model**: Update Pydantic models and SQLAlchemy/Supabase models.
3.  **Service**: `InvoiceService` (generate PDF, manage status).
4.  **Service**: `PublicationService` (handle DOI, email, state transition).
5.  **API**: Implement endpoints.
6.  **Tests**: Integration tests for the flow.

### Frontend

1.  **Dashboard (Author)**: Add "Download Invoice" button and payment info.
2.  **Dashboard (Editor)**: Add "Production Upload" and "Publish Online" actions.
3.  **Public Site**: Update "Latest Articles" to fetch only `published` items.
4.  **Tests**: E2E test for the publish flow.

## Gate Checks

- [ ] **Research Complete**: `research.md` created.
- [ ] **Design Complete**: `data-model.md` and contracts created.
- [ ] **Tests Planned**: Test cases defined in tasks.