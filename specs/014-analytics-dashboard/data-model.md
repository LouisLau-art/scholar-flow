# Data Model: Executive Analytics Dashboard

**Feature Branch**: `014-analytics-dashboard`  
**Date**: 2026-01-30

## 1. Database Views (PostgreSQL)

### `view_submission_trends`
- **Purpose**: Aggregates submissions and acceptances by month for the last 12 months.
- **Columns**: `month` (date), `submission_count` (int), `acceptance_count` (int).

### `view_status_pipeline`
- **Purpose**: Current snapshot of manuscripts in active stages.
- **Columns**: `stage` (text), `count` (int).
- **Stages**: 'Under Review', 'Revision', 'Production'.

## 2. Remote Procedure Calls (RPCs)

### `get_journal_kpis()`
- **Purpose**: Returns the 4 core KPI cards data.
- **Returns**: 
  ```json
  {
    "new_submissions_month": 12,
    "total_pending": 45,
    "avg_first_decision_days": 24.5,
    "yearly_acceptance_rate": 0.18,
    "apc_revenue_month": 15000.0,
    "apc_revenue_year": 120000.0
  }
  ```

### `get_author_geography()`
- **Purpose**: Aggregates submissions by country from `authors` table linked to `manuscripts`.
- **Returns**: `TABLE(country text, submission_count int)`.

## 3. Relationships & Logic
- **Time to First Decision**: Calculated using `manuscripts.submitted_at` and `manuscripts.first_decision_date`.
- **APC Revenue**: Sum of `invoices.amount` where `status = 'Paid'`.
- **Exclusion**: All Peer Review metrics exclude `desk_reject` status.
