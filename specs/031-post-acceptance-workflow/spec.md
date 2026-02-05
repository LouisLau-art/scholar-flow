# Feature Specification: Enhance Post-Acceptance Workflow

**Feature Branch**: `031-post-acceptance-workflow`  
**Created**: 2026-02-04  
**Status**: Draft  
**Input**: User description: "Feature 031: 出版流水线增强 (Post-Acceptance Workflow) * 背景: 目前系统状态机虽然支持 Layout / English Editing / Proofreading，但详情页缺乏推动这些状态流转的显式操作入口。 * 目标: * 在详情页（User Story 2 的基础上）增加状态控制按钮。 * 实现从 Accepted -> Layout -> English Editing -> Proofreading -> Published 的流转逻辑。 * (可选) 集成之前 Feature 024 的 Payment Gate 和 Production Gate 到这个流程中。"

## User Scenarios & Testing *(mandatory)*

## Clarifications

### Session 2026-02-04
- Q: Is the Production Gate (Final PDF check) mandatory? → A: Configurable (Controlled by `PRODUCTION_GATE_ENABLED` env var, default OFF for MVP).

### User Story 1 - Sequential Status Progression (Priority: P1)

As an Editor, I want clear action buttons on the manuscript details page to advance a manuscript through the post-acceptance stages (Layout, English Editing, Proofreading), so that I can track its production progress accurately.

**Why this priority**: Core functionality gap. The states exist in the database but are unreachable via the UI.

**Independent Test**: Navigate to an "Accepted" manuscript and verify buttons exist to move it to "Layout", then "English Editing", then "Proofreading".

**Acceptance Scenarios**:

1. **Given** a manuscript in `Accepted` status, **When** I click "Start Layout", **Then** the status updates to `Layout` and the audit log records the action.
2. **Given** a manuscript in `Layout` status, **When** I click "Start English Editing", **Then** the status updates to `English Editing`.
3. **Given** a manuscript in `English Editing` status, **When** I click "Start Proofreading", **Then** the status updates to `Proofreading`.

---

### User Story 2 - Publication with Gates (Priority: P1)

As an Editor, I want to publish a manuscript only after verifying that payment has been received (Payment Gate) and the final PDF is uploaded (Production Gate, optional), so that we don't publish incomplete or unpaid work.

**Why this priority**: Ensures business compliance (revenue assurance) and quality control before public release.

**Independent Test**: Try to publish a manuscript with an unpaid invoice and verify it is blocked. Then mark as paid and publish successfully.

**Acceptance Scenarios**:

1. **Given** a manuscript in `Proofreading` status with an unpaid invoice, **When** I click "Publish", **Then** the system shows an error message citing "Payment Pending".
2. **Given** a manuscript in `Proofreading` status with a paid invoice, **When** I click "Publish", **Then** the status updates to `Published` and a DOI is assigned (mock/real).

---

### Edge Cases

- **Skip Stages**: Can an editor skip directly from `Accepted` to `Published`? (Assumption: No, linear progression is enforced to ensure quality steps, though Admins might override).
- **Reversion**: What happens if an error is found during Proofreading? (Assumption: Editor should be able to revert to `Layout` or `English Editing`).
- **Concurrent Edits**: What if two editors try to update the status simultaneously? (Assumption: Optimistic locking or last-write-wins with audit log).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide status transition buttons on the Manuscript Details page corresponding to the current state's valid next steps.
- **FR-002**: The transition path MUST be: `Accepted` -> `Layout` -> `English Editing` -> `Proofreading` -> `Published`.
- **FR-003**: System MUST enforce a Payment Gate before allowing transition to `Published` (Invoice `status` must be `paid` or `waived`).
- **FR-004**: System MUST conditionally check for `final_pdf_path` before publishing, based on the `PRODUCTION_GATE_ENABLED` environment variable (default: false).
- **FR-005**: All status transitions MUST be logged in the `status_transition_logs` table.
- **FR-006**: System MUST allow reverting status (e.g., from `Proofreading` back to `Layout`) for correction purposes.

### Key Entities

- **Manuscript**: Updates to `status`, `published_at`, `doi`.
- **Invoice**: Checked for `status` (Payment Gate).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Editors can transition a manuscript through all 4 post-acceptance stages without page refreshes (optimistic UI) or errors.
- **SC-002**: 100% of published manuscripts have a `paid` or `waived` invoice.
- **SC-003**: Status transitions are logged with the correct actor ID and timestamp.