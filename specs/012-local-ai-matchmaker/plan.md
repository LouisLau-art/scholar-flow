# Implementation Plan: Local AI Matchmaker

**Branch**: `012-local-ai-matchmaker` | **Date**: 2026-01-30 | **Spec**: [specs/012-local-ai-matchmaker/spec.md](spec.md)
**Input**: Feature specification from `/specs/012-local-ai-matchmaker/spec.md`

## Summary

Implement a local, privacy-first reviewer recommendation engine using `sentence-transformers` (Python) and `pgvector` (Supabase). The system will index reviewer profiles into vector embeddings and provide an "AI Analysis" endpoint for Editors to find semantic matches for manuscripts without external API calls.

## Technical Context

**Language/Version**: Python 3.14+ (Backend), TypeScript 5.x (Frontend)
**Primary Dependencies**: 
- Backend: `sentence-transformers` (NLP), `pgvector` (DB), FastAPI `BackgroundTasks`
- Frontend: `recharts` (optional for score viz), Shadcn/UI
**Storage**: Supabase (`reviewer_embeddings` table, `vector` extension)
**Testing**: pytest (Backend integration), Playwright (E2E)
**Target Platform**: Linux / Vercel (Backend needs ~500MB RAM for model)
**Project Type**: Web application (Next.js + FastAPI)
**Performance Goals**: P95 < 5s for analysis.
**Constraints**: 
- NO external AI APIs (OpenAI/Claude blocked).
- Async indexing to avoid blocking Profile Save.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Governance (Principles I-V)
1. **治理合规 (SD/PG)**: [x] Spec created & clarified.
2. **交付模型 (TI/MVP)**: [x] Stories independent (Indexing vs Analysis).
3. **架构简约 (AS)**: [x] Using local lib instead of complex microservice.
4. **可观测性 (OT)**: [x] Logging required for model load failures.

### Security & Authentication (Principle XIII)
5. **认证优先**: [x] Analysis requires Editor role.
6. **JWT 验证**: [x] Standard auth middleware used.
7. **真实用户上下文**: [x] User IDs from token.
8. **RBAC**: [x] Editor-only access to analysis.
9. **安全设计**: [x] Privacy preserved (local compute).

### API Development (Principle XIV)
10. **API 优先**: [x] OpenAPI defined.
11. **路径一致性**: [x] `/api/v1/` used.
12. **版本控制**: [x] v1.
13. **错误处理**: [x] Unified middleware.
14. **数据验证**: [x] Pydantic models.

### Testing Strategy (Principle XII)
15. **完整 API 测试**: [x] Planned.
16. **身份验证测试**: [x] RLS/Role checks.
17. **错误场景测试**: [x] Cold start, Model failure.
18. **集成测试**: [x] Real `pgvector` tests required.
19. **100% 测试通过率**: [x] Required.

### Architecture & Version (Principles VI-VII)
20. **架构与版本**: [x] Compatible.
21. **数据流规范**: [x] Server Actions / API.
22. **容错机制**: [x] Graceful degradation if model fails.
23. **视觉标准**: [x] Shadcn/UI.

### User Experience (Principle XV)
24. **功能完整性**: [x] Indexing + Analysis + Invitation link.
25. **个人中心**: [x] N/A.
26. **清晰导航**: [x] Integrated in Editor workflow.
27. **错误恢复**: [x] Insufficient data msg.

### AI 协作 (Principle VII)
28. **任务原子化**: [x] Tasks split.
29. **中文注释**: [x] Required for math logic.
30. **文档同步**: [x] Synced.

## Project Structure

### Documentation (this feature)

```text
specs/012-local-ai-matchmaker/
├── plan.md              # This file
├── research.md          # Decisions (MiniLM, pgvector)
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
│   │   └── matchmaking.py      # NEW: Analysis endpoint
│   ├── core/
│   │   ├── ml.py               # NEW: Model loader & Vectorizer
│   │   └── config.py           # UPDATE: Add ML config
│   ├── services/
│   │   └── matchmaking_service.py # NEW: Logic
│   └── workers/                # (Optional directory, or just use BackgroundTasks in routers)
└── tests/

frontend/
├── src/
│   ├── components/
│   │   └── matchmaking/        # NEW: UI Components
└── tests/
```

**Structure Decision**: Standard Web App.

## Technical Decisions

### 1. Architecture & Routing
- **显性路由**: `/api/v1/matchmaking/analyze`.
- **全栈切片**: Frontend Panel -> API -> Local ML -> DB Vector Search.

### 2. Dependencies & SDKs
- **原生优先**: `sentence-transformers` for embeddings. `pgvector` for DB.

## Quality Assurance (QA Suite)

### Test Requirements
- **Backend**: Test vector generation shape (384), test cosine similarity logic (mock DB or real), test async worker trigger.
- **Frontend**: Test loading state, test "Invite" click integration.
- **Integration**: End-to-end flow from Profile Save -> Indexing -> Analysis.