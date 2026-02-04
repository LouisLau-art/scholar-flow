# Feature Specification: Refine Reviewer Library Logic

**Feature Branch**: `030-reviewer-library-management`  
**Created**: 2026-02-04  
**Status**: Draft  
**Input**: User description: "优先推荐：User Story 3 - 审稿人库逻辑细化 (P3-P4) 这是 PDF 中提到但 029 未涵盖的关键环节。 * 核心目标：将“添加审稿人”与“指派审稿人”逻辑彻底解耦。 * 具体任务： * 库管理：实现“Add to Library”功能（仅录入 Title/Institution/Interests/Homepage，不触发邮件）。 * 指派流程：从已有的“审稿人库”中搜索并指派到具体稿件。 * 字段补全：在 UI 和数据库中补齐 Title (Prof./Dr.) 和 Homepage URL。"

## User Scenarios & Testing *(mandatory)*

## Clarifications

### Session 2026-02-04
- Q: When adding a reviewer to the library, should we immediately create a corresponding user/profile? → A: Create immediately (Ensures data consistency and utilizes existing profile fields).
- Q: Where should Title and Homepage URL be stored? → A: Directly in `public.user_profiles` (Simplifies data access and adheres to existing profile extension patterns).
- Q: How to handle duplicate emails during library entry? → A: Link to existing profile (If the email exists, the library entry links to the existing user instead of erroring).

### User Story 1 - Build Reviewer Library (Priority: P1)

As an Editor, I want to add potential reviewers to a centralized library without sending them an immediate invitation, so that I can build a pool of qualified experts for future assignments.

**Why this priority**: Essential for decoupling the data entry from the workflow process, allowing editors to prepare their reviewer pool in advance.

**Independent Test**: Can be fully tested by adding a new reviewer entry with all required fields (Name, Email, Title, Affiliation) and verifying no email is sent, but the record is searchable in the library.

**Acceptance Scenarios**:

1. **Given** the "Add to Library" form, **When** I enter the reviewer's Title, Full Name, Email, Affiliation, and Homepage, **Then** a new entry is created in the database and no invitation email is triggered.
2. **Given** a reviewer already exists in the library, **When** I try to add them again with the same email, **Then** the system should warn me or update the existing record instead of creating a duplicate.

---

### User Story 2 - Search and Assign from Library (Priority: P1)

As an Editor, I want to search for reviewers in the library and assign them to a specific manuscript, so that I can leverage my pre-built pool of experts efficiently.

**Why this priority**: Core workflow requirement for actual manuscript evaluation.

**Independent Test**: Can be tested by selecting a manuscript, searching for an existing library entry, and clicking "Assign", which should then trigger the invitation flow.

**Acceptance Scenarios**:

1. **Given** a manuscript in the "Under Review" or "Pre-check" state, **When** I open the assignment interface and search by "Research Interests" or "Name", **Then** matching library entries are displayed.
2. **Given** a selected reviewer from the library, **When** I click "Assign to Manuscript", **Then** a review assignment record is created and an invitation email is sent to the reviewer.

---

### User Story 3 - Reviewer Profile Completion (Priority: P2)

As an Editor, I want to see and edit full details of reviewers in the library, including their Title (e.g., Prof., Dr.) and Homepage URL, so that I can make better-informed assignment decisions.

**Why this priority**: Improves the quality of the reviewer pool and helps in verifying expertise.

**Independent Test**: View a reviewer's profile in the library and edit the "Homepage URL" field.

**Acceptance Scenarios**:

1. **Given** the Reviewer Library list, **When** I click on a reviewer, **Then** I see their Title, Institution, Research Interests, and Homepage URL.
2. **Given** a reviewer entry, **When** I update their Title or Homepage, **Then** the changes are saved and reflected across the system.

---

### Edge Cases

- **Existing Auth Users**: What happens if an editor adds an email that already belongs to a registered Author? (Assumption: The system should link the library entry to the existing User Profile).
- **Deleted Reviewers**: How should the system handle library entries that have been assigned to manuscripts but are later removed from the library? (Assumption: Keep the assignment records intact for audit purposes, but mark the entry as "Inactive" in the library).
- **Empty Interests**: How does the search behave if a reviewer has no research interests listed? (Assumption: Search should still find them by Name or Institution).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated "Reviewer Library" management interface (Add/Search/List).
- **FR-002**: "Add to Library" MUST capture: Title (Enum: Prof., Dr., Mr., Ms., etc.), Full Name, Email (Unique), Affiliation, Research Interests (Tag-style), and Homepage URL.
- **FR-003**: System MUST NOT send any automatic emails when a reviewer is simply added to the library.
- **FR-004**: Adding a new reviewer to the library MUST immediately create a record in `auth.users` (with a random password) and `public.user_profiles`.
- **FR-005**: If the provided email already exists in the system, the library entry MUST link to the existing `user_profiles` record and update its metadata if necessary.
- **FR-006**: The Assignment UI MUST allow searching the library by Name, Email, Affiliation, or Research Interests using full-text search.
- **FR-007**: System MUST support one-click assignment of a library entry to a manuscript, which triggers the invitation email.
- **FR-008**: System MUST persist `Title` and `Homepage URL` directly in the `public.user_profiles` table.
- **FR-009**: System MUST validate that Homepage URL is a valid URL format.

### Key Entities *(include if feature involves data)*

- **Reviewer Library Entry**: Represents a potential reviewer. Linked to `user_profiles`. Includes `Title`, `Homepage URL`, `Institution`, and `Research Interests`.
- **Review Assignment**: Connects a Reviewer Library Entry to a Manuscript for a specific review cycle.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Editors can add a new reviewer to the library in under 30 seconds.
- **SC-002**: Library search results for 1,000+ entries return in under 500ms.
- **SC-003**: 100% of review invitations sent from the library include the correct Title and Affiliation in the email template.
- **SC-004**: System successfully prevents duplicate reviewer entries based on Email uniqueness.