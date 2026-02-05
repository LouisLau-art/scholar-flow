# Feature 036: Internal Collaboration & Manuscript Detail Upgrade

**Status**: Implemented (2026-02-06)
**Type**: Feature / Refactor

## Background

The "Manuscript Detail" page (`/editor/manuscript/[id]`) is the command center for editors. It needs to be high-density and support internal collaboration.
Based on the "Upgrade Plan v2.0", we need to align this page with the new design (2-column layout) and add collaboration tools.

## Goals

1.  **Refactor Layout**: Switch to a 2-column layout (Left: Info/Files/Notebook, Right: Workflow/History) to match the new UI mocks.
2.  **Internal Notebook**: Add a real-time style commenting system for internal staff (AE, ME, EIC) to discuss manuscripts without cluttering the decision letter.
3.  **Audit Log**: Visualize the `status_transition_logs` as a timeline to track history.
4.  **File Hub**: Centralize all file downloads (Manuscript, Cover Letter, Peer Review Files) into a single "Document Repository" card.
5.  **Metadata Visibility**: Clearly display Owner (Sales), AE, and Finance Status.

## Implementation Details

### Database

-   **New Table**: `internal_comments`
    -   `id` (uuid)
    -   `manuscript_id` (fk)
    -   `user_id` (fk)
    -   `content` (text)
    -   `created_at` (timestamptz)
-   **RLS**: Only `is_internal_staff` (or authenticated editors/admins) can read/write.

### Backend API (`/api/v1/editor`)

-   `GET /manuscripts/{id}/comments`: Fetch internal comments.
-   `POST /manuscripts/{id}/comments`: Post a new comment.
-   `GET /manuscripts/{id}/audit-logs`: Fetch `status_transition_logs` for the timeline.

### Frontend (`/editor/manuscript/[id]`)

-   **Components**:
    -   `InternalNotebook`: Comment list + Input box.
    -   `AuditLogTimeline`: Vertical timeline of status changes.
    -   `FileHubCard`: Tabbed or grouped list of files.
-   **Layout**:
    -   Header: Sticky, with Status/Updated Time.
    -   Left Col: Metadata Card -> File Hub -> Notebook.
    -   Right Col: Workflow Actions -> Audit Log.

## Status

-   [x] Database migration created (`20260206100000_create_internal_comments.sql`)
-   [x] Backend API endpoints implemented & tested manually.
-   [x] Frontend page refactored with new layout.
-   [x] UI Mocks generated and inserted into documentation.
