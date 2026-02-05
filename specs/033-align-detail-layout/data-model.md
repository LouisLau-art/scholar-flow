# Data Model: Align Manuscript Detail Page Layout

## Entities

### Manuscript (Header Projection)
Fields needed for the new Header layout.

| Field | Type | Source | Display Label |
|---|---|---|---|
| `title` | Text | manuscripts | Title |
| `authors` | Text[] | manuscripts | Authors |
| `funding_info` | Text | manuscripts | Funding |
| `owner_id` | UUID | manuscripts | Internal Owner |
| `editor_id` | UUID | manuscripts | Assigned Editor |
| `apc_status` | Enum | invoices.status | APC Status |

### Files (Categorized)
Logical grouping for the file area.

| Category | Filter Logic | Permissions |
|---|---|---|
| `Cover Letter` | `file_type = 'cover_letter'` | Editor View |
| `Original Manuscript` | `file_type = 'manuscript'` | Editor View |
| `Peer Review Files` | `file_type = 'review_attachment'` | Editor View Only |

### Invoice Info (Bottom Panel)
Fields for the financial footer.

| Field | Source | Editable? |
|---|---|---|
| `billable_authors` | invoices | Yes |
| `affiliation` | invoices | Yes |
| `amount` | invoices | Yes |
| `funding` | invoices | Yes |
