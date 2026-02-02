# Feature Specification: Executive Analytics Dashboard

**Feature Branch**: `014-analytics-dashboard`  
**Created**: 2026-01-30  
**Status**: Draft  
**Input**: User description: "开启 Feature 014: 数据可视化驾驶舱 (Executive Analytics Dashboard)。 本项目是一个学术投稿系统，本功能旨在为期刊主编（EIC）和管理编辑（ME）提供一个高可视化的数据看板，用于实时监控期刊运行健康度、审稿效率及财务营收状况。 核心需求如下： 1. **关键指标卡片 (KPI Cards)**： - 在 Dashboard 顶部展示 4-5 个核心数据卡片： - **实时稿量**：本月新投稿数 / 总待处理稿件数。 - **平均周期**：从投稿到初次决定的平均天数 (Time to First Decision)。 - **录用率**：本年度的 Acceptance Rate (录用数 / 决议总数)。 - **财务总览**：本月/本年已确认到账的 APC 总金额。 2. **核心图表 (Visual Charts)**： - **投稿趋势图 (Submission Trends)**：折线图，展示过去 12 个月的投稿量与录用量对比。 - **稿件状态分布 (Status Pipeline)**：漏斗图或柱状图，展示各阶段（Under Review, Revision, Production）的稿件积压情况。 - **决定类型分布**：甜甜圈图 (Doughnut Chart)，展示 Accept / Reject / Major Revise / Minor Revise 的比例。 - **作者地理分布**：横向柱状图，展示投稿量前 10 的国家/地区（基于作者 Affiliation）。 3. **技术实现约束 (Tech Stack)**： - **前端库**：强制使用 **Recharts**。这是 React 生态最成熟的图表库，且能完美适配 Shadcn/UI 的设计风格。 - **后端计算**：**严禁在前端或 Python 内存中循环计算统计数据**。必须在 Supabase (PostgreSQL) 中创建 **SQL Views（视图）** 或 **RPC (Remote Procedure Calls)** 来完成聚合计算（Sum, Count, Avg），后端 API 只负责透传结果。 - **性能优化**：前端需使用 React Query 或 SWR 进行数据缓存，避免每次切换页面都重新查询数据库。图表加载时必须有 Skeleton 骨架屏。 4. **导出功能**： - 提供一个“导出报表”按钮，支持将当前统计数据导出为 Excel (.xlsx) 或 CSV 格式。 5. **宪法遵从**： - **UI 风格**：保持极简、商务风格（参考 Stripe Dashboard 或 Vercel Analytics）。图表颜色需符合 ScholarFlow 的主色调（深蓝/灰色系）。 - **显性逻辑**：SQL 统计逻辑必须 have 注释，明确“平均周期”的计算公式（例如：是否剔除了被拒稿件）。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real-time KPI Monitoring (Priority: P1)

As a Managing Editor, I want to see a high-level summary of the journal's health immediately upon entering the dashboard, so I can identify if there are bottlenecks or sudden drops in submission volume.

**Why this priority**: KPIs are the primary "at-a-glance" metrics for editorial health and financial status. They provide immediate value for daily operational decisions.

**Independent Test**: Can be fully tested by navigating to the "Analytics" tab and verifying the values in the 4 KPI cards (Submissions, Decision Time, Acceptance Rate, APC Total) against known database states.

**Acceptance Scenarios**:

1. **Given** there are 10 new submissions this month and 50 total pending, **When** the dashboard is loaded, **Then** the "Real-time Submissions" card shows "10 / 50".
2. **Given** the "Time to First Decision" average is 25 days, **When** the dashboard is loaded, **Then** the "Average Cycle" card displays "25 Days".

---

### User Story 2 - Visualizing Editorial Trends and Pipeline (Priority: P2)

As an Editor-in-Chief, I want to see visual charts of submission trends and current manuscript status distribution, so I can understand the journal's growth and workload over time.

**Why this priority**: Charts provide deeper insights than raw numbers, helping with strategic planning and identifying long-term patterns.

**Independent Test**: Can be tested by interacting with the chart components (Submission Trends, Status Pipeline, Author Geo) and ensuring they accurately reflect historical and current data.

**Acceptance Scenarios**:

1. **Given** 100 manuscripts are in "Under Review" and 20 are in "Production", **When** viewing the "Status Pipeline" chart, **Then** the chart accurately represents this distribution.
2. **Given** submissions increased by 20% in December, **When** viewing "Submission Trends", **Then** the line chart shows a corresponding upward trend.

---

### User Story 3 - Data Export for Reporting (Priority: P3)

As a Managing Editor, I want to export the dashboard data to an Excel or CSV file, so I can include the statistics in the annual editorial report or perform offline analysis.

**Why this priority**: While the dashboard is visual, offline reporting is a standard administrative requirement.

**Independent Test**: Can be tested by clicking the "Export Report" button and verifying the generated .xlsx or .csv file contains all the statistics displayed on the dashboard.

**Acceptance Scenarios**:

1. **Given** the dashboard is fully loaded with data, **When** the "Export Report" button is clicked and Excel is chosen, **Then** an .xlsx file is downloaded containing structured summary data.

---

### Edge Cases

- **Empty Database**: If the journal has no submissions yet, cards should show "0" or "N/A" and charts should display "No data available" states rather than crashing.
- **Large Data Volumes**: Performance must remain high (via SQL views/caching) even if there are tens of thousands of manuscript records.
- **Database Unavailability**: Error states should be handled gracefully with a user-friendly message and an "Attempt Reconnect" option.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display 4 KPI cards: "Monthly New/Total Pending Submissions", "Time to First Decision" (Average Days), "Yearly Acceptance Rate", and "Total Confirmed APC Revenue" (Monthly/Yearly).
- **FR-002**: System MUST render a "Submission Trends" line chart comparing new submissions and accepted papers (defined as those in 'Accepted' or 'Production' stages, excluding withdrawn manuscripts) over the last 12 months.
- **FR-003**: System MUST render a "Status Pipeline" chart (Funnel or Bar) showing counts of manuscripts in "Under Review", "Revision", and "Production".
- **FR-004**: System MUST render a "Decision Distribution" doughnut chart for "Accept", "Reject", "Major Revision", and "Minor Revision".
- **FR-005**: System MUST render a "Top 10 Author Geography" horizontal bar chart based on the corresponding author's affiliation.
- **FR-006**: System MUST provide an "Export Report" button supporting .xlsx and .csv formats containing an aggregated summary of the dashboard statistics.
- **FR-007**: System MUST calculate "Time to First Decision" by excluding Desk Rejects to focus on peer review efficiency.
- **FR-008**: System MUST display a global journal view accessible to both EIC and ME roles without additional isolation.

### Security & Authentication Requirements *(mandatory)*

- **SEC-001**: The Analytics Dashboard MUST be accessible only to users with 'Editor-in-Chief' or 'Managing Editor' roles (Principle XIII).
- **SEC-002**: All data fetching API endpoints MUST validate JWT tokens and check the user's role on every request (Principle XIII).
- **SEC-003**: Financial data (APC totals) MUST be protected with the same strict RBAC as editorial data (Principle XIII).
- **SEC-004**: Use the authenticated user's ID from the session context to verify authorization (Principle XIII).

### API Development Requirements *(mandatory)*

- **API-001**: Define OpenAPI specification for the `/api/v1/analytics/` endpoints BEFORE implementation (Principle XIV).
- **API-002**: Use consistent patterns like `/api/v1/analytics/summary` and `/api/v1/analytics/trends` (Principle XIV).
- **API-003**: All analytics APIs MUST be versioned under `/api/v1/` (Principle XIV).
- **API-004**: Each endpoint MUST include documentation describing the SQL logic/aggregation used (Principle XIV).
- **API-005**: Errors (e.g., database timeout) MUST be handled via a unified middleware with appropriate 5xx or 4xx responses (Principle XIV).

### Test Coverage Requirements *(mandatory)*

- **TEST-001**: Test GET methods for all analytics endpoints to ensure correct aggregation and filtering (Principle XII).
- **TEST-002**: Ensure frontend API calls match backend routes exactly (Principle XII).
- **TEST-003**: Verify that non-EIC/ME users receive 403 Forbidden when attempting to access analytics endpoints (Principle XII).
- **TEST-004**: Test aggregation logic with edge cases (e.g., leap years, manuscripts with missing affiliation data) (Principle XII).
- **TEST-005**: Integration tests MUST use a real database with populated test data to verify SQL View/RPC accuracy (Principle XII).
- **TEST-007**: Achieve 100% test pass rate for the analytics module before delivery (Principle XI).

### Key Entities *(include if feature involves data)*

- **Analytics Snapshot**: A point-in-time aggregation of editorial and financial metrics.
- **Submission Trend**: A time-series data point containing submission counts per month.
- **Geographic Point**: A pair of (Country, SubmissionCount) derived from author affiliations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dashboard renders all KPI cards and charts in under 2 seconds (P95) using cached data.
- **SC-002**: Data accuracy is 100% when compared to manual SQL queries on the raw manuscripts table.
- **SC-003**: Editors can export a full report in under 10 seconds for a dataset of up to 5,000 manuscripts.
- **SC-004**: 100% of chart visual elements follow the ScholarFlow brand guide (colors and typography).