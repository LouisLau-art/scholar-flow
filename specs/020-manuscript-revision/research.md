# Research: Revision & Resubmission Loop

## 1. File Versioning Strategy

**Decision:** Use explicit file versioning in the storage path (e.g., `manuscript_id/v1_filename.pdf`, `manuscript_id/v2_filename.pdf`) rather than relying on bucket-level versioning features (which Supabase Storage handles via objects but explicit paths are safer for application logic).

**Rationale:**
- **Control:** We need to strictly associate a specific file version with a specific `Revision` record in the database. Implicit versioning can be opaque.
- **Portability:** File paths stored in the DB (`manuscript_versions.file_path`) will be unambiguous.
- **Organization:** Grouping by `manuscript_id` folder keeps the bucket clean.

**Alternatives Considered:**
- **Bucket Versioning:** Supabase Storage (S3 under hood) supports versioning, but accessing specific versions requires handling version IDs, which complicates the API and data model.
- **Overwrite:** Explicitly rejected by user requirements (Gate 2: File Safety).

## 2. Revision Data Model

**Decision:** Create a `revisions` table (1:N with `manuscripts`) to track the **process** (request type, response letter, dates) and a `manuscript_versions` table (1:N with `manuscripts`, 1:1 with `revisions`) to track the **content** (file path, title snapshot, abstract snapshot).

**Refined Model:**
Actually, linking `manuscript_versions` directly to `revisions` is cleaner.
- `manuscripts`: Current state, current version number.
- `revisions`: Represents a cycle. `manuscript_id`, `round_number`, `status` (requested, submitted, declined?), `decision` (major/minor).
- `manuscript_versions`: Snapshot of data. `manuscript_id`, `revision_id` (nullable for v1?), `version_number`, `file_path`, `title`, `abstract`.

**Simplification for MVP:**
We can combine them or keep them separate.
- A "Revision" is a request from Editor.
- A "Version" is a submission from Author.
- Flow: Version 1 (Initial) -> Editor requests Revision 1 -> Author submits Version 2 (linked to Revision 1).

**Chosen Schema:**
- `manuscript_versions`: Stores content snapshots. `version` 1 is initial.
- `revisions`: Stores the *workflow context*. "Round 1" is requested by Editor. When Author submits Version 2, it fulfills Revision Round 1.

**Rationale:**
- Separates "content history" from "workflow process".
- Allows looking up "what did the author submit for Round 1?" (Version 2).

## 3. Existing "Make Decision" Logic Refactoring

**Decision:** The existing `submit_final_decision` endpoint in `editor.py` handles "accept/reject". We will create a NEW endpoint `request_revision` for the revision workflow to keep concerns separated and avoid making the existing endpoint too complex (it already handles DOI minting, etc.).

**Rationale:**
- **Separation of Concerns:** Final decisions end the process (mostly). Revisions keep it alive.
- **Risk Mitigation:** Touching the "Accept" logic (which mints DOIs) carries regression risk. A new endpoint is safer.

## 4. Re-review Logic

**Decision:** We will reuse the `review_assignments` table. When sending for re-review:
- We can create NEW assignments for the same reviewers (cleanest for tracking history).
- Or we can add a `round` field to `review_assignments`.

**Chosen Approach:** Add `round_number` to `review_assignments`.
- Current assignments are Round 1 (default 1).
- New assignments will be Round 2.
- This allows us to see "Reviewer A gave score 3 in Round 1, and score 5 in Round 2".

**Migration Note:** Existing data needs `round_number` = 1.

## 5. Summary of Changes

1.  **DB**:
    - New `manuscript_versions` table.
    - New `revisions` table.
    - Alter `manuscripts`: add `version` (default 1).
    - Alter `review_assignments`: add `round` (default 1).
2.  **API**:
    - `POST /editor/revisions`: Request revision.
    - `POST /manuscripts/{id}/revisions`: Submit revision (upload + metadata).
    - `GET /manuscripts/{id}/history`: Get versions.
