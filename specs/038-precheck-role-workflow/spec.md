# Feature Specification: Pre-check Role Workflow (ME → AE → EIC)

**Feature Branch**: `038-precheck-role-workflow`  
**Created**: 2026-02-05  
**Last Updated**: 2026-02-06  
**Status**: Approved  
**Input**: User description: "Feature 038: Pre-check 角色工作流（ME 分配 AE → AE 技术质检 → EIC 学术初审）+ 可视化待办与时间戳"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Managing Editor performs intake pre-check first (Priority: P1)

As a Managing Editor (ME), I can perform the initial technical/administrative intake check before assigning the manuscript to an AE, so that only workable submissions enter the follow-up queue.

**Why this priority**: 最新业务反馈明确“投稿前期先由 ME 审查”，这是队列分工的入口规则。

**Independent Test**: Create a newly submitted manuscript, open ME pre-check view, complete ME pre-check, and verify only then the manuscript can be assigned to an AE.

**Acceptance Scenarios**:

1. **Given** a manuscript is newly submitted, **When** ME completes intake pre-check as pass, **Then** the system allows assignment to a specific AE and records timestamp/actor.
2. **Given** a manuscript is newly submitted, **When** ME determines it needs author corrections, **Then** the manuscript enters revision-request flow and AE becomes follow-up owner after assignment.

---

### User Story 2 - Assistant Editor executes follow-up operations (Priority: P2)

As an Assistant Editor (AE), I can follow up the manuscripts that passed ME intake, including author-revision follow-up and reviewer-operation handoff, so that workflow execution is continuous.

**Why this priority**: AE 是运营执行角色，负责把已通过 ME 入口审查的稿件持续推进。

**Independent Test**: With a manuscript assigned by ME, AE can process it and move it to the next expected queue/state with visible timestamps.

**Acceptance Scenarios**:

1. **Given** a manuscript is assigned to AE, **When** AE records technical follow-up completion, **Then** manuscript becomes ready for academic pre-check (EIC queue).
2. **Given** manuscript needs author correction, **When** AE follows up and author resubmits, **Then** manuscript returns to AE queue with complete trace.

---

### User Story 3 - EIC performs academic pre-check and decision routing (Priority: P3)

As an Editor-in-Chief (EIC), I can perform academic pre-check and route the manuscript either to peer review or to decision stage, so that academic authority stays explicit and auditable.

**Why this priority**: 学术判断必须由学术角色做出，且与行政执行分离。

**Independent Test**: With a manuscript in EIC pre-check queue, EIC makes a decision and manuscript is routed to under-review flow or decision flow with audit records.

**Acceptance Scenarios**:

1. **Given** a manuscript is awaiting academic pre-check, **When** EIC passes it, **Then** manuscript enters reviewer assignment/under-review workflow.
2. **Given** a manuscript is awaiting academic pre-check, **When** EIC decides not to continue external review, **Then** manuscript is routed into `decision` stage (not directly rejected), and final reject is produced only from decision flow.

---

### Edge Cases

- **Unassigned manuscript**: AEs cannot act until ME finishes intake and assigns AE.
- **Role misuse**: non-ME cannot perform intake assignment; non-EIC cannot perform academic pre-check routing.
- **Reassignment mid-work**: new AE inherits context/history; old AE drops from actionable queue.
- **Reject governance**: `pre_check`, `under_review`, `resubmitted` must not directly transition to `rejected`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST enforce ME-first intake pre-check before AE assignment.
- **FR-002**: The system MUST support assigning each pre-checked manuscript to one AE and allow ME reassignment with audit trail.
- **FR-003**: The system MUST provide role-specific queues/views for ME (intake), AE (operational follow-up), and EIC (academic pre-check).
- **FR-004**: The system MUST enforce role permissions so only ME can perform intake/assignment and only EIC can perform academic pre-check routing.
- **FR-005**: The system MUST record timestamps for key steps: intake checked, assigned, AE follow-up updated, EIC routed.
- **FR-006**: The system MUST keep a clear audit trail for role actions (who, when, what changed, optional reason).
- **FR-007**: The system MUST prevent direct reject from `pre_check`, `under_review`, and `resubmitted`; reject MUST be finalized in `decision/decision_done`.
- **FR-008**: The system MUST show explicit user feedback after each role action (state changed + next owner/queue).

### Key Entities

- **Pre-check Intake Record**: ME intake decision and metadata.
- **Pre-check Assignment**: manuscript-to-AE responsibility record.
- **Academic Pre-check Routing**: EIC routing outcome to review/decision path.

### Assumptions & Dependencies

- Submitted manuscripts and editor dashboard already exist.
- Roles ME/AE/EIC are available and enforceable in RBAC.
- Downstream review and decision modules are available.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ME can complete intake + assign AE within 30 seconds median in UAT.
- **SC-002**: 95%+ of intake/assignment/routing actions produce audit entries with actor + timestamp.
- **SC-003**: AE can process assigned manuscripts to EIC-ready state within 5 minutes (happy path, excluding manuscript reading).
- **SC-004**: 100% of rejected manuscripts in sampled UAT runs are finalized from `decision/decision_done`, not from `pre_check`/`under_review`/`resubmitted`.
