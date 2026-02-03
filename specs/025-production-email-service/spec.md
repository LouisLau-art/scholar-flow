# Feature Specification: Production Email Service

**Feature Branch**: `025-production-email-service`
**Created**: 2026-02-03
**Status**: Draft
**Input**: User description: "开启 Feature 026: 生产级邮件服务集成 (Production Email Service). 目标：取消之前所有邮件发送的 print() 模拟，接入真实的发送服务。 核心需求： 1. **服务集成**：后端 Python 集成 Resend SDK (或 SMTP)。 2. **场景覆盖**： - 审稿人邀请（含真实的 Token 链接）。 - 稿件状态变更通知（录用/退修）。 - 财务账单通知（带 PDF 链接）。 3. **安全与回退**：如果邮件发送失败，必须记录在 `email_logs` 中，且不能中断当前的 API 响应。"

## Clarifications

### Session 2026-02-03
- Q: Which email provider/protocol should be prioritized? → A: Resend (Modern SDK) for better observability and tracking.
- Q: What is the retry policy for temporary delivery failures? → A: Automatic retries with exponential backoff.
- Q: How should email templates be managed? → A: Dynamic HTML templates (Jinja2) for consistent branding and personalization.
- Q: What security constraints apply to reviewer access links? → A: Signed tokens with a 7-day expiration period.
- Q: What level of detail should be stored in the audit log? → A: Metadata, subject, and status only (no sensitive body content).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reviewer Invitation (Priority: P1)

Editors need to send real email invitations to reviewers so they can access the review interface via a secure link without logging in manually.

**Why this priority**: Essential for the peer review workflow; reviewers are external users and rely on email to know they have a task.

**Independent Test**: Can be tested by inviting a reviewer with a controlled email address and verifying receipt of the email with a working link that expires after 7 days.

**Acceptance Scenarios**:

1. **Given** an editor assigns a reviewer to a manuscript, **When** the assignment is confirmed, **Then** the reviewer receives an email containing the manuscript title and a direct access link with a valid token.
2. **Given** the email service is down, **When** the editor invites a reviewer, **Then** the system records the invitation in the database, schedules an automatic retry, but displays a success message to the editor (non-blocking).

---

### User Story 2 - Author Status Notifications (Priority: P1)

Authors need to receive immediate email updates when their manuscript status changes (e.g., Rejected, Revision Requested, Accepted) to take timely action.

**Why this priority**: Keeps authors engaged and informed, reducing manual status checks.

**Independent Test**: Can be tested by changing a manuscript status as an editor and verifying the author receives the correct personalized HTML template.

**Acceptance Scenarios**:

1. **Given** a manuscript is marked as "Revision Requested", **When** the decision is saved, **Then** the author receives an email with the editor's comments (or link to them) and instructions for resubmission.
2. **Given** a manuscript is "Accepted", **When** the decision is finalized, **Then** the author receives an acceptance email.

---

### User Story 3 - Financial Invoice Delivery (Priority: P2)

Authors whose papers are accepted need to receive invoice notifications with payment details to proceed with publication.

**Why this priority**: Critical for revenue collection and the final publication step.

**Independent Test**: Can be tested by generating an invoice and verifying the email contains the correct amount and a link to the invoice/payment page.

**Acceptance Scenarios**:

1. **Given** an invoice is generated for an accepted paper, **When** the invoice status is set to "Pending", **Then** the author receives an email with the invoice details and a link to the payment portal or PDF download.

---

### User Story 4 - Resilient Error Handling (Priority: P1)

System administrators need to ensure that email delivery failures do not crash the application or prevent business logic from completing.

**Why this priority**: Prevents external service outages from affecting core system stability.

**Independent Test**: Can be tested by configuring invalid credentials and verifying that core actions still complete while an entry is added to the log with a "Pending Retry" status.

**Acceptance Scenarios**:

1. **Given** the email provider is unreachable, **When** a trigger event occurs (e.g., invitation), **Then** the API returns a 200 OK response, the business entity is created, and an entry is added to the audit log with the error details.

### Edge Cases

- **Invalid Email Address**: System should capture the bounce or rejection if possible and log it as a terminal failure.
- **Rate Limiting**: If the email provider rate limits the service, the system should log the error and apply exponential backoff retries.
- **Expired Tokens**: Reviewer links accessed after 7 days should redirect to a friendly "Link Expired" page with instructions to contact the editor.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST integrate with Resend (transactional email service) via its official Python SDK.
- **FR-002**: System MUST send a "Reviewer Invitation" email containing a secure, unique access URL with a 7-day expiration token.
- **FR-003**: System MUST send a "Status Update" email to the author when a manuscript transitions to "Revision Requested", "Rejected", or "Approved".
- **FR-004**: System MUST send an "Invoice Generated" email to the author containing the amount and a link to the payment/invoice page when an invoice is created.
- **FR-005**: System MUST perform email sending asynchronously using a background task queue (e.g., FastAPI BackgroundTasks or Celery) to ensure no impact on API response latency.
- **FR-006**: System MUST persist a record of every email attempt in a centralized audit log, capturing recipient, subject, status, provider ID, and retry count.
- **FR-007**: System MUST implement an automatic retry mechanism with exponential backoff for transient delivery failures.
- **FR-008**: System MUST support dynamic HTML templates (Jinja2) for all outbound emails to ensure consistent branding.

### Key Entities

- **Email Log**: Records the history of all email attempts. Attributes: `recipient`, `subject`, `status`, `provider_id`, `retry_count`, `error_details`, `created_at`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of triggered email events result in an audit log entry.
- **SC-002**: API response time (TTFB) for actions triggering emails remains below 200ms for 95% of requests.
- **SC-003**: System successfully recovers and delivers 90% of transiently failed emails within 4 hours via retries.
- **SC-004**: 0% of email delivery failures result in a 500 Internal Server Error for the end user.