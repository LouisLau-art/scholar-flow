# QA Regression Quickstart Guide

## Prerequisites

- **Docker & Docker Compose**: For running the test database and services.
- **Node.js (v20+) & pnpm**: For running the Playwright test suite.
- **Python (3.11+)**: For the backend services.

## 1. Local Setup

### 1.1. Start the Environment
Ensure the backend and frontend are running in "Test Mode" (connected to the test database).

```bash
# Start local services (Supabase, etc.)
npm run supabase:start

# Run the backend (ensure GO_ENV=test or similar configuration)
cd backend
uvicorn app.main:app --reload --port 8000
```

### 1.2. Install Test Dependencies
In the frontend directory (where Playwright is configured):

```bash
cd frontend
pnpm install
pnpm exec playwright install
```

## 2. Running E2E Tests

### 2.1. Run All Tests
Execute the full regression suite:

```bash
cd frontend
npm run test:e2e
```

### 2.2. Run Specific Tests
To run tests for a specific feature (e.g., submission):

```bash
npx playwright test tests/e2e/submission
```

### 2.3. Debug Mode
Run tests with the UI inspector:

```bash
npx playwright test --ui
```

## 3. Database Reset (Manual)

If you need to manually reset the database during development:

```bash
curl -X POST http://localhost:8000/api/v1/internal/reset-db
curl -X POST http://localhost:8000/api/v1/internal/seed-db
```

## 4. CI/CD Integration

The E2E suite is integrated into GitHub Actions via `.github/workflows/e2e.yml`.

- **Trigger**: Pushes to `main` and Pull Requests.
- **Steps**:
    1.  Checkout code.
    2.  Start Supabase (local/CI instance).
    3.  Build Backend & Frontend.
    4.  Run `reset-db` and `seed-db`.
    5.  Execute Playwright tests.
    6.  Upload artifacts (screenshots/videos) on failure.
