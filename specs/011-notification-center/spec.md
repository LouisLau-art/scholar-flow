# Feature Specification: Notification Center

**Feature Branch**: `011-notification-center`
**Created**: 2026-01-30
**Status**: Implemented
**Input**: User description: "开启 Feature 011: 智能化通知中心 (Notification Center)。 本项目是一个学术投稿系统，本功能旨在建立一套全方位的通知体系，涵盖邮件通知与站内信通知。 核心需求如下： 1. **多端通知逻辑**： - 当系统内稿件状态发生变更（如：从 Submitted 变为 Under Review，或录用 Accepted）时，必须同时触发“电子邮件”和“站内信”。 - 站内信：在前端（Next.js）右上角增加一个带红点的铃铛图标，展示未读消息列表。 - 电子邮件：后端（FastAPI）调用邮件服务发送正式的英文通知邮件。 2. **用户角色覆盖**： - **对作者 (Author)**：通知投稿成功、需要修稿、录用通知、收到账单、文章正式上线。 - **对审稿人 (Reviewer)**：发送审稿邀请（含免登录 Token 链接）、审稿任务提醒、感谢信。 - **对编辑 (Editor)**：提醒有新投稿待处理、审稿意见已集齐、作者已修回、财务已确认到账。 3. **核心功能：自动催办 (Auto-Chasing)**： - 系统需支持后台自动任务。如果审稿人在截止日期前 24 小时未提交报告，系统自动发送一封语气礼貌的催办邮件。 4. **技术实现约束**： - **数据模型**：在 Supabase 中建立 `notifications` 表，记录消息内容、接收人、关联稿件 ID、是否已读。 - **邮件模板**：所有邮件必须使用专业、地道的学术英语模板（参考顶级期刊语气）。 - **异步处理**：发送邮件必须是异步的，不能阻塞主业务流程（建议后端使用 BackgroundTasks）。 - **安全性**：审稿邀请邮件中的 Token 链接必须与 007/008 模块的逻辑严格一致。 5. **宪法遵从**： - 必须在代码中包含详细的中文注释。 - 实现“显性逻辑”，严禁使用复杂的第三方通知框架，优先使用 Supabase 的实时订阅 (Realtime) 或简单的轮询实现站内信。"

## Clarifications

### Session 2026-01-30
- Q: 如何防止自动催办邮件重复发送 (Idempotency)? → A: 在 `review_assignments` 表中增加 `last_reminded_at` 字段，调度器仅筛选该字段为空且截止时间临近的记录。
- Q: 后端使用哪个库发送邮件? → A: 使用 Python 标准库 `smtplib` 和 `email.mime` 以保持显性逻辑和轻量依赖。
- Q: 站内信实时性如何实现? → A: 使用 Supabase Realtime 监听 `notifications` 表的 `INSERT` 事件。
- Q: 邮件模板引擎选用什么? → A: 使用 Jinja2，以便将 HTML 模板与代码逻辑分离，易于维护学术英语文案。
- Q: 内部定时任务 API (`/internal/cron/*`) 如何鉴权? → A: 使用 `X-Admin-Key` Header 校验，密钥存储在环境变量中。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-channel Status Notifications (Priority: P1)

As a User (Author/Reviewer/Editor), I want to receive immediate notifications via Email and In-App Bell whenever a relevant manuscript status changes, so that I stay informed without constant page refreshing.

**Why this priority**: Core functionality ensuring users are aware of workflow progression.

**Independent Test**: Trigger a status change (e.g., submit a manuscript) and verify (1) `notifications` table entry created, (2) UI bell icon shows red dot, (3) Email received (mocked/logged).

**Acceptance Scenarios**:

1.  **Given** an Author submits a manuscript, **When** the status changes to `submitted`, **Then** the Author receives a "Submission Acknowledgement" email and an in-app notification.
2.  **Given** an Editor logs in, **When** a new submission arrives, **Then** the bell icon shows an unread badge.
3.  **Given** a Reviewer is invited, **When** the invitation is sent, **Then** they receive an email with a secure, valid Token link (matching 007 logic).

---

### User Story 2 - In-App Notification Center (Priority: P2)

As a User, I want to view a list of my unread messages by clicking the bell icon and mark them as read, so that I can manage my pending alerts.

**Why this priority**: Provides a persistent history of events within the application.

**Independent Test**: Click the bell icon, see list, click a message, verify red dot count decreases.

**Acceptance Scenarios**:

1.  **Given** unread notifications, **When** clicking the bell icon, **Then** a dropdown/popover displays the top 5 recent unread messages.
2.  **Given** a notification list, **When** clicking "Mark all as read" or clicking a single item, **Then** the red dot count updates immediately.
3.  **Given** no unread messages, **When** viewing the bell, **Then** it shows an empty state illustration.

---

### User Story 3 - Automated Chasing (Priority: P3)

As an Editor, I want the system to automatically email Reviewers who are close to their deadline (24h), so that I don't have to manually chase them.

**Why this priority**: Reduces administrative burden and speeds up the review process.

**Independent Test**: Simulate a review assignment with a deadline 23 hours from now, trigger the background scheduler, and verify a "Reminder" email is queued.

**Acceptance Scenarios**:

1.  **Given** a pending review assignment due in < 24 hours, **When** the scheduled task runs, **Then** a polite reminder email is sent to the reviewer.
2.  **Given** a review assignment due in > 24 hours, **When** the task runs, **Then** no email is sent.
3.  **Given** a completed review, **When** the task runs, **Then** no reminder is sent.

## Edge Cases

-   **Email Failure**: If the email service is down (SMTP error), the system MUST log the error but NOT fail the main transaction (e.g., manuscript submission should still succeed).
-   **Duplicate Chasing**: The auto-chasing logic MUST ensure it doesn't send the same "24h reminder" multiple times (idempotency).
-   **Empty Inbox**: New users with zero notifications should see a friendly "No notifications yet" state instead of a broken empty list.
-   **Token Expiry**: If a reviewer clicks an old invitation link from an email, they must see a clear "Token Expired" page (aligned with 007).

## Requirements *(mandatory)*

### Functional Requirements

-   **FR-001**: System MUST support dual-channel delivery (Email + In-App) for all core events.
-   **FR-002**: In-App notifications MUST update in near real-time (using Supabase Realtime or 30s polling).
-   **FR-003**: Emails MUST use HTML templates with professional Academic English phrasing (e.g., "We are pleased to inform you...").
-   **FR-004**: The system MUST implement an automated background scheduler (e.g., APScheduler or simple cron-triggered endpoint) to check for expiring reviews.
-   **FR-005**: Users MUST be able to see a history of notifications in the frontend.

### Security & Authentication Requirements *(mandatory)*

-   **SEC-001**: Reviewer invitation emails MUST contain secure, signed Token links (reusing 007/008 logic).
-   **SEC-002**: Users MUST ONLY be able to fetch notifications belonging to their own `user_id` (RLS Policy).
-   **SEC-003**: Email sending logic MUST NOT expose SMTP credentials in client-side code.

### API Development Requirements *(mandatory)*

-   **API-001**: `GET /api/v1/notifications` - Fetch list for current user.
-   **API-002**: `PATCH /api/v1/notifications/{id}/read` - Mark as read.
-   **API-003**: `POST /api/v1/internal/cron/chase-reviews` - Trigger for auto-chasing (protected by internal key).

### Technical Constraints *(from user input)*

-   **Database**: Use `notifications` table in Supabase (`id`, `user_id`, `content`, `manuscript_id`, `is_read`, `created_at`).
-   **Async**: Email sending MUST use FastAPI `BackgroundTasks`.
-   **Governance**: Core logic MUST include Chinese comments.
-   **Simplicity**: NO complex third-party notification services (e.g., Courier, Novu); use "Glue Coding" with standard libs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

-   **SC-001**: 100% of status changes trigger a database record in `notifications` table.
-   **SC-002**: Email sending does not block the API response (P95 response time < 500ms even if email takes 2s).
-   **SC-003**: Auto-chasing job identifies 100% of eligible reviewers (due within 24h) in test scenarios.

## Assumptions

-   SMTP settings (Host, Port, User, Pass) are available in environment variables.
-   The "Bell Icon" will be added to the existing `SiteHeader` component.
-   "Academic English" templates will be hardcoded or stored as Jinja2 templates in the backend.

## Key Entities

### Notification
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary Key |
| user_id | UUID | Recipient (FK to auth.users) |
| manuscript_id | UUID | Context link (FK to manuscripts) |
| type | String | Enum: `submission`, `review_invite`, `decision`, `chase`, `system` |
| title | String | Short header for UI |
| content | Text | Body text for UI |
| is_read | Boolean | Read status |
| created_at | Timestamp | Creation time |
