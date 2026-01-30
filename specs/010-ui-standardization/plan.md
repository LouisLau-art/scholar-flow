# Implementation Plan: UI Standardization and Fixes

**Branch**: `010-ui-standardization` | **Date**: 2026-01-30 | **Spec**: [specs/010-ui-standardization/spec.md](spec.md)
**Status**: Complete
**Input**: Feature specification from `specs/010-ui-standardization/spec.md`

## Summary

This feature standardizes the frontend UI to strictly follow Shadcn/UI patterns, fixing "white-on-white" legibility issues. It involves initializing standard Shadcn configuration, replacing custom buttons/cards with `Button` and `RadioGroup` components, unifying component states (Default, Active, Hover, Disabled), and strictly enforcing Light Mode to avoid theme inconsistencies.

## Technical Context

**Language/Version**: TypeScript 5.x, React 18, Next.js 14.2
**Primary Dependencies**: Shadcn/UI (Radix Primitives), Tailwind CSS 3.4, Lucide React
**Storage**: N/A (Frontend only)
**Testing**: Vitest (Unit), Playwright (E2E)
**Target Platform**: Web
**Project Type**: Web application (Next.js)
**Performance Goals**: UI interactions <100ms
**Constraints**: Strict adherence to Shadcn components, Slate color theme, and **Light Mode Only**.
**Scale/Scope**: Refactoring ~5 key components and global styles.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Governance (Principles I-V)
1. **治理合规 (SD/PG)**: [x] Spec created, clarified, and validated.
2. **交付模型 (TI/MVP)**: [x] Stories are independent. MVP focused on legibility.
3. **架构简约 (AS)**: [x] Explicit component logic, removing custom styles.
4. **可观测性 (OT)**: [x] N/A (UI focused).

### Security & Authentication (Principle XIII)
5. **认证优先**: [x] DecisionPanel submission requires auth (unchanged).
6. **JWT 验证**: [x] Existing API calls use JWT (unchanged).
7. **真实用户上下文**: [x] Uses real user context (unchanged).
8. **RBAC**: [x] Editor role enforced (unchanged).
9. **安全设计**: [x] UI changes do not expose sensitive data.

### API Development (Principle XIV)
10. **API 优先**: [x] No API changes.
11. **路径一致性**: [x] No API changes.
12. **版本控制**: [x] No API changes.
13. **错误处理**: [x] UI displays API errors via Toast (standardized).
14. **数据验证**: [x] Frontend validation preserved.

### Testing Strategy (Principle XII)
15. **完整 API 测试**: [x] Existing tests cover endpoints.
16. **身份验证测试**: [x] Existing tests cover auth.
17. **错误场景测试**: [x] UI tests will cover error states.
18. **集成测试**: [x] N/A for pure UI.
19. **100% 测试通过率**: [x] Requirement for delivery.

### Architecture & Version (Principles VI-VII)
20. **架构与版本**: [x] Next.js 14.2 compatible.
21. **数据流规范**: [x] 'use client' usage minimized/standardized.
22. **容错机制**: [x] Loading states included.
23. **视觉标准**: [x] **CORE GOAL**: Enforcing Frontiers style/Shadcn. Enforcing Light Mode (FR-009).

### User Experience (Principle XV)
24. **功能完整性**: [x] Workflows preserved.
25. **个人中心**: [x] N/A.
26. **清晰导航**: [x] Improved visual feedback.
27. **错误恢复**: [x] Clearer disabled/error states.

### AI 协作 (Principle VII)
28. **任务原子化**: [x] Broken down by component type.
29. **中文注释**: [x] Will add Chinese comments for complex state logic if any.
30. **文档同步**: [x] Spec and Plan synced.

## Project Structure

### Documentation (this feature)

```text
specs/010-ui-standardization/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (empty)
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
frontend/
├── components.json      # NEW: Shadcn config
├── tailwind.config.ts   # UPDATED: Shadcn extensions, Light Mode enforcement
├── src/
│   ├── app/
│   │   └── globals.css  # UPDATED: CSS variables (Light mode only)
│   ├── components/
│   │   ├── DecisionPanel.tsx  # REFACTORED
│   │   └── ui/
│   │       ├── button.tsx     # NEW
│   │       ├── radio-group.tsx # NEW
│   │       ├── label.tsx      # NEW
│   │       ├── card.tsx       # NEW
│   │       └── tabs.tsx       # UPDATED
└── tests/
```

**Structure Decision**: Standard Next.js + Shadcn structure.

## Technical Decisions

### 1. Architecture & Routing
- N/A (UI Refactor)

### 2. Dependencies & SDKs
- **Shadcn/UI**: Initialize standardized config.
- **Tailwind**: Enable `tailwindcss-animate`.
- **Theme**: Force Light Mode via configuration.

### 3. Component Strategy
- **Button**: Use standard variants (default, outline, ghost).
- **Selection Cards**: Use `RadioGroup` with custom `Label` children for rich content (title + description).
- **State Precedence**: CSS specificity will ensure `.data-[state=checked]` overrides `:hover`.

## Quality Assurance (QA Suite)

### Test Requirements
- **Visual Verification**: Check DecisionPanel states (Default, Active, Disabled).
- **Theme Check**: Verify Dark Mode system setting does NOT affect UI.
- **Regression Testing**: Run `./run_tests.sh`.

## Completion Notes (2026-01-30)
- Shadcn primitives installed and global tokens wired through Tailwind + CSS variables.
- DecisionPanel and Reviewer review modal updated to Shadcn components to fix legibility.
- Editor Pipeline cards now support click-to-filter and Clear Filter for navigation.
- Tests executed: `npm run test` (frontend) and `./run_tests.sh`.
