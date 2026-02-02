# Feature Specification: Revision & Resubmission Loop

**Feature Branch**: `020-manuscript-revision`
**Created**: 2026-01-31
**Status**: Draft
**Input**: User description: "开启 Feature 020: 修稿与复审闭环 (Revision & Resubmission Loop)。 背景：目前系统的决议逻辑仅支持二元选项 (Accept/Reject)，缺失了学术界最核心的“退修 (Revision)”流程。UAT 期间发现 Editor 无法要求作者修改，Author 也无法上传修改稿。 本功能旨在实现完整的多轮审稿机制。 核心需求如下： 1. **决策选项扩展 (Decision Logic Upgrade)**： - **Editor 端**：在 "Make Decision" 弹窗中，新增以下选项： - **Major Revision (大修)**：通常意味着需要再次送审。 - **Minor Revision (小修)**：通常由编辑直接确认即可。 - **状态流转**： - 选择 Revision 后，稿件状态从 `under_review` 变更为 `revision_requested`。 - 此时流程**不应该结束**，而是挂起等待作者操作。 2. **作者修稿工作台 (Author Revision UI)**： - **入口**：Author 登录后，在 Dashboard 看到状态为 `revision_requested` 的稿件，出现 "Submit Revision" 按钮。 - **提交表单**： - **Response Letter**：一个富文本框或文件上传，用于回复审稿意见。 - **Revised Manuscript**：上传新的 PDF 文件。 - **动作**：提交后，稿件状态变更为 `resubmitted` (或 `revision_submitted`)。 3. **二轮处理 (Round 2 Handling)**： - **Editor 端**：收到 `resubmitted` 的稿件后，Dashboard 需高亮提示。 - **决策分支**：Editor 进入详情页后，有两个选择： - **A. Send for Re-review (二审)**：将新文件再次发送给之前的 Reviewer（或邀请新人）。 - **B. Make Final Decision (终审)**：直接根据修改稿做出 Accept/Reject 决定。 4. **数据模型变更**： - **版本控制**：在 `manuscripts` 表中增加 `version` 字段 (v1, v2...)，或者新建 `manuscript_versions` 表来存储历史版本（MVP 阶段可简化为覆盖 file_path 但保留历史记录）。 - **决策记录**：`decisions` 表需支持存储 revision 类型，并关联到具体版本。 5. **宪法遵从**： - **显性逻辑**：代码中必须清晰定义状态机 (State Machine) 的流转图。 - **文件安全**：作者上传修改稿时，**严禁覆盖**原始投稿文件，必须重命名存储（如 `paper_id_v2.pdf`），以备追溯。"

## Clarifications

### Session 2026-01-31
- Q: How should we implement version control for manuscripts? → A: Create `manuscript_versions` table (1:N)
- Q: How should we structure the revision workflow? → A: Create a dedicated workflow/state machine for revisions
- Q: How should we store revision-specific metadata like the response letter? → A: Create a new `Revision` entity (1:N with Manuscript) to track the revision cycle
- Q: How should re-review assignments be handled? → A: Link re-review requests to existing review assignments (allowing reuse of previous reviewers)
- Q: Should the system automatically create a version snapshot when a revision is requested? → A: Yes, automatically snapshot on request

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Editor Requests Revision (Priority: P1)

The Editor needs the ability to request modifications (Major or Minor) from the Author. This uses a dedicated revision workflow distinct from the final "Accept/Reject" decision.

**Why this priority**: It is the core trigger for the revision loop. Without this, the workflow cannot start.

**Independent Test**: Can be tested by an Editor selecting "Request Revision" on a manuscript and verifying the status updates.

**Acceptance Scenarios**:

1. **Given** a manuscript in `under_review` or `pending_decision` status, **When** the Editor opens the "Request Revision" modal (distinct from Final Decision), **Then** they should see options for "Major Revision" and "Minor Revision".
2. **Given** the Editor selects "Major Revision" and submits, **When** the action completes, **Then** the manuscript status updates to `revision_requested`, a version snapshot is created, and the author is notified.
3. **Given** the Editor selects "Minor Revision", **When** submitted, **Then** the status also updates to `revision_requested` but the revision type is recorded as minor.

---

### User Story 2 - Author Submits Revision (Priority: P1)

The Author needs to be able to respond to the Editor's revision request by uploading a new version of their manuscript and a response letter.

**Why this priority**: Enables the Author to participate in the loop and move the workflow forward.

**Independent Test**: Can be tested by an Author logging in, finding a `revision_requested` manuscript, and submitting new files.

**Acceptance Scenarios**:

1. **Given** a manuscript in `revision_requested` status, **When** the Author views their Dashboard, **Then** they see a "Submit Revision" action/button for that manuscript.
2. **Given** the Author clicks "Submit Revision", **When** they fill out the Response Letter (Rich Text) and upload a new PDF, **Then** the system accepts the submission.
3. **Given** the revision is submitted, **When** the process completes, **Then** the manuscript status updates to `resubmitted`, the version number increments (e.g., v1 -> v2), and the original file is preserved in `manuscript_versions`.

---

### User Story 3 - Editor Processes Resubmission (Priority: P1)

The Editor needs to handle the revised manuscript by either sending it back for review or making a final decision.

**Why this priority**: Closes the loop for the current round of revision.

**Independent Test**: Can be tested by an Editor viewing a `resubmitted` manuscript and choosing the next step.

**Acceptance Scenarios**:

1. **Given** a manuscript in `resubmitted` status, **When** the Editor views their Dashboard, **Then** the manuscript is highlighted or clearly marked as "Resubmitted".
2. **Given** the Editor views the details of a `resubmitted` manuscript, **When** they choose "Send for Re-review", **Then** the status updates to `under_review` and they can assign reviewers (previous or new).
3. **Given** the Editor views the details, **When** they choose "Make Final Decision", **Then** they can Accept or Reject the manuscript immediately.

---

### Edge Cases

- **What happens when an Author tries to submit a revision for a manuscript not in `revision_requested` state?** System must block the action.
- **How does the system handle file naming collisions?** System must automatically append version numbers or timestamps to filenames to prevent overwriting (e.g., `manuscript_id_v2.pdf`).
- **What happens if an Editor tries to "Send for Re-review" without assigning reviewers?** System should prompt to confirm using previous reviewers or require selecting new ones.

## Requirements *(mandatory)*

### Assumptions

- **A-001**: The "Response Letter" will be a Rich Text field in the system, not strictly requiring a file upload (though file attachment is nice to have).
- **A-002**: "Send for Re-review" will transition the manuscript status back to `under_review`, reusing the existing review logic.
- **A-003**: The system's storage backend supports file versioning or renaming (e.g., S3/Supabase Storage) to ensure `paper_id_v2.pdf` does not conflict with `paper_id_v1.pdf`.

### Functional Requirements

- **FR-001**: System MUST allow Editors to trigger a Revision workflow (Major/Minor) distinct from the Final Decision (Accept/Reject).
- **FR-002**: System MUST transition manuscript status from `under_review`/`pending_decision` to `revision_requested` upon revision request.
- **FR-003**: System MUST provide an interface for Authors to upload a new PDF version and enter a Response Letter (Rich Text) when status is `revision_requested`.
- **FR-004**: System MUST increment the manuscript version number (e.g., 1 to 2) upon revision submission.
- **FR-005**: System MUST preserve historical versions of the manuscript file and metadata in a new `manuscript_versions` table and NEVER overwrite the original file in storage.
- **FR-006**: System MUST transition manuscript status to `resubmitted` after Author submits revision.
- **FR-007**: System MUST allow Editors to transition `resubmitted` manuscripts to `under_review` (Re-review) or `published`/`rejected` (Final Decision).
- **FR-008**: System MUST display the "Response Letter" content to the Editor during the re-review/decision process.
- **FR-009**: System MUST allow Editors to reuse previous review assignments or add new ones when initiating a re-review round.
- **FR-010**: System MUST automatically create a version snapshot (ManuscriptVersion) when an Editor requests a revision to lock the state of that round.

### Key Entities

- **Manuscript**: Updated to include `version` (integer) and current `status`.
- **ManuscriptVersion**: New entity to store snapshots of manuscript data (title, abstract, file_path, version_number, created_at) for history. Linked 1:N to Manuscript.
- **Revision**: New entity to track each revision cycle. Attributes: manuscript_id, round_number, request_type (major/minor), response_letter (rich text), status (requested/submitted/processed), requested_at, submitted_at. Linked 1:N to Manuscript.
- **Decision**: Final outcome entity (Accept/Reject).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Editors can successfully complete a "Major Revision" decision flow in under 1 minute.
- **SC-002**: Authors can successfully upload a revised PDF and submit a response letter without errors (100% success rate for valid files).
- **SC-003**: System accurately retains 100% of historical file versions (v1 files are accessible after v2 upload).
- **SC-004**: 100% of `resubmitted` manuscripts appear in the Editor's dashboard with correct status highlighting.
