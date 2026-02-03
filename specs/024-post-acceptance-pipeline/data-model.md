# Data Model

## Tables

### `invoices` (New)

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PK, Default: gen_random_uuid() | Unique Invoice ID |
| `manuscript_id` | UUID | FK -> manuscripts(id), Not Null | Linked Manuscript |
| `amount` | Numeric(10,2) | Not Null, Default: 1000.00 | APC Amount |
| `status` | Text | Not Null, Default: 'pending' | Enum: pending, paid, cancelled |
| `created_at` | Timestamptz | Default: now() | Creation time |
| `updated_at` | Timestamptz | Default: now() | Last update time |
| `paid_at` | Timestamptz | Nullable | Time of payment confirmation |

### `manuscripts` (Update)

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `final_pdf_path` | Text | Nullable | Path in storage to the production PDF |
| `doi` | Text | Nullable, Unique | Digital Object Identifier |
| `published_at` | Timestamptz | Nullable | Time of publication |
| `owner_id` | UUID | FK -> auth.users(id), Nullable | Inviting Editor (for KPI) |

## Relationships

- `manuscripts` (1) -> (0..1) `invoices` (One-to-One mostly, but could be One-to-Many if re-issued, stick to 1 active for MVP).
- `manuscripts` (N) -> (1) `users` (Owner/Editor).

## Validation Rules

- `invoices.status`: Must be one of `pending`, `paid`, `cancelled`.
- `manuscripts.doi`: Must be unique if not null.
- Publish Action: Requires `invoices.status = 'paid'` AND `final_pdf_path IS NOT NULL`.
