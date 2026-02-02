# Implementation Plan - Revision & Resubmission Loop

The goal of this feature is to implement a complete "Revision & Resubmission" workflow in the ScholarFlow system. This moves beyond the simple Accept/Reject binary decision model and introduces a cyclic process where Editors can request modifications (Major/Minor) and Authors can submit revised versions.

## User Review

> [!IMPORTANT]
> **Critical User Feedback**: The user has emphasized the need for a robust versioning system and strict file safety (never overwriting originals). The system must handle the full loop: Editor Request -> Author Submission -> Editor Re-evaluation.

## Technical Context

### Architecture

This feature touches both the Frontend (Next.js/React) and Backend (FastAPI/Supabase). It introduces a new state machine for manuscripts and requires significant database schema changes to support versioning.

**Frontend**:
- **Components**: New "Request Revision" modal for Editors, "Submit Revision" form for Authors.
- **Pages**: Updates to Editor Dashboard (pipeline visualization), Author Dashboard (status actions), and Manuscript Detail pages.
- **State**: Handling new manuscript statuses (`revision_requested`, `resubmitted`).

**Backend**:
- **API**: New endpoints for requesting revisions, submitting revisions, and handling re-review assignments.
- **Database**: New `manuscript_versions` table, `revisions` table, and updates to `manuscripts` table.
- **Storage**: Logic to handle versioned file uploads (e.g., `paper_id_v2.pdf`).

### Dependencies

- **Supabase Database**: For storing manuscript metadata, versions, and revision tracking.
- **Supabase Storage**: For storing manuscript PDF files.
- **FastAPI**: Backend logic for state transitions and validation.
- **React Hook Form**: For frontend form handling.

### Integrations

- **Notification System**: Triggers notifications for "Revision Requested" and "Resubmission Received".
- **Email Service**: Sends email alerts for critical workflow steps.

## Constitution Check

### Gates

- [x] **Gate 1: No Regression** - The new revision workflow MUST NOT break the existing submission or direct Accept/Reject flows.
- [x] **Gate 2: File Safety** - The implementation MUST guarantee that original manuscript files are never overwritten.
- [x] **Gate 3: State Clarity** - The manuscript status state machine must be deterministic and clearly defined.

### Rules

- **R1: Explicit State Transitions**: All status changes (e.g., `under_review` -> `revision_requested`) must be handled by dedicated backend endpoints, not direct DB updates from the client.
- **R2: Data Integrity**: Version history must be immutable. Once a version is snapshotted, it cannot be changed.
- **R3: User Feedback**: Actions like "Request Revision" must provide immediate feedback (success/error) to the user.

## Phase 0: Outline & Research

- [ ] **Research 1**: Verify Supabase Storage file versioning capabilities or best practices for manual versioning (e.g., naming conventions vs. buckets).
- [ ] **Research 2**: Determine the best way to model the `Revision` entity to support multiple rounds (e.g., linked list vs. simple 1:N with round number).
- [ ] **Research 3**: Check existing "Make Decision" logic to ensure it can be cleanly refactored or extended without breaking changes.

## Phase 1: Design & Contracts

- [ ] **Design 1**: Define the data model for `manuscript_versions` and `revisions` tables.
- [ ] **Design 2**: Define the state machine transitions for the revision loop.
- [ ] **Contract 1**: OpenAPI spec for `POST /revisions/request` (Editor requests revision).
- [ ] **Contract 2**: OpenAPI spec for `POST /revisions/submit` (Author submits revision).
- [ ] **Contract 3**: OpenAPI spec for `GET /manuscripts/{id}/versions` (View version history).

## Phase 2: Implementation

- [ ] **Task 1**: Database Migration - Create `manuscript_versions` and `revisions` tables.
- [ ] **Task 2**: Backend - Implement "Request Revision" logic (Snapshotting + Status Update).
- [ ] **Task 3**: Backend - Implement "Submit Revision" logic (File Upload + Version Increment).
- [ ] **Task 4**: Backend - Implement "Re-review" logic (Link to existing/new reviewers).
- [ ] **Task 5**: Frontend - Editor "Request Revision" Modal.
- [ ] **Task 6**: Frontend - Author "Submit Revision" Page/Form.
- [ ] **Task 7**: Frontend - Display Version History on Manuscript Detail.