# Research: Enhance Post-Acceptance Workflow

## Decisions & Rationale

### 1. State Machine Control
**Decision**: Reuse the existing `ManuscriptStatus` enum and `EditorialService.update_status` method, but add a new dedicated endpoint `POST /api/v1/editor/manuscripts/{id}/advance-production` for post-acceptance transitions.
**Rationale**: This encapsulates the specific validation logic (payment check, file check) for production stages separate from the generic status update, ensuring business rules are enforced.
**Alternatives considered**: Overloading the generic `update_status` (Rejected: complicates the core logic with too many conditionals).

### 2. Payment Gate Implementation
**Decision**: Query the `invoices` table directly within the transition logic.
**Rationale**: Direct DB check is reliable and atomic. If `amount > 0` and `status != 'paid' | 'waived'`, blocking the transition is a hard constraint.
**Alternatives considered**: Frontend-only check (Rejected: insecure).

### 3. Production Gate Configuration
**Decision**: Use `os.getenv("PRODUCTION_GATE_ENABLED", "false")`.
**Rationale**: Agreed in Spec Clarification. Allows rolling out the feature incrementally.

### 4. UI/UX for Transitions
**Decision**: Add a "Production Status" card to the Manuscript Details sidebar (or top metadata area) with a primary action button that dynamically changes label based on current status (e.g., "Start Layout" -> "Start English Editing").
**Rationale**: Keeps the main content area focused on the manuscript while providing clear, contextual next steps.

## Best Practices

- **Atomic Transactions**: Use Supabase/Postgres transactions when updating status and logging the transition to ensure data integrity.
- **Optimistic Updates**: Frontend should update the UI immediately upon success, using React Query's `invalidateQueries` to refresh the manuscript state.
