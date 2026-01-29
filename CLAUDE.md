# scholar-flow Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-29

## Active Technologies

- Python 3.14+, TypeScript 5.x, Node.js 20.x + FastAPI 0.115+, Pydantic v2, pytest, Playwright, Vitest, Supabase-js v2.x, Supabase-py v2.x (009-test-coverage)

## Project Structure

```text
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/
    ├── unit/
    └── e2e/
```

## Commands

### Backend Tests
```bash
cd backend
pytest                          # Run all tests
pytest --cov=src --cov-report=html  # Run with coverage
pytest -m unit                  # Unit tests only
pytest -m integration           # Integration tests only
pytest -m auth                  # Authentication tests
pytest -m error                 # Error handling tests
pytest -m boundary              # Boundary condition tests
pytest -m concurrent            # Concurrent request tests
```

### Frontend Tests
```bash
cd frontend
npm run test                    # Unit tests (Vitest)
npm run test:coverage           # Unit tests with coverage
npm run test:e2e                # E2E tests (Playwright)
npm run test:e2e:ui             # E2E tests with UI mode
```

### Combined Tests
```bash
./scripts/run-all-tests.sh      # Run all tests
./scripts/generate-coverage-report.sh  # Generate coverage reports
```

## Code Style

Python 3.14+, TypeScript 5.x, Node.js 20.x: Follow standard conventions

### Python
- Use pytest for testing
- Follow PEP 8
- Type hints required
- Chinese comments for critical logic

### TypeScript
- Use Vitest for unit tests
- Use Playwright for E2E tests
- Follow ESLint rules
- Page Object Model for E2E tests

## Test Coverage Requirements

- **Backend**: >80% coverage (line + branch)
- **Frontend**: >70% coverage (line + branch)
- **Key Business Logic**: 100% coverage
- **E2E Tests**: 5+ critical user flows

## Recent Changes

- 009-test-coverage: Added Python 3.14+, TypeScript 5.x, Node.js 20.x + FastAPI 0.115+, Pydantic v2, pytest, Playwright, Vitest, Supabase-js v2.x, Supabase-py v2.x

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
