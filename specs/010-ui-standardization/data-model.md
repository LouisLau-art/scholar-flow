# Data Model & Component State

## Frontend Components

### DecisionPanel

**Path**: `frontend/src/components/DecisionPanel.tsx`

#### Props
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `manuscriptId` | `string` | No | ID of the manuscript being decided on |
| `reviewerScores` | `ReviewerScore[]` | Yes | Array of scores from reviewers |
| `onSubmitted` | `() => void` | No | Callback after successful submission |

#### Internal State
| Name | Type | Initial | Description |
|------|------|---------|-------------|
| `decision` | `'accept' \| 'reject' \| null` | `null` | The decision selected by the editor. Maps to `RadioGroup.Item` value. |
| `comment` | `string` | `''` | Optional comment for the decision |
| `isSubmitting` | `boolean` | `false` | Loading state during API call |
| `submitSuccess` | `boolean` | `false` | Success state to show confirmation UI |

#### Schema Definition (Frontend Validation)
- `decision`: Must be non-null before submit.
- `comment`: Max length 1000 chars (implied).

#### UI State Rules
- **Selection**: Uses `RadioGroup` primitive.
- **Active State**: When `decision` is 'accept' or 'reject', the corresponding card must show "Active" styles (Dark bg, White text).
- **Disabled State**: During `isSubmitting`, all inputs must be disabled.

## Backend Models (No Changes)

No changes to database schema or Pydantic models required for this feature.