# Data Model: Automated Invoice PDF (Feature 026)

## Entities

### `invoices` (existing)

**Purpose**: One invoice per manuscript, used by Payment Gate and author payment workflow.

**Existing fields (observed/assumed)**:
- `id` (UUID, PK)
- `manuscript_id` (UUID, UNIQUE, FK → `manuscripts.id`)
- `amount` (numeric)
- `status` (`unpaid` / `paid`)
- `confirmed_at` (timestamp, nullable)
- `pdf_url` (text, nullable; currently used as a placeholder)
- `created_at` (timestamp)
- `deleted_at` (timestamp, nullable)

### Invoice PDF fields (new / clarified)

To support durable storage + secure download:

- `invoice_number` (text, NOT NULL after generation)
  - Format: `INV-{YYYY}-{invoice_id_short}`
  - Display-only identifier, stable over time
- `pdf_path` (text, nullable)
  - Stable storage object path in bucket `invoices`
  - Example: `{manuscript_id}/{invoice_id}.pdf`
- `pdf_generated_at` (timestamp, nullable)
  - When the current PDF was generated
- `pdf_error` (text, nullable)
  - Last generation error message (for internal debugging / retry UI)

**Constraints / Rules**:
- One manuscript must not have multiple invoices: enforced by existing `manuscript_id UNIQUE` and `upsert on_conflict=manuscript_id`.
- Regeneration overwrites `pdf_path` content and updates `pdf_generated_at/pdf_error`, but MUST NOT mutate `status/confirmed_at`.
- The database must NOT store a time-limited signed URL (avoid expiration bugs).

## Storage (Supabase Storage)

### Bucket: `invoices`

- `public = false`
- Object key pattern (recommended): `{manuscript_id}/{invoice_id}.pdf`

### Access policy (MVP baseline)

- Upload/sign is performed by backend using service role.
- Client downloads via backend-generated short-lived signed URL.

