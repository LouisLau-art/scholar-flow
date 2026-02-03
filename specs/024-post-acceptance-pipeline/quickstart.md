# Quickstart: Post-Acceptance Pipeline

## Prerequisites

- Python 3.10+
- Supabase local instance running

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install reportlab
    ```

2.  **Run Migrations**:
    ```bash
    # Apply new invoice table and manuscript columns
    supabase db push
    ```
    *(Or run the SQL file manually if not using CLI push)*

## Verification

### 1. Invoice Generation
1.  Log in as Editor.
2.  Approve a manuscript: `POST /api/v1/editor/decisions` with `decision=accept`.
3.  Check Database: `select * from public.invoices where manuscript_id = '...'`.

### 2. Payment Flow
1.  Log in as Admin.
2.  Mark paid: `POST /api/v1/invoices/{invoice_id}/pay`.
3.  Verify status is `paid`.

### 3. Production Upload
1.  Log in as Editor.
2.  Upload PDF: `POST /api/v1/manuscripts/{id}/production-file` with a PDF.
3.  Verify `final_pdf_path` in `manuscripts` table.

### 4. Publish
1.  Log in as Editor.
2.  Publish: `POST /api/v1/manuscripts/{id}/publish`.
3.  Verify status is `published` and DOI is set.
