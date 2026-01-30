# Implementation Plan: Executive Analytics Dashboard

**Branch**: `014-analytics-dashboard` | **Date**: 2026-01-30 | **Spec**: [specs/014-analytics-dashboard/spec.md](spec.md)
**Input**: Feature specification from `/specs/014-analytics-dashboard/spec.md`

## Summary

Implement a high-performance, visual analytics dashboard for EICs and MEs. The dashboard will feature KPI cards, Recharts-powered visual trends, and geographic distribution charts. All calculations will be offloaded to PostgreSQL (Supabase) via SQL Views and RPCs to ensure scalability and data integrity.

## Technical Context

**Language/Version**: Python 3.11+ (Backend), TypeScript 5.x (Frontend)
**Primary Dependencies**: 
- Backend: FastAPI, Pandas, OpenPyXL, Supabase-py
- Frontend: Next.js 14.2 (App Router), Recharts, TanStack Query (React Query), Shadcn/UI
**Storage**: Supabase (PostgreSQL), SQL Views, RPC
**Testing**: pytest (Backend), Vitest (Frontend), Playwright (E2E)
**Target Platform**: Linux Server (Backend), Vercel (Frontend)
**Project Type**: Web application
**Performance Goals**: Dashboard renders < 2s (P95), API responses < 500ms
**Constraints**: 
- No in-memory aggregation in Python or JS.
- Strict RBAC (EIC/ME only).
- Recharts for all visualizations.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Governance (Principles I-V)
1. **治理合规 (SD/PG)**: [x] Spec created. Sequence 0->1 observed.
2. **交付模型 (TI/MVP)**: [x] Stories independent (KPI vs Charts vs Export).
3. **架构简约 (AS)**: [x] Using Views/RPC instead of complex analytics engines.
4. **可观测性 (OT)**: [x] API logging and SQL comments included.

### Security & Authentication (Principle XIII)
5. **认证优先**: [x] ME/EIC role check enforced.
6. **JWT 验证**: [x] Supabase JWT used.
7. **真实用户上下文**: [x] No hardcoded IDs.
8. **RBAC**: [x] Restricted to editorial roles.
9. **安全设计**: [x] Financial data protected at same level.

### API Development (Principle XIV)
10. **API 优先**: [x] OpenAPI contract created.
11. **路径一致性**: [x] Consistent `/api/v1/analytics/`.
12. **版本控制**: [x] v1.
13. **错误处理**: [x] Unified middleware.
14. **数据验证**: [x] Pydantic models for response validation.

### Testing Strategy (Principle XII)
15. **完整 API 测试**: [x] Planned.
16. **身份验证测试**: [x] Role checks in tests.
17. **错误场景测试**: [x] Empty DB handled.
18. **集成测试**: [x] Real DB connection for SQL Views.
19. **100% 测试通过率**: [x] Required.

### Architecture & Version (Principles VI-VII)
20. **架构与版本**: [x] Compatible.
21. **数据流规范**: [x] Server Actions / API + Query caching.
22. **容错机制**: [x] Loading states + Skeleton screens.
23. **视觉标准**: [x] Frontiers style / Shadcn.

### User Experience (Principle XV)
24. **功能完整性**: [x] Full dashboard workflow.
25. **个人中心**: [x] N/A (Global view).
26. **清晰导航**: [x] Dashboard accessible via Editor menu.
27. **错误恢复**: [x] User-friendly error messages.

### AI 协作 (Principle VII)
28. **任务原子化**: [x] Tasks split by story.
29. **中文注释**: [x] SQL logic and formula comments.
30. **文档同步**: [x] Documentation generated.

## Project Structure

### Documentation (this feature)

```text
specs/014-analytics-dashboard/
├── plan.md              # This file
├── research.md          # Decisions (Export, Logic)
├── data-model.md        # Views/RPCs
├── quickstart.md        # Setup
├── contracts/           # OpenAPI
└── tasks.md             # To be created
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/v1/
│   │   └── analytics.py       # NEW: Analytics Endpoints
│   ├── core/
│   │   └── export_service.py  # NEW: Pandas Export logic
│   └── models/
│       └── analytics.py       # NEW: Pydantic schemas
└── tests/
    └── test_analytics.py      # NEW: API Tests

frontend/
├── src/
│   ├── app/
│   │   └── (admin)/editor/analytics/ # NEW: Dashboard page
│   ├── components/
│   │   └── analytics/         # NEW: KPI Cards, Charts
│   └── lib/
│       └── api/analytics.ts   # NEW: API Client
└── tests/
```

**Structure Decision**: Standard Web App.

## Technical Decisions

### 1. Architecture & Routing
- **显性路由**: `/api/v1/analytics/summary`, `/api/v1/analytics/trends`.
- **全栈切片**: Dashboard UI -> Analytics API -> SQL Views.

### 2. Dependencies & SDKs
- **Data Engine**: PostgreSQL Views for logic, Pandas for export.
- **Charts**: Recharts.
- **Toast**: Shadcn/Sonner for export success/error.

## Quality Assurance (QA Suite)

### Test Requirements
- **Backend**: Test SQL Views results against manual counts. Verify RBAC for non-editors.
- **Frontend**: Verify chart rendering and skeleton visibility.
- **Integration**: Full flow from dashboard view to report export.