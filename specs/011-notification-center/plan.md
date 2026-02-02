# Implementation Plan: Notification Center

**Branch**: `011-notification-center` | **Date**: 2026-01-30 | **Spec**: [specs/011-notification-center/spec.md](spec.md)
**Input**: Feature specification from `/specs/011-notification-center/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a comprehensive notification system supporting both Email (via `smtplib`) and In-App (via Supabase Realtime) channels. Features include role-based triggers (submission, review invite, decision), a notification history UI (Bell Icon), and an automated background scheduler for chasing overdue reviews.

## Technical Context

**Language/Version**: Python 3.14+ (Backend), TypeScript 5.x (Frontend)
**Primary Dependencies**: 
- Backend: `smtplib` (Standard Lib), `jinja2` (Templating), FastAPI BackgroundTasks
- Frontend: `@supabase/supabase-js` (Realtime), Lucide React (Icons)
**Storage**: Supabase (`notifications` table, `review_assignments` extension)
**Testing**: pytest (Backend), Playwright (E2E)
**Target Platform**: Linux / Vercel
**Project Type**: Web application (Next.js + FastAPI)
**Performance Goals**: Email sending < 500ms (async), Realtime latency < 200ms
**Constraints**: 
- No 3rd party notification services (Courier/Novu).
- Strict idempotency for auto-chasing.
- Academic English templates.
**Scale/Scope**: ~5 new API endpoints, 1 new DB table, 1 new Cron job.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Governance (Principles I-V)
1. **治理合规 (SD/PG)**: [x] Spec created, clarified, and validated.
2. **交付模型 (TI/MVP)**: [x] Stories split by channel and automation.
3. **架构简约 (AS)**: [x] Using standard `smtplib` and native Supabase Realtime.
4. **可观测性 (OT)**: [x] Logging required for SMTP errors (Edge Case spec).

### Security & Authentication (Principle XIII)
5. **认证优先**: [x] Cron job protected by Admin Key.
6. **JWT 验证**: [x] User endpoints protected by JWT.
7. **真实用户上下文**: [x] RLS ensures users only see their own notifs.
8. **RBAC**: [x] Supported via existing auth model.
9. **安全设计**: [x] Token links reuse 007 secure logic.

### API Development (Principle XIV)
10. **API 优先**: [x] OpenAPI defined in `contracts/api.yaml`.
11. **路径一致性**: [x] `/api/v1/` prefix used.
12. **版本控制**: [x] v1 versioning.
13. **错误处理**: [x] Standard middleware used.
14. **数据验证**: [x] Pydantic models will be used.

### Testing Strategy (Principle XII)
15. **完整 API 测试**: [x] Planned for notification endpoints.
16. **身份验证测试**: [x] Required for RLS verification.
17. **错误场景测试**: [x] Email failure handling planned.
18. **集成测试**: [x] Real DB tests for `notifications` insert.
19. **100% 测试通过率**: [x] Requirement for delivery.

### Architecture & Version (Principles VI-VII)
20. **架构与版本**: [x] Next.js 14.2 / Pydantic v2 compatible.
21. **数据流规范**: [x] Server Actions / API Routes utilized.
22. **容错机制**: [x] Email async handling prevents blocking.
23. **视觉标准**: [x] Bell icon to match Frontiers style.

### User Experience (Principle XV)
24. **功能完整性**: [x] History + Realtime + Email covers all bases.
25. **个人中心**: [x] N/A.
26. **清晰导航**: [x] Bell icon acts as notification hub.
27. **错误恢复**: [x] Empty states defined.

### AI 协作 (Principle VII)
28. **任务原子化**: [x] Tasks broken down by phase.
29. **中文注释**: [x] Mandatory for core logic.
30. **文档同步**: [x] Plan synced with Spec.

## Project Structure

### Documentation (this feature)

```text
specs/011-notification-center/
├── plan.md              # This file
├── research.md          # Tech decisions (SMTP, Realtime)
├── data-model.md        # DB Schema & RLS
├── quickstart.md        # Verification steps
├── contracts/           # OpenAPI Spec
└── tasks.md             # Task breakdown
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/v1/
│   │   ├── notifications.py    # NEW: User endpoints
│   │   └── internal.py         # NEW: Cron endpoints
│   ├── core/
│   │   ├── mail.py             # NEW: SMTP wrapper
│   │   └── scheduler.py        # NEW: Chasing logic
│   └── templates/
│       └── emails/             # NEW: Jinja2 templates
└── tests/

frontend/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   └── SiteHeader.tsx  # UPDATE: Add Bell
│   │   └── notifications/      # NEW: List/Item components
│   └── lib/
│       └── supabase.ts         # UPDATE: Realtime helper
└── tests/
```

**Structure Decision**: Standard Web App structure (Frontend + Backend).

## Technical Decisions

### 1. Architecture & Routing
- **显性路由**: `GET /api/v1/notifications`, `POST /api/v1/internal/cron/chase-reviews`.
- **全栈切片**: Frontend Bell -> API -> DB.

### 2. Dependencies & SDKs
- **原生优先**: `smtplib` over `FastAPI-Mail`. `Supabase Realtime` over polling.
- **交互标准**: Shadcn Popover for Bell dropdown.

## Quality Assurance (QA Suite)

### Test Requirements
- **Backend**: Test email sending (mock SMTP), test notification creation, test RLS.
- **Frontend**: Test Realtime subscription (mock), test read-marking.
- **Integration**: Test auto-chase logic with DB state.