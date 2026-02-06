# Feature Specification: Reviewer Invitation & Magic Link

**Feature Branch**: `039-reviewer-magic-link`  
**Created**: 2026-02-06  
**Status**: Draft  
**Input**: User description: "Feature 038: Invitation & Magic Link (邀请与魔术链接) * 核心痛点：审稿人忘记密码，或不愿注册。 * 解决方案： * 邀请机制：重构邀请弹窗，支持从 Library 中搜索并发送邀请邮件。 * Token 生成：后端生成一个带有签名的 Token（有效期 7-14 天），拼接到 URL 中（如 .../review/invite?token=xyz）。 * 免登录验证：后端中间件识别该 Token，临时授予 Reviewer 权限访问特定稿件。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Editor invites Reviewer from Library (Priority: P1)

As an Editor, I want to search for a reviewer in the existing Reviewer Library and send them an invitation email with a "Magic Link", so that I can quickly assign reviewers without waiting for them to register or remember passwords.

**Why this priority**: Streamlines the invitation process and leverages the pre-built Reviewer Library (Feature 037/030).

**Independent Test**:
1. Open "Invite Reviewer" modal on a manuscript.
2. Search for an existing reviewer in the library.
3. Click "Invite".
4. Verify an email is sent to that reviewer containing a unique link.
5. Verify a `review_assignment` is created with status `invited` (or similar).

**Acceptance Scenarios**:

1. **Given** a manuscript in `under_review` (or `pre_check`), **When** Editor searches "Smith" in the invite modal, **Then** matching results from the Reviewer Library are shown.
2. **Given** a selected reviewer, **When** Editor sends the invite, **Then** the system generates a secure token and sends an email with the link `.../review/invite?token=...`.
3. **Given** the invite is sent, **Then** the assignment status updates to "Invited".

---

### User Story 2 - Reviewer accesses Manuscript via Magic Link (Priority: P1)

As a Reviewer, I want to click the link in my email and immediately access the manuscript review page without entering a password, so that I can start my work with zero friction.

**Why this priority**: Solves the core pain point of "forgot password" / "unwilling to register".

**Independent Test**:
1. Obtain a valid magic link (from email or DB log).
2. Open it in an incognito window (no existing session).
3. Verify the system logs the user in (as a "guest reviewer" or the specific reviewer account) and redirects to the review page for *that specific manuscript*.
4. Verify the reviewer *cannot* access other manuscripts or editor pages.

**Acceptance Scenarios**:

1. **Given** a valid, unexpired token, **When** Reviewer accesses the URL, **Then** they are authenticated and redirected to the Review Workspace for the target manuscript.
2. **Given** the reviewer is already logged in as a different user, **When** they click the link, **Then** the system should either prompt to switch accounts or handle the dual-identity safely (e.g., restricted view).
3. **Given** a magic link, **When** accessed, **Then** the user has permission to read the manuscript and submit a review, but *not* to access administrative features.

---

### User Story 3 - Token Security & Expiration (Priority: P2)

As a System Admin, I want magic links to expire after a set time (7-14 days) and be invalid if tampered with, so that unauthorized access is prevented.

**Why this priority**: Security is critical for "no-password" access.

**Independent Test**:
1. Generate a token.
2. Manually modify one character in the token string.
3. Try to access the URL. Verify access is denied.
4. (Mock test) Fast-forward time by 15 days. Verify the original token is rejected as expired.

**Acceptance Scenarios**:

1. **Given** a token generated >14 days ago, **When** accessed, **Then** show an "Expired Link" error page with an option to request a new link.
2. **Given** a malformed or tampered token, **When** accessed, **Then** show an "Invalid Link" error.
3. **Given** a token for Manuscript A, **When** the user tries to manually navigate to Manuscript B, **Then** access is denied (scope restriction).

### Edge Cases

- **Reviewer account exists**: If the email matches an existing registered user, the magic link should still work without requiring the password, logging them in as that user (or a scoped session).
- **Token reuse**: Can the token be used multiple times? (Yes, for the duration of the review period, to allow returning to finish work).
- **Revocation**: If the editor cancels the invitation, the token must immediately stop working.

## Clarifications

### Session 2026-02-06

- **Token Implementation**: Use **Stateless JWT** (embedded in URL) for scalability and simplicity, signed with the backend secret. This avoids a new DB table for tokens.
- **Session Handling**: Magic link grants a **Scoped Guest Session** (cookie-based) specifically for that manuscript review, independent of main user login. This handles the "already logged in" edge case cleanly by isolating the review context.
- **Expiration Policy**: Set expiration to **14 days** (matching the default review deadline), renewable if the editor re-sends the invite.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a capability to search the `reviewer_library` (or `user_profiles` marked as reviewers) within the Invite Modal.
- **FR-002**: The system MUST generate a cryptographically secure **JWT (HS256)** token containing at least: `assignment_id`, `reviewer_id`, `manuscript_id`, and `expiration_timestamp`.
- **FR-003**: The token MUST be valid for a configurable period (default **14 days**).
- **FR-004**: The system MUST allow Editors to send an email template containing the magic link.
- **FR-005**: The system MUST provide a validation mechanism that verifies the token from the URL query parameter `?token=...`.
- **FR-006**: Upon successful token validation, the system MUST grant a session/context with `read` access to the specific manuscript and `write` access to the associated review report.
- **FR-007**: If a token is expired or invalid, the system MUST deny access and display a user-friendly error message.
- **FR-008**: The system MUST revoke token validity if the review assignment is cancelled by the editor (checked via DB status lookup, even if JWT is valid).
- **FR-009**: The system MUST support "guest session" isolation (or explicit account switching) to allow reviewing without disrupting an existing unrelated user session.

### Key Entities

- **Review Token**: A temporary credential (**JWT payload structure**) linking a Reviewer to a Manuscript Assignment.
- **Review Assignment**: The record tracking the relationship between a manuscript and a reviewer (Status: Invited, Accepted, Completed, Cancelled).

### Assumptions & Dependencies

- **Reviewer Library** (Feature 037/030) is implemented and populated.
- **Email Service** (SendGrid/SMTP) is configured and operational.
- **Reviewer Workspace** page exists (or will be built in Feature 039) to receive the user.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Reviewers can access the review page within 5 seconds of clicking the email link (no login screen).
- **SC-002**: 100% of invalid or expired tokens are rejected by the system.
- **SC-003**: Editors can search and send an invite to a library reviewer in under 30 seconds.
- **SC-004**: System prevents access to any manuscript other than the one specified in the token.