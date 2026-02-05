# Research: Refine Portal Home and Navigation

## Decisions & Rationale

### 1. Banner & Footer Implementation
**Decision**: Create standalone components `HomeBanner` and `SiteFooter`.
**Rationale**: Adheres to modular design. `SiteFooter` will be included in the root layout to ensure consistency across all public pages.
**Alternatives considered**: Inline layout code (Rejected: hard to maintain across pages).

### 2. "Latest Articles" Query Logic
**Decision**: Use a dedicated `PublishedArticles` service to fetch manuscripts where `status = 'published'`.
**Rationale**: Ensures clear separation of concerns. This logic is already partially present in `ProductionService`, but a public-facing read-only service is safer.
**Alternatives considered**: Direct client-side Supabase call (Rejected: harder to centralize business rules/filtering).

### 3. Static Assets (Metrics & Metrics)
**Decision**: Use placeholders for ISSN and Impact Factor for now, managed via a `site-config.ts` file.
**Rationale**: Allows for easy updates without redeploying code once real values are assigned.

## Best Practices

- **Responsive Design**: Use Tailwind's `md:`, `lg:` prefixes for the banner to ensure it looks academic and spacious on large screens but functional on mobile.
- **Image Optimization**: Use `next/image` for any journal logos or background patterns to ensure fast LCP.
- **Empty States**: Provide a subtle "Recent publications will appear here" placeholder if the database has 0 published articles.
