# Research: Enhance Manuscripts Process List

## Decisions & Rationale

### 1. Filter State Management
**Decision**: Use URL query parameters (`?status=x&journal=y`) as the single source of truth for filter state.
**Rationale**: Meets FR-005 requirement for bookmarking/sharing. React Server Components (RSC) can read params directly to fetch data, reducing client-side effect complexity.
**Alternatives considered**: Local state (Rejected: fails bookmarking requirement).

### 2. Search Implementation
**Decision**: Implement server-side search via Supabase `ilike` or `textSearch` on the `manuscripts` table.
**Rationale**: Client-side search is insufficient for large datasets.
**Alternatives considered**: Dedicated search service (Rejected: overkill for MVP).

### 3. Quick Actions UI
**Decision**: Use `Lucide React` icons inside a flex container within the table cell.
**Rationale**: Clarification session confirmed "Icon Buttons" for efficiency. Lucide is already the project standard. Tooltips will provide labels.

### 4. Pre-check Workflow
**Decision**: The "Pre-check" quick action will open a Shadcn `Dialog` that reuses the logic from the details page but in a condensed form.
**Rationale**: Allows editing the decision comment without leaving the list context.

## Best Practices

- **Debounce**: Apply 300ms debounce to the search input to prevent API spamming.
- **Date Formatting**: Use `date-fns` with `format(date, 'yyyy-MM-dd HH:mm')` for strict adherence to requirements.
- **Composition**: Extract `ProcessFilterBar` and `ManuscriptActions` as pure components to keep the page logic clean.
