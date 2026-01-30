# Feature Specification: Dynamic Portal CMS

**Feature Branch**: `013-portal-cms`
**Created**: 2026-01-30
**Status**: Implemented
**Input**: User description: "开启 Feature 013: 动态门户内容管理系统 (Lightweight CMS)..."

## Clarifications

### Session 2026-01-30
- Q: Menu Storage Strategy? → A: Use a structured table (`cms_menu_items`) with `parent_id` and `order_index` to allow relational constraints and efficient partial updates.
- Q: Image Handling Strategy? → A: Use Supabase Storage (`cms-assets` public bucket) for image uploads; store the resulting public URL in the content.
- Q: Content Storage Format? → A: Store content as sanitized HTML string to ensure maximum compatibility with Tiptap/Quill and simplify frontend rendering.

## User Scenarios & Testing *(mandatory)*
...
### Functional Requirements

- **FR-001**: System MUST provide a database schema to store CMS pages with attributes: `slug` (unique), `title`, `content` (stored as sanitized HTML), and `is_published`).
- **FR-002**: System MUST support dynamic routing to render pages based on their `slug` (e.g., `/journal/[slug]`).
...
- **FR-003**: System MUST provide a "Website Management" module in the Editor Workspace with a Rich Text Editor that uploads images to a dedicated Supabase Storage bucket (`cms-assets`) and embeds them via public URL.
- **FR-004**: System MUST allow Editors to manage global navigation menus via a `cms_menu_items` table, allowing hierarchical definitions (parent/child) and link targets (internal dynamic page or external URL).
...
- **FR-005**: System MUST auto-generate standard placeholder pages (About, Board, Guidelines, Contact, Ethics) upon initialization if missing.
- **FR-006**: Dynamic pages MUST be Server-Side Rendered (SSR) to ensure content is indexable by search engines (SEO).
- **FR-007**: System MUST implement caching strategies (e.g., ISR or efficient cache headers) for dynamic pages to ensure high read performance.
- **FR-008**: System MUST prevent creation of pages with slugs that conflict with existing system routes.

### Security & Authentication Requirements *(mandatory)*

- **SEC-001**: All content management operations (Create/Edit/Publish) MUST require authentication with the 'Editor' role (Principle XIII).
- **SEC-002**: API endpoints for CMS management MUST validate JWT tokens on every request (Principle XIII).
- **SEC-003**: Public access to "Published" pages MUST NOT require authentication.
- **SEC-004**: Access to "Draft" pages via public URL MUST be denied (404 or 403) for unauthenticated users.
- **SEC-005**: Rich Text content MUST be sanitized to prevent XSS attacks before rendering.

### API Development Requirements *(mandatory)*

- **API-001**: Define API specification (OpenAPI/Swagger) for CMS endpoints (pages, menu) BEFORE implementation (Principle XIV).
- **API-002**: Use consistent path patterns (e.g., `/api/v1/cms/pages`) (Principle XIV).
- **API-003**: Always version APIs (e.g., `/api/v1/`) (Principle XIV).
- **API-004**: Every endpoint MUST have clear documentation (Principle XIV).
- **API-005**: Implement unified error handling (e.g., 409 Conflict for duplicate slugs) (Principle XIV).
- **API-006**: Provide detailed logging for content changes (Audit Trail) (Principle XIV).

### Test Coverage Requirements *(mandatory)*

- **TEST-001**: Test ALL HTTP methods for CMS endpoints (Principle XII).
- **TEST-002**: Ensure frontend routing correctly handles dynamic slugs vs. system routes (Principle XII).
- **TEST-003**: Authenticated management endpoints MUST have tests for role validation (Editor vs. Author vs. Anon) (Principle XII).
- **TEST-004**: Test input validation (e.g., invalid slug characters, empty title) (Principle XII).
- **TEST-005**: Test error cases, such as attempting to duplicate a slug (Principle XII).
- **TEST-006**: Include integration tests verifying the full flow from "Create Page" to "Public View" (Principle XII).
- **TEST-007**: Achieve 100% test pass rate before delivery (Principle XI).

### Key Entities

- **CMS Page**: Represents a content page. Attributes: `id`, `slug`, `title`, `content`, `is_published`, `created_at`, `updated_at`.
- **CMS Menu Item**: Represents a navigation link. Attributes: `id`, `label`, `url` (or `page_id` FK), `parent_id` (nullable), `order_index`, `location` (header/footer).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Public dynamic pages load in under 500ms (P95) via effective caching/ISR.
- **SC-002**: Editors can create and publish a new page with an image in under 2 minutes (Usability).
- **SC-003**: System initializes with 5 standard pages fully accessible immediately after deployment.
- **SC-004**: Public pages are fully rendered in the HTML source (SSR verified) for SEO compliance.

## Implementation Notes

- **DB Migration**: `supabase/migrations/20260130193000_add_portal_cms.sql`
- **Backend API**: `backend/app/api/v1/cms.py` (注册于 `backend/main.py`)
- **CMS 初始化**: `backend/app/core/init_cms.py`（启动时补齐 About/Board/Guidelines/Contact/Ethics）
- **Frontend 管理入口**: `Dashboard → Editor → Website`（`frontend/src/components/EditorDashboard.tsx`）
- **公开页面 SSR/ISR**: `frontend/src/app/journal/[slug]/page.tsx`（`revalidate=60`）
