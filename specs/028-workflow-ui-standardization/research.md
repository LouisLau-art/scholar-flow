# Research: Workflow and UI Standardization

## Decisions & Rationale

### 1. 12-Stage Status Machine Implementation
**Decision**: Update the existing `manuscripts.status` enum in the database and implement a formal state transition service.
**Rationale**: The PDF specifies a strict sequence from `Pre-check` to `Published`. Implementing this as a centralized service ensures that state transitions are validated, logged (audit trail), and triggered correctly across the system (e.g., triggering English Editing after Layout).
**Alternatives considered**: Ad-hoc status updates in controllers (Rejected: leading to inconsistent states and hard-to-maintain logic).

### 2. Manuscripts Process (Pipeline) View
**Decision**: Replace the board/card view with a `Shadcn UI` based data table.
**Rationale**: PDF P2/P3 requires a professional tabular view with sortable columns and precision timestamps. Data tables provide better density and control for large manuscript sets.
**Alternatives considered**: Keeping the card view but adding filters (Rejected: does not meet the "类似于一个表格" requirement).

### 3. Precision Timestamps and Timezones
**Decision**: Store all timestamps in PostgreSQL as `TIMESTAMPTZ` (UTC) and use `date-fns` on the frontend for local timezone rendering.
**Rationale**: Requirements specifically mention "精确到小时和分钟" and "时区的问题". Using UTC at the database level is the industry standard for avoiding drift.

### 4. Reviewer Management Logic
**Decision**: Add a `title` field and `metadata` JSONB column to `user_profiles` to store academic details (Institution, Interests, etc.).
**Rationale**: PDF P3 requires more detail for reviewers. Decoupling "Add to library" from "Assign" requires a state where a user is in the library but not yet assigned to a specific task.

### 5. Invoice Info and APC Management
**Decision**: Add an `invoice_metadata` JSONB column to the `manuscripts` table to store Authors, Affiliation, APC, and Funding.
**Rationale**: These fields are manuscript-specific and need to be editable via an "Edit" button on the details page (PDF P6). JSONB allows flexibility for different journal metadata requirements.

## Best Practices

- **FastAPI**: Use `Enum` for status codes to ensure type safety in the backend.
- **Next.js**: Use `Server Components` for the main list to ensure fast initial load (<1.5s SC-002) and `Client Components` for interactive filters.
- **Supabase**: Use `RPC` or `Stored Procedures` for complex state transitions that involve multiple table updates (e.g., updating manuscript status + creating a notification + updating the audit log).
