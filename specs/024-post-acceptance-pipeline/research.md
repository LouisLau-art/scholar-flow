# Research & Decisions

**Feature**: `024-post-acceptance-pipeline`

## Decisions

### 1. Invoice PDF Generation Library
**Decision**: Use `reportlab`.
**Rationale**: `reportlab` is the industry standard for generating programmatic PDFs in Python. It is lightweight, fast, and does not require external browser dependencies like `WeasyPrint` (which needs GTK/cairo).
**Alternatives**:
- `WeasyPrint`: Good for HTML-to-PDF, but heavy dependencies.
- `FPDF`: Simpler, but less powerful for complex layouts if needed later.

### 2. Production File Storage
**Decision**: Use Supabase Storage bucket `manuscripts` with path `production/{manuscript_id}/{filename}`.
**Rationale**: Reusing the existing bucket simplifies permissions and configuration. The `production/` prefix separates these final assets from initial submissions.

### 3. Database Schema
**Decision**:
- New `invoices` table linked to `manuscripts`.
- Add `final_pdf_path`, `doi`, `published_at`, `owner_id` (confirm usage) to `manuscripts`.
**Rationale**: Relational integrity. `owner_id` on manuscript allows KPI tracking of the inviting editor.

### 4. DOI Mocking
**Decision**: Format `10.5555/scholarflow.{year}.{short_uuid}`.
**Rationale**: `10.5555` is a common test prefix. Using the short UUID ensures uniqueness without a complex counter system for the MVP.

## Unknowns Resolved
- **Invoice Trigger**: Will be triggered synchronously by the `ManuscriptService.approve` method (or similar state transition logic) to ensure atomic operation or via a robust background task if available. For MVP, synchronous within the `approve` endpoint is acceptable if PDF gen is fast (<1s).
