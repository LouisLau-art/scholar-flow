# Data Model: Manuscript Details and Invoice Info Management

## Entities

### Manuscript (Extended Metadata)
The `manuscripts` table already exists, but we are standardizing the usage of the `invoice_metadata` JSONB column.

| Field | Type | Description |
|---|---|---|
| `invoice_metadata` | JSONB | Structure: `{ "authors": string, "affiliation": string, "apc_amount": number, "funding_info": string }` |
| `status` | Enum | Used to determine APC payment status (e.g., `approved` leads to invoice generation) |

### Audit Log (Updated)
We use a centralized log to track sensitive changes.

| Field | Type | Description |
|---|---|---|
| `entity_type` | Text | Always "manuscript" for this feature |
| `entity_id` | UUID | Link to the manuscript |
| `action` | Text | e.g., "update_invoice_info" |
| `payload` | JSONB | The diff or new state of the invoice info |
| `user_id` | UUID | The editor/admin who performed the change |

## Validation Rules
- `apc_amount`: Must be a non-negative number.
- `authors`: Free-text, no specific character constraints beyond DB limits.
- `affiliation`: Free-text.
