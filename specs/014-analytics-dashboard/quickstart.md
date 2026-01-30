# Quickstart: Executive Analytics Dashboard

## 1. Environment Setup
- Ensure Python dependencies are installed: `pip install pandas openpyxl`
- Ensure Frontend dependencies are installed: `pnpm add recharts @tanstack/react-query`

## 2. Database Migration
- Run the SQL scripts in `supabase/migrations/` to create views and RPCs.
- Verify RPCs using Supabase Dashboard SQL Editor.

## 3. Local Development
- Start Backend: `uvicorn main:app --reload`
- Start Frontend: `pnpm dev`
- Navigate to `/editor/analytics` (RBAC required: ME or EIC).

## 4. Verification Scenarios
- **KPI Accuracy**: Compare Dashboard cards with manual `SELECT COUNT(*) FROM manuscripts`.
- **Chart Rendering**: Verify Recharts animations and Tailwind styling.
- **Export**: Click "Export Report" and check if the file opens correctly in Excel.
