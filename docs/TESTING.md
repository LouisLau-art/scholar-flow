# Testing Guide

This document outlines the testing strategy and procedures for Scholar Flow, focusing on End-to-End (E2E) regression testing.

## Overview

We use **Playwright** for E2E testing to validate critical user journeys across the integrated system (Frontend + Backend + Database).

## Prerequisites

- **Docker & Docker Compose**: For running the test database and services.
- **Node.js (v20+) & pnpm**: For running the Playwright test suite.
- **Python (3.11+)**: For the backend services.

## 1. Local Environment Setup

### 1.1. Start Services
Ensure the backend and frontend are running in "Test Mode" (connected to the test database).

```bash
# Start Supabase (local)
npm run supabase:start

# Run the Backend
# Ensure GO_ENV=test (enables /internal/reset-db endpoint)
cd backend
export GO_ENV=test
uvicorn app.main:app --reload --port 8000
```

### 1.2. Install Dependencies
```bash
cd frontend
pnpm install
pnpm exec playwright install
```

## 2. Running E2E Tests

### 2.1. Run Full Suite
Execute the comprehensive regression suite:

```bash
cd frontend
npm run test:e2e
```

### 2.2. Run Specific Features
To run tests for a specific user journey (e.g., Author Flow):

```bash
npx playwright test tests/e2e/author-flow.spec.ts
```

### 2.3. Debugging
Run tests with the UI inspector to step through execution:

```bash
npx playwright test --ui
```

## 3. Database Management

The test suite automatically resets and seeds the database before execution (configured in `global-setup.ts`).

### Manual Reset
If you need to manually reset the database during development:

```bash
# Truncate all public tables
curl -X POST http://localhost:8000/api/v1/internal/reset-db \
  -H "Authorization: Bearer <ADMIN_TOKEN>"

# Seed standard test data (Users, Journals, Manuscripts)
curl -X POST http://localhost:8000/api/v1/internal/seed-db \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

## 4. Test Data Strategy

### Seeded Users
| Role | Email | Password |
| :--- | :--- | :--- |
| **Author** | `author@example.com` | `password123` |
| **Editor** | `editor@example.com` | `password123` |
| **Reviewer 1** | `reviewer1@example.com` | `password123` |
| **Admin** | `admin@example.com` | `password123` |

### Seeded Manuscripts
- **The Impact of Automated Testing**: Submitted
- **Algorithms for Peer Review**: Under Review
- **Finalized Research Paper**: Accepted/Published
- **Ready for Decision**: Pending Decision

## 5. CI/CD Integration

The E2E suite runs on GitHub Actions on every push to `main` and PRs.
Artifacts (screenshots, traces) are uploaded on failure for debugging.

```