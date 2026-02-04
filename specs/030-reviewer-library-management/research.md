# Research: Reviewer Library Management

## Decisions & Rationale

### 1. Unified Identity Strategy
**Decision**: Use `auth.users` and `public.user_profiles` as the source of truth for all reviewers in the library.
**Rationale**: Clarification Session 2026-02-04 confirmed immediate user creation. This avoids duplicating fields like `affiliation` and `research_interests` in a separate table and allows for a unified search index.
**Alternatives considered**: A separate `reviewer_pool` table (Rejected: leads to data fragmentation).

### 2. Profile Schema Extension
**Decision**: Add `title` (text/enum) and `homepage_url` (text) columns directly to the `public.user_profiles` table.
**Rationale**: Minimal schema overhead and high performance for joined queries (e.g., fetching assignments with profile details).
**Alternatives considered**: A `reviewer_metadata` table (Rejected: overkill for two fields).

### 3. Asynchronous Workflow
**Decision**: Use the existing `EditorialService` to handle "Add to Library" (no email) and a separate "Assign" method (triggers email via `EmailService`).
**Rationale**: Decoupling prevents accidental email spam during data entry.
**Alternatives considered**: A "Draft" assignment state (Rejected: too complex for the current MVP).

### 4. Search Implementation
**Decision**: Leverage PostgreSQL Full-Text Search (FTS) with a GIN index on `user_profiles`.
**Rationale**: Ensures <500ms performance for 1,000+ entries (Success Criteria SC-002) without introducing external search engines like ElasticSearch.

## Best Practices

- **Supabase Admin**: Use the service role key for creating `auth.users` without password verification (setting a random password).
- **Validation**: Use Pydantic's `HttpUrl` or custom regex for `homepage_url` validation in the backend.
- **UI UX**: Use Shadcn UI `Command` or `Combobox` for searching and selecting reviewers from the library.
