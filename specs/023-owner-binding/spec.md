# Feature Specification: Owner Binding

**Feature Branch**: `023-owner-binding`  
**Created**: 2026-02-02  
**Status**: Draft  
**Input**: User description: 'Feature 023: 稿件归属人绑定 (KPI Owner Binding)。

背景：在最终验收测试中发现，系统缺失了“稿件归属人 (Owner)”的绑定功能。这是业务方（老板）计算绩效的核心依据，必须在稿件初审阶段完成绑定。

核心需求如下：
1. **数据模型变更 (Schema Change)**：
   - 在 `manuscripts` 表中新增字段 `owner_id` (UUID, Foreign Key -> `auth.users` 或 `profiles`)。
   - 该字段允许为空（自然投稿），也允许指向某个具体的内部员工（Editor/Admin）。

2. **后端 API 更新**：
   - 修改 `get_manuscript_details` 接口，返回 `owner` 的详细信息（姓名）。
   - 修改 `update_manuscript` 接口，允许 PATCH 更新 `owner_id`。

3. **前端 UI 实现 (Editor Interface)**：
   - **位置**：在 Editor Dashboard 的 **稿件详情页 (Manuscript Details)** 右侧边栏 (Sidebar) 或 元数据区域。
   - **组件**：新增一个 "Internal Owner / Invited By" 的 **搜索下拉框 (Combobox)**。
   - **数据源**：下拉框仅列出角色为 `editor` 或 `admin` 的内部人员（排除 Author 和 Reviewer）。
   - **交互**：Editor 可以随时修改这个字段，修改后自动保存并提示 "Owner updated"。

4. **列表页展示 (Optional)**：
   - 在 Editor 的稿件列表页 (Table)，增加一列 "Owner"，显示该稿件的负责人姓名，方便老板一眼看出是谁的业绩。

5. **宪法遵从**：
   - **显性逻辑**：后端在处理 `owner_id` 更新时，必须校验传入的 ID 是否确实是内部员工（防止误操作绑定给外部作者）。'

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Bind owner during initial review (Priority: P1)

When a manuscript reaches the editor pipeline, the assigned editor must declare the internal owner so leadership can attribute KPIs before review work begins. The owner field should live in the manuscript detail sidebar and auto-save whenever the editor chooses an internal staff member.

**Why this priority**: This binding step is explicitly required by the business owner to compute KPI ownership, so the workflow cannot proceed without data in place before review assignments or decisions happen.

**Independent Test**: Open the manuscript details screen for a known manuscript, select an internal owner from the new combobox, and verify the payload that hits `PATCH /api/v1/manuscripts/{id}` contains the `owner_id` and triggers the "Owner updated" toast.

**Acceptance Scenarios**:

1. **Given** an under-review manuscript with no owner, **When** the editor selects an internal staff member from the combobox, **Then** the details sidebar auto-saves the new `owner_id`, displays "Owner updated", and the detail API now returns the owner metadata.
2. **Given** the editor reopens the same manuscript, **When** they view the owner field, **Then** the previously selected owner is pre-populated, and the system still allows changing to another internal staffer without manual save buttons.

---

### User Story 2 - Expose owner through APIs (Priority: P2)

Leadership and downstream services need to know who owns each manuscript without querying the UI. The manuscript detail endpoint must surface the owner information so any consumer can show the attribute, and API clients must receive a 400 if someone attempts to set an owner who is not an internal editor/admin.

**Why this priority**: Without the API backing, the UI cannot stay in sync and automation cannot aggregate KPI data; also, enforcing internal-user validation inside the API prevents mis-attribution.

**Independent Test**: Call `GET /api/v1/manuscripts/{id}` before and after assigning an owner and verify the response includes an `owner` object containing `id` and `full_name`. Independently attempt to `PATCH` with a non-staff `owner_id` and expect HTTP 400 with a clear message.

**Acceptance Scenarios**:

1. **Given** a manuscript with an owner, **When** the detail API is called, **Then** the payload includes `owner_id` plus the owner's name; if owner is null, the API returns `owner: null`.
2. **Given** a request to `PATCH` `owner_id` with a user who lacks editor/admin role, **When** the breakpoint fires, **Then** the API rejects it with a 4xx status and leaves the existing owner untouched.

---

### User Story 3 - Owner column on manuscript list (Priority: P3)

Management relies on a single glance at the editor manuscript table to see KPI assignments. Adding an "Owner" column that displays the owner name (or "Unassigned") gives business users a quick audit trail.

**Why this priority**: It is explicitly noted as optional, but adds transparency for KPI tracking and keeps the list page aligned with the new owner data created in the detail view.

**Independent Test**: Load the editor manuscript list and ensure each row shows the owner name that matches the owner returned by the detail API, even when the table is filtered or paginated.

**Acceptance Scenarios**:

1. **Given** a mix of manuscripts with and without owners, **When** the editor opens the pipeline list, **Then** every row shows the correct owner name or "Unassigned" and updates in under a second when the owner is changed from the detail view.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- What happens when an editor removes the owner (sets it to null) immediately after review assignment? The UI must show "Unassigned" and the API must accept null without validation for existing staff, so the manuscript simply becomes ownerless again.
- How does the system behave when the chosen owner is disabled or deleted while still referenced? The detail endpoint must treat owner metadata as missing (null) and the API must allow selecting a new owner without failing.
- What happens when the combobox query returns no internal staff due to Supabase downtime? The UI should display a disabled dropdown and a contextual message "Unable to fetch owners; try again" while the server still permits owner updates via API when manual selection is later possible.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST add an optional `owner_id` UUID column to the `manuscripts` table that is nullable by default and constrained to reference the `auth.users`/`user_profiles` of internal staff.
- **FR-002**: System MUST surface the owner metadata (id, full name, roles) when `GET /api/v1/manuscripts/{id}` or similar detail endpoints are invoked.
- **FR-003**: Editor clients MUST be able to `PATCH /api/v1/manuscripts/{id}` with an `owner_id` payload, and the backend MUST persist the update, returning the refreshed owner data in the response.
- **FR-004**: Backend MUST validate every incoming `owner_id` update to ensure it belongs to a user with `editor` or `admin` role and return an informative 4xx error if not.
- **FR-005**: The manuscript detail sidebar MUST render an "Internal Owner / Invited By" combobox that only lists internal staff (editors/admins), selects the current owner, and automatically saves on selection, showing "Owner updated" on success.
- **FR-006**: The pipeline manuscript table MUST display an "Owner" column with the owner full name or the text "Unassigned" if the field is null, reloading instantly when ownership changes.
- **FR-007**: The UI MUST handle owner fetch failures gracefully by disabling the combobox and prompting editors to retry later without blocking other manuscript edits.

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **Manuscript**: Represents the submission record with metadata such as `id`, `title`, `status`, and the new `owner_id` pointer that may be null for natural submissions but otherwise references an internal KPI owner.
- **Internal Owner**: An editor or admin user identity (sourced from `auth.users`/`user_profiles`) that carries attributes `id`, `full_name`, `roles`, and is the business owner used for KPI reporting.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: 100% of manuscripts returned by the detail endpoint include either `owner` metadata or `null`, ensuring downstream KPI reports always know whether an owner exists.
- **SC-002**: Editors can change the owner via the combobox and see the "Owner updated" confirmation within two seconds for at least 95% of attempts during standard load testing.
- **SC-003**: The manuscript list shows a populated Owner column for every row and refreshes the displayed name within one second when the owner is edited on the detail page.
- **SC-004**: Any attempt to assign a non-internal owner receives a clear 4xx response, preserving existing owner data and eliminating KPI misattribution reports.

## Assumptions

- The Supabase schema can be migrated to include `manuscripts.owner_id`, and the foreign key can point to `auth.users` (or `user_profiles`) without conflicting with existing RLS policies.
- Editors and admins are already represented in `user_profiles` with distinguishable roles so the combobox can filter by role and the backend can verify the role before persisting.
- The optional list column can reuse the same owner metadata that powers the detail view without requiring additional backend endpoints.
