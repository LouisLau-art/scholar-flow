# Research: Owner Binding

## 1. Data Model Strategy

**Decision**: Add `owner_id` as a nullable UUID foreign key to `manuscripts` table, referencing `auth.users`.

**Rationale**:
- **Simplicity**: Direct relationship is standard for ownership.
- **Referential Integrity**: Ensures owner exists.
- **Nullable**: Natural submissions have no owner initially.

**Alternatives Considered**:
- **Separate `manuscript_owners` table**: Overkill for 1:1 relationship.
- **Using `assigned_to`**: Confusing with Reviewers or current Editor working on it (which might rotate). `owner` is permanent KPI owner.

## 2. API Validation Strategy

**Decision**: Validate `owner_id` against `user_profiles` table to check for `editor` or `admin` role before update.

**Rationale**:
- **Data Quality**: Prevents accidental assignment to authors or reviewers.
- **Security**: Enforces business rule at the API level.

## 3. Frontend Component Strategy

**Decision**: Use a Combobox (Shadcn `Command` + `Popover`) fetching from a new `/api/v1/editor/staff` endpoint.

**Rationale**:
- **UX**: Searchable dropdown is better than a long select list.
- **Performance**: Fetching staff list is lightweight compared to all users.
- **Reusability**: Staff list endpoint can be used elsewhere.

## 4. Unknowns Resolved

- **Combobox Empty State**: UI will show "No internal staff found" if search yields no results.
- **Role Terminology**: Standardized on "editor" and "admin" roles from `user_profiles.roles` JSONB array.
