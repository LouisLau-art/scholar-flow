# Research: Executive Analytics Dashboard

**Feature Branch**: `014-analytics-dashboard`  
**Date**: 2026-01-30

## 1. Export Implementation (.xlsx / .csv)

- **Options**: `pandas` + `openpyxl`, `XlsxWriter`, `csv` module.
- **Decision**: **`pandas` + `openpyxl`**.
- **Rationale**: 
  - `pandas` makes it extremely easy to convert SQL results into dataframes and then to multiple formats.
  - `openpyxl` is the standard engine for modern `.xlsx` files in Python.
  - Consistent with potential future data analysis needs.

## 2. SQL Calculation Logic (Views & RPCs)

- **Decision**: Use **PostgreSQL Views** for fixed-window trends (last 12 months) and **RPCs** for dynamic KPI calculations (e.g., current month APC).
- **Rationale**: 
  - Views are great for standard reports that don't need parameters.
  - RPCs allow passing the current timestamp or specific filters if needed, while still executing in-database to avoid memory overhead.
- **Logic for "Time to First Decision"**:
  - Filter: `manuscripts.status != 'Desk Reject'`.
  - Calculation: `AVG(first_decision_at - submitted_at)`.
  - Metadata: Must include comments in SQL explaining the exclusion of Desk Rejects.

## 3. Frontend Visualization (Recharts + Shadcn)

- **Decision**: **Recharts**.
- **Rationale**: 
  - Mandated by spec.
  - Composition-based API fits perfectly with React.
  - Easy to style with CSS variables from Shadcn/UI theme.
- **Performance**: Use `memo` for chart components and ensure `React Query` handles the JSON response from Supabase.

## 4. Performance & Caching

- **Decision**: **Supabase Realtime + React Query Caching**.
- **Rationale**: 
  - `staleTime: 5 * 60 * 1000` (5 minutes) for analytics data.
  - Real-time updates are not strictly required for "historical trends", but current manuscript counts can benefit from shorter cache times.
- **Skeletons**: Use Shadcn `Skeleton` component to match the chart layout (e.g., a rectangular box with pulse effect for the line chart area).
