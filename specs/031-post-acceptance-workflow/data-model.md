# Data Model: Enhance Post-Acceptance Workflow

## Entities

### Manuscript (Status Transitions)
The `manuscripts` table uses the existing `status` enum.

**Valid Transitions**:
- `accepted` -> `layout`
- `layout` -> `english_editing`
- `english_editing` -> `proofreading`
- `proofreading` -> `published`

**Reversion Paths**:
- `proofreading` -> `english_editing`
- `english_editing` -> `layout`

### Invoice (Gate Check)
Used to validate the Payment Gate.

| Field | Type | Description |
|---|---|---|
| `manuscript_id` | UUID | FK to manuscripts |
| `status` | Enum | `pending`, `paid`, `waived`, `cancelled` |
| `amount` | Numeric | If > 0, payment is required |

## Validation Rules
- **Payment Gate**: Transition to `published` requires related invoice `status` in (`paid`, `waived`) OR `amount` <= 0.
- **Production Gate**: Transition to `published` requires `final_pdf_path` IS NOT NULL (if `PRODUCTION_GATE_ENABLED=true`).
