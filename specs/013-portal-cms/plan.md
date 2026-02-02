# Implementation Plan: Dynamic Portal CMS

**Branch**: `013-portal-cms` | **Date**: 2026-01-30 | **Spec**: [specs/013-portal-cms/spec.md](spec.md)
**Input**: Feature specification from `/specs/013-portal-cms/spec.md`

## Summary

Implement a lightweight, database-driven Content Management System (CMS) for the Journal Portal. 
**Key capabilities**:
1. **Dynamic Pages**: SSR rendering of content pages via `/journal/[slug]`.
2. **Editor Workspace**: "Website Management" module with rich text editing (Tiptap/Quill) and image uploads.
3. **Menu Management**: Configurable Navigation/Footer via a structured database table.
4. **Storage**: HTML content storage + Supabase Storage for assets.

## Technical Context

**Language/Version**: Python 3.11+ (Backend), TypeScript 5.x (Frontend)
**Primary Dependencies**: 
- Backend: FastAPI (Routes), Pydantic v2 (Validation), Supabase-py (DB/Auth)
- Frontend: Next.js 14.2 (App Router), Tiptap or React-Quill (Rich Text), Supabase-js
**Storage**: Supabase (PostgreSQL `cms_pages`, `cms_menu_items`, Storage Bucket `cms-assets`)
**Testing**: pytest (Backend), Vitest/Playwright (Frontend)
**Target Platform**: Vercel (Frontend), Linux Server (Backend)
**Project Type**: Web application (Next.js + FastAPI)
**Performance Goals**: P95 < 500ms for dynamic page loads (SSR/ISR).
**Constraints**: 
- Must use **SSR** for SEO.
- Must use **Incremental Static Regeneration (ISR)** for performance.
- Secure Editor-only access for management.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Governance (Principles I-V)
1. **治理合规 (SD/PG)**: [x] Spec created & clarified.
2. **交付模型 (TI/MVP)**: [x] Stories independent (Page mgmt vs Menu mgmt).
3. **架构简约 (AS)**: [x] Simple tables, no complex headless CMS integration.
4. **可观测性 (OT)**: [x] Logging required for content changes.

### Security & Authentication (Principle XIII)
5. **认证优先**: [x] Editor role required for management.
6. **JWT 验证**: [x] Standard auth middleware used.
7. **真实用户上下文**: [x] User IDs from token.
8. **RBAC**: [x] Editor-only access enforced.
9. **安全设计**: [x] XSS sanitization required for HTML content.

### API Development (Principle XIV)
10. **API 优先**: [x] OpenAPI defined.
11. **路径一致性**: [x] `/api/v1/` used.
12. **版本控制**: [x] v1.
13. **错误处理**: [x] Unified middleware.
14. **数据验证**: [x] Pydantic models.

### Testing Strategy (Principle XII)
15. **完整 API 测试**: [x] Planned.
16. **身份验证测试**: [x] RLS/Role checks.
17. **错误场景测试**: [x] Duplicate slug, invalid HTML.
18. **集成测试**: [x] Real DB tests required.
19. **100% 测试通过率**: [x] Required.

### Architecture & Version (Principles VI-VII)
20. **架构与版本**: [x] Compatible.
21. **数据流规范**: [x] Server Actions / API.
22. **容错机制**: [x] 404 handling for missing slugs.
23. **视觉标准**: [x] Shadcn/UI.

### User Experience (Principle XV)
24. **功能完整性**: [x] Create -> Publish -> View flow complete.
25. **个人中心**: [x] N/A (Admin focus).
26. **清晰导航**: [x] This feature *fixes* navigation.
27. **错误恢复**: [x] Form validation.

### AI 协作 (Principle VII)
28. **任务原子化**: [x] Tasks split.
29. **中文注释**: [x] Required for routing logic.
30. **文档同步**: [x] Synced.

## Project Structure

### Documentation (this feature)

```text
specs/013-portal-cms/
├── plan.md              # This file
├── research.md          # Decisions (Editor lib, ISR config)
├── data-model.md        # Schema
├── quickstart.md        # Setup guide
├── contracts/           # OpenAPI
└── tasks.md             # Tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/v1/
│   │   └── cms.py              # NEW: CMS Endpoints
│   ├── models/
│   │   └── cms.py              # NEW: Pydantic Models
│   ├── services/
│   │   └── cms_service.py      # NEW: Business Logic
│   └── core/init_cms.py         # NEW: Seed default pages
├── main.py                      # UPDATE: Register router + startup init
└── tests/

frontend/
├── src/
│   ├── app/
│   │   └── journal/[slug]/     # NEW: Dynamic Public Page
│   ├── components/
│   │   └── cms/                # NEW: Rich Text Editor, Menu Builder
│   ├── services/
│   │   └── cms.ts              # NEW: API Client
│   └── components/layout/
│       └── SiteFooter.tsx      # NEW: Footer driven by CMS menu
└── tests/
```

**Structure Decision**: Standard Web App.

## Technical Decisions

### 1. Architecture & Routing
- **显性路由**: `/api/v1/cms/pages`, `/api/v1/cms/menu`.
- **全栈切片**: Admin Panel -> API -> DB -> Public Render.

### 2. Dependencies & SDKs
- **Rich Text**: `Tiptap`（已选型）
- **Sanitization**: `bleach`（后端写入消毒）+ `isomorphic-dompurify`（前端渲染前二次消毒）

## Quality Assurance (QA Suite)

### Test Requirements
- **Backend**: Test slug uniqueness, XSS sanitization (if backend-side), role checks.
- **Frontend**: Test editor state management, image upload flow.
- **Integration**: End-to-end flow from "Create Draft" to "Publish" to "Public View".
