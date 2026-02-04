# Research: Manuscript Details and Invoice Info Management

## Decisions & Rationale

### 1. Document Management UI Strategy
**Decision**: Use Shadcn UI's `Card` and `List` components to group files into three distinct sections (Cover Letter, Original, Peer Review).
**Rationale**: Adheres to PDF P4-P5 requirements for a professional, organized layout. Grouping by functional category reduces cognitive load for editors compared to a single list of files.
**Alternatives considered**: Accordion-based grouping (Rejected: too many clicks to see available files).

### 2. Invoice Info Editing Interaction
**Decision**: Use a Shadcn `Dialog` (Modal) for editing `invoice_metadata`.
**Rationale**: Approved in clarification session. Modals prevent accidental field changes during scrolling and allow for a dedicated "Review & Save" flow for sensitive financial metadata (APC).
**Alternatives considered**: Inline form (Rejected per user decision).

### 3. File Visibility and Permissions
**Decision**: Implement conditional rendering based on the user's role (Editor/Admin vs. Author) for the "Peer Review Reports" section.
**Rationale**: Spec requires Peer Review Reports to be restricted. Frontend will check the Supabase session role, and backend endpoints will verify the same via JWT.

### 4. Audit Logging for Metadata
**Decision**: Leverage the existing `StatusTransitionLog` or a new `ActivityLog` table to record `invoice_metadata` changes.
**Rationale**: Spec FR-005 requires an audit trail. Storing a JSON snapshot of the "before" and "after" state provides a robust history of financial changes.

## Best Practices

- **Next.js**: Use `Server Actions` for updating the invoice metadata to simplify the form submission lifecycle and revalidation.
- **Tailwind**: Use `grid-cols-1 md:grid-cols-3` for the file section layout to ensure it's responsive but takes advantage of screen width (as fixed in the recent 1600px width update).
- **Security**: Ensure file download URLs are generated on-the-fly (Signed URLs) to prevent unauthorized access to manuscript assets.
