# Research: Final Decision Workspace (Feature 041)

## Unknowns & Research Tasks

### 1. PostgREST / Supabase Optimistic Locking
- **Task**: Research how to implement optimistic locking in `supabase-py`.
- **Decision**: Use a manual `updated_at` check in the `.update()` call. PostgREST supports `If-Match` with ETags, but for Python SDK, adding `.eq("updated_at", original_updated_at)` is the most straightforward and consistent with our existing patterns.
- **Rationale**: Keeps implementation simple without custom middleware.
- **Alternatives considered**: If-Match header (too complex for MVP SDK usage).

### 2. Multi-Report Side-by-Side UI Patterns
- **Task**: Find best practices for comparing 3-5 reports on a single screen.
- **Decision**: Vertical list of expandable cards for reports in the middle column. If 2 reports, allow side-by-side. If >2, use a "Sticky Summary" at top + detailed cards below.
- **Rationale**: Horizontal scrolling is painful for text-heavy reports.
- **Alternatives considered**: Horizontal columns (rejected due to space constraints).

### 3. Attachment Persistence
- **Task**: Storage bucket for decision attachments.
- **Decision**: Use a dedicated private bucket `decision-attachments`.
- **Rationale**: Final decision documents should be isolated from reviewer attachments for clearer permission boundaries and easier final-only author visibility enforcement.
- **Alternatives considered**: Reuse `review-attachments` with prefix (rejected due to access-rule coupling risk).
