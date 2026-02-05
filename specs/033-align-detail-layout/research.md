# Research: Align Manuscript Detail Page Layout

## Decisions & Rationale

### 1. Layout Structure (Grid vs Flex)
**Decision**: Use CSS Grid (Tailwind `grid-cols-12`) for the main layout.
**Rationale**: The PDF P4 layout implies a complex 2-column structure with varying row heights (Header spans full, Files split, Invoice full bottom). Grid offers precise control over spanning (`col-span-12`, `col-span-4`) compared to nested Flexboxes.
**Alternatives considered**: Flexbox (Rejected: harder to align vertical rhythm across columns).

### 2. File Section Component
**Decision**: Create a generic `FileSectionCard` component that accepts `title`, `files` array, and an optional `uploadAction` slot.
**Rationale**: The three file sections (Cover, Original, Review) share identical visual structure (Card, Title, List) but differ in actions. Composition is cleaner than repetition.

### 3. Invoice Info Location
**Decision**: Place the Invoice Info component at the very bottom of the `main` content area, just above the footer (if any).
**Rationale**: Strict adherence to FR-004/PDF P6. This separates financial data from the editorial workflow visually.

### 4. Owner & Editor Display
**Decision**: Display "Internal Owner" and "Assigned Editor" as two distinct fields in the top-right metadata grid of the Header.
**Rationale**: PDF P4 shows them grouped with metadata. Sidebar is reserved for actions/status.

## Best Practices

- **Component Splitting**: Break the giant `/manuscript/[id]/page.tsx` into `ManuscriptHeader`, `ManuscriptFileArea` (containing the 3 cards), and `InvoiceInfoPanel`.
- **Skeleton Loading**: Each section should have its own skeleton to avoid layout shift as data loads progressively.
