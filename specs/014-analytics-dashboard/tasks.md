---
description: "Tasks for Executive Analytics Dashboard implementation"
---

# Tasks: Executive Analytics Dashboard

**Input**: Design documents from `/specs/014-analytics-dashboard`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/analytics.yaml, research.md

## Phase 1: Setup (Project Initialization)

- [X] T001 [P] Install backend dependencies: `pandas`, `openpyxl` in `backend/requirements.txt`
- [X] T002 [P] Install frontend dependencies: `recharts`, `@tanstack/react-query` in `frontend/package.json`
- [X] T003 Create `supabase/migrations/20260130200000_analytics_views_rpcs.sql` with `view_submission_trends`, `view_status_pipeline` and RPCs `get_journal_kpis`, `get_author_geography`

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T004 [P] Implement `AnalyticsSummary`, `TrendData`, and `GeoData` Pydantic models in `backend/app/models/analytics.py`
- [X] T005 [P] Create `AnalyticsService` for executing Supabase RPCs and Views in `backend/app/services/analytics_service.py`
- [X] T006 [P] Register `analytics` router in `backend/main.py`
- [X] T007 [P] Implement `TanStack Query` provider and client configuration in `frontend/src/lib/query-client.ts`

## Phase 3: User Story 1 - Real-time KPI Monitoring (Priority: P1)

**Goal**: Display the 4 core KPI cards at the top of the dashboard.
**Independent Test**: Navigate to `/editor/analytics` and verify KPI cards display data from `get_journal_kpis()` RPC.

- [X] T008 [P] [US1] Implement `GET /api/v1/analytics/summary` endpoint in `backend/app/api/v1/analytics.py`
- [X] T009 [P] [US1] Create `KPICard` and `KPIGrid` components in `frontend/src/components/analytics/KPISection.tsx`
- [X] T010 [US1] Create Analytics Dashboard layout and integrate `KPISection` in `frontend/src/app/(admin)/editor/analytics/page.tsx`
- [X] T011 [US1] Add `Skeleton` loading states for KPI cards in `frontend/src/components/analytics/KPISkeleton.tsx`
- [X] T012 [P] [US1] Add unit tests for `get_journal_kpis` endpoint in `backend/tests/test_analytics.py`

## Phase 4: User Story 2 - Visualizing Editorial Trends (Priority: P2)

**Goal**: Render line charts, doughnut charts, and bar charts for journal data.
**Independent Test**: Verify charts (Trends, Pipeline, Decision, Geo) render accurately based on backend data.

- [X] T013 [P] [US2] Implement `GET /api/v1/analytics/trends` and `GET /api/v1/analytics/geo` in `backend/app/api/v1/analytics.py`
- [X] T014 [P] [US2] Create `SubmissionTrendChart` (Line) using Recharts in `frontend/src/components/analytics/SubmissionTrendChart.tsx`
- [X] T015 [P] [US2] Create `StatusPipelineChart` (Funnel) and `DecisionDistributionChart` (Doughnut) in `frontend/src/components/analytics/EditorialCharts.tsx`
- [X] T016 [P] [US2] Create `AuthorGeoChart` (Horizontal Bar) in `frontend/src/components/analytics/AuthorGeoChart.tsx`
- [X] T017 [US2] Integrate all charts into the Dashboard page with `Skeleton` fallbacks in `frontend/src/app/(admin)/editor/analytics/page.tsx`
- [X] T018 [P] [US2] Add integration tests for trend and geo aggregation in `backend/tests/test_analytics_aggregation.py`

## Phase 5: User Story 3 - Data Export for Reporting (Priority: P3)

**Goal**: Support downloading dashboard data as .xlsx or .csv.
**Independent Test**: Click "Export Report" button and verify the downloaded file contains the aggregated summary.

- [X] T019 [P] [US3] Implement `ExportService` using Pandas for XLSX/CSV generation in `backend/app/core/export_service.py`
- [X] T020 [P] [US3] Implement `GET /api/v1/analytics/export` endpoint in `backend/app/api/v1/analytics.py`
- [X] T021 [US3] Create `ExportButton` with format selection and toast notifications in `frontend/src/components/analytics/ExportButton.tsx`
- [X] T022 [P] [US3] Add functional test for export file generation in `backend/tests/test_analytics_export.py`

## Final Phase: Polish & Cross-Cutting Concerns

- [X] T023 [P] Add navigation link to "Analytics" in the Editor Dashboard `frontend/src/components/EditorDashboard.tsx`
- [X] T024 [P] Apply ScholarFlow brand colors (深蓝/灰色系) to all Recharts components using Tailwind CSS variables
- [X] T025 [P] Implement RBAC check (EIC/ME) in both frontend route and backend middleware `backend/app/core/auth.py`
- [X] T025b [P] Implement audit logging for all analytics API access events in `backend/app/api/v1/analytics.py`
- [X] T026 Run full E2E flow test for Dashboard and Export using Playwright in `frontend/tests/e2e/analytics.spec.ts`

## Dependencies

- Phase 2 (Foundational) blocks all US implementation.
- US1 (KPIs) is the MVP and should be completed first.
- US2 (Charts) depends on foundational API patterns established in US1.
- US3 (Export) depends on the data aggregation logic used in US1 and US2.

## Parallel Execution

**Setup & Foundational**:
- T001, T002 (Deps) can run in parallel.
- T004, T005, T007 (Internal structures) can run in parallel after T003.

**User Story 1 & 2**:
- Backend API implementation (T008, T013) can proceed in parallel with Frontend component development (T009, T014, T015, T016).

**Export**:
- Export Service (T019) can be developed independently once data models are defined.
