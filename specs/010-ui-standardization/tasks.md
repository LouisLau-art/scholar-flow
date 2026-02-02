# Tasks: UI Standardization and Fixes

**Feature Branch**: `010-ui-standardization`
**Spec**: [specs/010-ui-standardization/spec.md](spec.md)
**Status**: Complete

## Implementation Strategy
- **Approach**: "Adopt & Eject" - Initialize standard Shadcn infrastructure first, then migrate components one by one.
- **Critical Path**: Setup Config -> Install Primitives -> Refactor DecisionPanel -> Global Polish.
- **Risk Mitigation**: Verify `Tabs` (existing component) immediately after config update to prevent regression.

## Dependencies

- Phase 2 depends on Phase 1
- Phase 3 (US1) depends on Phase 2
- Phase 4 (US2) depends on Phase 2
- Phase 5 depends on all previous phases

---

## Phase 1: Setup & Configuration
**Goal**: Initialize Shadcn/UI infrastructure and enforce Light Mode.

- [x] T001 Create `frontend/components.json` with standard Shadcn configuration
- [x] T002 Install core dependencies (`tailwindcss-animate`, `class-variance-authority`, `clsx`, `tailwind-merge`)
- [x] T003 Update `frontend/src/app/globals.css` to define CSS variables (Light Mode only, locking `--background` etc.)
- [x] T004 Update `frontend/tailwind.config.ts` to include Shadcn plugin and extend theme using CSS variables
- [x] T005 Create `frontend/src/lib/utils.ts` (verify `cn` helper exists and matches standard)

## Phase 2: Foundational Components
**Goal**: Install and standardize reusable UI components.

- [x] T006 Install/Create `Button` component in `frontend/src/components/ui/button.tsx`
- [x] T007 Install/Create `RadioGroup` component in `frontend/src/components/ui/radio-group.tsx` (requires `@radix-ui/react-radio-group`)
- [x] T008 Install/Create `Label` component in `frontend/src/components/ui/label.tsx` (requires `@radix-ui/react-label`)
- [x] T009 Install/Create `Card` component in `frontend/src/components/ui/card.tsx`
- [x] T010 [P] Update `frontend/src/components/ui/tabs.tsx` to use standard CSS variables (remove hardcoded Slate colors)
- [x] T011 [P] Verify `Tabs` rendering in existing dashboard (visual check)

## Phase 3: User Story 1 - Consistent Legibility (DecisionPanel)
**Goal**: Fix white-on-white issues in DecisionPanel by adopting standard components.

- [x] T012 [US1] Refactor `frontend/src/components/DecisionPanel.tsx` to use `Card` and `CardContent` for layout
- [x] T013 [US1] Refactor `frontend/src/components/DecisionPanel.tsx` to replace `div` selectors with `RadioGroup`
- [x] T014 [US1] Refactor `frontend/src/components/DecisionPanel.tsx` to replace `button` with `Button` component
- [x] T015 [US1] Ensure `DecisionPanel` state styles (Active vs Hover) follow precedence rules via Shadcn primitives

## Phase 4: User Story 2 - Standardized Interactions
**Goal**: Apply standard components to other key areas (Reviewer Modal, Editor Tabs).

- [x] T016 [US2] Scan `frontend/src` for other ad-hoc button implementations (using `grep`)
- [x] T017 [US2] [P] Refactor `frontend/src/components/ReviewerModal.tsx` (if exists) or equivalent review area to use `Button` and `Label`
- [x] T018 [US2] [P] Ensure Editor Dashboard tabs use the updated `Tabs` component correctly

## Phase 5: Polish & Verification
**Goal**: Final regression testing and cleanup.

- [x] T019 Run `npm run test` in `frontend/` to ensure no component regressions
- [x] T020 Verify Light Mode enforcement (check that system Dark Mode does not affect UI)
- [x] T021 Run full project test suite `./run_tests.sh`

## Completion Notes (2026-01-30)
- Added Shadcn config, CSS variables, and shared UI primitives (Button/Card/Label/RadioGroup).
- Refactored DecisionPanel and Reviewer review modal to use Shadcn components and restore legible default states.
- Updated Tabs styling, Editor Dashboard tabs, and Editor Pipeline interactions (card filters + clear filter).
- Tests run: `npm run test` (frontend) and `./run_tests.sh` (full suite).
