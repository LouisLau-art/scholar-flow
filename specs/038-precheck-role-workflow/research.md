# Research: Pre-check Role Workflow

## Decision: Data Model Schema
**Decision**: Add `assistant_editor_id` (UUID) and `pre_check_status` (TEXT) to `manuscripts` table.
**Rationale**:
- `assistant_editor_id` is needed to assign a specific AE to a manuscript, distinct from the generic "Editor" or "Owner" (which might change). This ensures accountability.
- `pre_check_status` allows sub-state tracking within the existing `PRE_CHECK` master status, avoiding pollution of the public `ManuscriptStatus` enum and minimizing impact on `allowed_next` logic for other modules.
**Alternatives Considered**:
- *Overloading `editor_id`*: Rejected because we lose the history of who was the AE once it moves to EIC/Review.
- *New Master Statuses (INTAKE, TECHNICAL, ACADEMIC)*: Rejected to keep the public-facing status simple and minimize migration risk for existing "Pre-check" logic.

## Decision: RBAC Implementation
**Decision**: Use `user_profiles.roles` (TEXT[]) to validate permissions.
**Rationale**: Existing schema supports multiple roles per user. We will define canonical role strings: `managing_editor`, `assistant_editor`, `editor_in_chief`.
**Alternatives Considered**:
- *Separate permissions table*: Overkill for MVP.

## Decision: Queue Implementation
**Decision**: Implement dedicated API endpoints for each queue (ME, AE, EIC) that filter based on `status`, `pre_check_status`, and `assistant_editor_id`.
**Rationale**: Keeps frontend logic simple (just fetch "my queue").
- ME Queue: `status='pre_check'` AND `pre_check_status='intake'` (or null).
- AE Queue: `status='pre_check'` AND `pre_check_status='technical'` AND `assistant_editor_id=me`.
- EIC Queue: `status='pre_check'` AND `pre_check_status='academic'`.

## Decision: Rejection Logic
**Decision**: Rejection is only allowed via `POST /decision` (Final Decision). Pre-check stages can only "Move to Revision" or "Move to Next Stage" or "Move to Decision Phase".
**Rationale**: Enforces the constraint "No direct reject from pre-check".

## Open Questions Resolved
- **Existing Schema**: Confirmed `manuscripts` has `editor_id` but no `ae_id`.
- **Status Log**: `status_transition_logs` exists and can store text transitions.
