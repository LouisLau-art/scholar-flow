# Quickstart: 完善测试覆盖

**Feature Branch**: `009-test-coverage`
**Date**: 2026-01-29
**Purpose**: Quick setup guide for implementing test coverage feature

## Prerequisites

### System Requirements
- **OS**: Arch Linux (recommended) or any Linux distribution
- **Python**: 3.14+
- **Node.js**: 20.x+
- **Supabase**: Active project with database access

### Environment Variables

Create `.env` file in project root:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret

# Test Configuration
TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/test_db
COVERAGE_THRESHOLD_BACKEND=0.8
COVERAGE_THRESHOLD_FRONTEND=0.7
```

## Installation

### Backend Dependencies

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Install test-specific dependencies
pip install pytest pytest-cov pytest-asyncio httpx

# Verify installation
pytest --version
```

### Frontend Dependencies

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Install Playwright for E2E testing
npm install --save-dev @playwright/test

# Install Playwright browsers
npx playwright install

# Verify installation
npx playwright --version
```

## Configuration

### Backend: pytest Configuration

Create `backend/pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    -v
    --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    auth: Authentication tests
    error: Error handling tests
    boundary: Boundary condition tests
    concurrent: Concurrent request tests
```

Create `backend/.coveragerc`:

```ini
[run]
source = src
branch = True
omit =
    */tests/*
    */__pycache__/*
    */conftest.py
    */fixtures.py

[report]
precision = 2
show_missing = True
skip_covered = False
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod
    @abc.abstractmethod
```

### Frontend: Playwright Configuration

Create `frontend/playwright.config.ts`:

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

### Frontend: Vitest Configuration

Update `frontend/vitest.config.ts`:

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 70,
        statements: 70,
      },
      exclude: [
        'node_modules/',
        'tests/',
        '**/*.d.ts',
        '**/*.config.{js,ts}',
      ],
    },
  },
});
```

## Test Structure

### Backend Test Directory Structure

```
backend/tests/
├── conftest.py              # Pytest fixtures
├── fixtures.py              # Test data factories
├── unit/                    # Unit tests
│   ├── test_services.py
│   ├── test_models.py
│   └── test_utils.py
├── integration/             # Integration tests
│   ├── test_manuscripts.py
│   ├── test_auth.py
│   └── test_editor.py
└── contract/                # API contract tests
    ├── test_api_contracts.py
    └── test_openapi_spec.py
```

### Frontend Test Directory Structure

```
frontend/tests/
├── unit/                    # Vitest unit tests
│   ├── components/
│   │   ├── SubmissionForm.test.tsx
│   │   └── EditorDashboard.test.tsx
│   └── services/
│       └── api.test.ts
├── e2e/                     # Playwright E2E tests
│   ├── pages/               # Page Object Models
│   │   ├── login.page.ts
│   │   ├── submission.page.ts
│   │   ├── dashboard.page.ts
│   │   └── editor.page.ts
│   ├── specs/               # Test specifications
│   │   ├── authentication.spec.ts
│   │   ├── submission.spec.ts
│   │   └── editor.spec.ts
│   └── fixtures/
│       └── authenticated-user.ts
└── setup.ts                 # Test setup
```

## Writing Tests

### Backend: Authentication Test Example

```python
# backend/tests/integration/test_auth.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.mark.integration
@pytest.mark.auth
class TestAuthentication:
    """Test authentication endpoints"""

    def test_missing_jwt_token(self):
        """Test 401 error when JWT token is missing"""
        # Given
        endpoint = "/api/v1/manuscripts"

        # When
        response = client.get(endpoint)

        # Then
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_invalid_jwt_token(self):
        """Test 401 error when JWT token is invalid"""
        # Given
        endpoint = "/api/v1/manuscripts"
        headers = {"Authorization": "Bearer invalid.token.here"}

        # When
        response = client.get(endpoint, headers=headers)

        # Then
        assert response.status_code == 401

    def test_expired_jwt_token(self):
        """Test 401 error when JWT token is expired"""
        # Given
        endpoint = "/api/v1/manuscripts"
        expired_token = generate_expired_token()
        headers = {"Authorization": f"Bearer {expired_token}"}

        # When
        response = client.get(endpoint, headers=headers)

        # Then
        assert response.status_code == 401

    def test_cross_user_access(self):
        """Test 403 error when accessing other user's data"""
        # Given
        endpoint = "/api/v1/manuscripts/some-other-user-id"
        user1_token = generate_test_token(user_id="user-1")
        headers = {"Authorization": f"Bearer {user1_token}"}

        # When
        response = client.get(endpoint, headers=headers)

        # Then
        assert response.status_code == 403
```

### Backend: Boundary Condition Test Example

```python
# backend/tests/integration/test_boundary.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.mark.integration
@pytest.mark.boundary
class TestBoundaryConditions:
    """Test boundary conditions for input validation"""

    def test_title_min_length(self):
        """Test minimum title length validation"""
        # Given
        endpoint = "/api/v1/manuscripts"
        data = {
            "title": "",  # Empty title
            "abstract": "Valid abstract"
        }
        token = generate_test_token()
        headers = {"Authorization": f"Bearer {token}"}

        # When
        response = client.post(endpoint, json=data, headers=headers)

        # Then
        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any("title" in str(e).lower() for e in errors)

    def test_title_max_length(self):
        """Test maximum title length validation"""
        # Given
        endpoint = "/api/v1/manuscripts"
        data = {
            "title": "A" * 501,  # Exceeds 500 character limit
            "abstract": "Valid abstract"
        }
        token = generate_test_token()
        headers = {"Authorization": f"Bearer {token}"}

        # When
        response = client.post(endpoint, json=data, headers=headers)

        # Then
        assert response.status_code == 422

    def test_abstract_min_length(self):
        """Test minimum abstract length validation"""
        # Given
        endpoint = "/api/v1/manuscripts"
        data = {
            "title": "Valid Title",
            "abstract": ""  # Empty abstract
        }
        token = generate_test_token()
        headers = {"Authorization": f"Bearer {token}"}

        # When
        response = client.post(endpoint, json=data, headers=headers)

        # Then
        assert response.status_code == 422

    def test_abstract_max_length(self):
        """Test maximum abstract length validation"""
        # Given
        endpoint = "/api/v1/manuscripts"
        data = {
            "title": "Valid Title",
            "abstract": "A" * 5001  # Exceeds 5000 character limit
        }
        token = generate_test_token()
        headers = {"Authorization": f"Bearer {token}"}

        # When
        response = client.post(endpoint, json=data, headers=headers)

        # Then
        assert response.status_code == 422
```

### Backend: Concurrent Request Test Example

```python
# backend/tests/integration/test_concurrent.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.mark.integration
@pytest.mark.concurrent
class TestConcurrentRequests:
    """Test concurrent request handling"""

    @pytest.mark.asyncio
    async def test_concurrent_manuscript_submissions(self):
        """Test multiple users submitting manuscripts simultaneously"""
        # Given
        endpoint = "/api/v1/manuscripts"
        num_requests = 10

        async def submit_manuscript(user_id: str):
            """Submit a manuscript for a user"""
            data = {
                "title": f"Manuscript by {user_id}",
                "abstract": f"Abstract for {user_id}"
            }
            token = generate_test_token(user_id=user_id)
            headers = {"Authorization": f"Bearer {token}"}

            response = client.post(endpoint, json=data, headers=headers)
            return response.status_code, response.json()

        # When
        tasks = [
            submit_manuscript(f"user-{i}")
            for i in range(num_requests)
        ]
        results = await asyncio.gather(*tasks)

        # Then
        # All requests should succeed
        for status_code, _ in results:
            assert status_code == 201

        # Verify all manuscripts were created
        get_response = client.get(endpoint, headers={
            "Authorization": f"Bearer {generate_test_token()}"
        })
        assert get_response.status_code == 200
        manuscripts = get_response.json()
        assert len(manuscripts) >= num_requests
```

### Frontend: E2E Test Example

```typescript
// frontend/tests/e2e/specs/submission.spec.ts
import { test, expect } from '@playwright/test';
import { SubmissionPage } from '../pages/submission.page';
import { LoginPage } from '../pages/login.page';

test.describe('Manuscript Submission', () => {
  test('should show login prompt when user is not authenticated', async ({ page }) => {
    // Given
    const submissionPage = new SubmissionPage(page);

    // When
    await submissionPage.navigate();

    // Then
    await expect(page.locator('[data-testid="login-prompt"]')).toBeVisible();
    await expect(submissionPage.submitButton).toBeDisabled();
  });

  test('should successfully submit manuscript when authenticated', async ({ page }) => {
    // Given
    const loginPage = new LoginPage(page);
    const submissionPage = new SubmissionPage(page);

    // When
    await loginPage.login('test@example.com', 'password123');
    await submissionPage.navigate();
    await submissionPage.uploadPDF('./test-files/sample.pdf');
    await submissionPage.submit();

    // Then
    await expect(submissionPage.getSuccessMessage()).toBeVisible();
    await expect(page.locator('[data-testid="manuscript-list"]')).toContainText('Sample Manuscript');
  });

  test('should show validation error for empty form', async ({ page }) => {
    // Given
    const loginPage = new LoginPage(page);
    const submissionPage = new SubmissionPage(page);

    // When
    await loginPage.login('test@example.com', 'password123');
    await submissionPage.navigate();
    await submissionPage.submit();

    // Then
    await expect(page.locator('[data-testid="form-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="title-error"]')).toContainText('required');
  });
});

test.describe('Editor Dashboard', () => {
  test('should show pending manuscripts list for editor', async ({ page }) => {
    // Given
    const loginPage = new LoginPage(page);

    // When
    await loginPage.login('editor@example.com', 'password123');
    await page.goto('/dashboard');

    // Then
    await expect(page.locator('[data-testid="pending-manuscripts"]')).toBeVisible();
    await expect(page.locator('[data-testid="manuscript-item"]')).toHaveCount(5);
  });

  test('should allow editor to assign reviewer', async ({ page }) => {
    // Given
    const loginPage = new LoginPage(page);

    // When
    await loginPage.login('editor@example.com', 'password123');
    await page.goto('/dashboard');
    await page.locator('[data-testid="assign-reviewer-btn"]').first().click();
    await page.locator('[data-testid="reviewer-option"]').first().click();
    await page.locator('[data-testid="confirm-assignment"]').click();

    // Then
    await expect(page.locator('[data-testid="success-toast"]')).toBeVisible();
    await expect(page.locator('[data-testid="manuscript-status"]')).toContainText('Assigned');
  });
});
```

### Frontend: Page Object Example

```typescript
// frontend/tests/e2e/pages/submission.page.ts
import { Page, Locator } from '@playwright/test';

export class SubmissionPage {
  readonly page: Page;
  readonly submitButton: Locator;
  readonly fileInput: Locator;
  readonly titleInput: Locator;
  readonly abstractInput: Locator;

  constructor(page: Page) {
    this.page = page;
    this.submitButton = page.locator('button[type="submit"]');
    this.fileInput = page.locator('input[type="file"]');
    this.titleInput = page.locator('input[name="title"]');
    this.abstractInput = page.locator('textarea[name="abstract"]');
  }

  async navigate(): Promise<void> {
    await this.page.goto('/submit');
  }

  async uploadPDF(filePath: string): Promise<void> {
    await this.fileInput.setInputFiles(filePath);
  }

  async fillTitle(title: string): Promise<void> {
    await this.titleInput.fill(title);
  }

  async fillAbstract(abstract: string): Promise<void> {
    await this.abstractInput.fill(abstract);
  }

  async submit(): Promise<void> {
    await this.submitButton.click();
  }

  async getSuccessMessage(): Promise<Locator> {
    return this.page.locator('[data-testid="success-toast"]');
  }

  async getErrorMessage(): Promise<Locator> {
    return this.page.locator('[data-testid="error-toast"]');
  }
}
```

## Running Tests

### Backend Tests

```bash
# Run all backend tests
cd backend
pytest

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term-missing

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m auth          # Authentication tests only
pytest -m error         # Error handling tests only
pytest -m boundary      # Boundary condition tests only
pytest -m concurrent    # Concurrent request tests only

# Run specific test file
pytest tests/integration/test_manuscripts.py

# Run with verbose output
pytest -v

# Run with parallel execution (requires pytest-xdist)
pytest -n auto
```

### Frontend Unit Tests

```bash
# Run all frontend unit tests
cd frontend
npm run test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run specific test file
npm run test -- tests/unit/components/SubmissionForm.test.tsx
```

### Frontend E2E Tests

```bash
# Run all E2E tests
cd frontend
npm run test:e2e

# Run with UI mode (interactive)
npm run test:e2e:ui

# Run specific test file
npm run test:e2e -- tests/e2e/specs/submission.spec.ts

# Run with specific browser
npx playwright test --project=chromium

# Run in headed mode (visible browser)
npx playwright test --headed
```

### Combined Test Run

```bash
# Run all tests (backend + frontend)
./scripts/run-all-tests.sh

# Or manually:
cd backend && pytest --cov=src --cov-report=html && cd ..
cd frontend && npm run test && npm run test:e2e
```

## Coverage Reports

### Backend Coverage Report

```bash
# Generate HTML coverage report
cd backend
pytest --cov=src --cov-report=html

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Frontend Coverage Report

```bash
# Generate coverage report
cd frontend
npm run test:coverage

# View report
open coverage/index.html  # macOS
xdg-open coverage/index.html  # Linux
```

### Combined Coverage Report

```bash
# Run coverage for both backend and frontend
./scripts/generate-coverage-report.sh

# This will:
# 1. Run backend tests with coverage
# 2. Run frontend unit tests with coverage
# 3. Generate combined HTML report
# 4. Display coverage summary
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Test

on:
  push:
    branches: [main, 009-test-coverage]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install backend dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Install frontend dependencies
        run: |
          cd frontend
          npm ci
          npx playwright install --with-deps

      - name: Run backend tests
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          SUPABASE_JWT_SECRET: ${{ secrets.SUPABASE_JWT_SECRET }}
        run: |
          cd backend
          pytest --cov=src --cov-report=xml --cov-fail-under=80

      - name: Run frontend unit tests
        run: |
          cd frontend
          npm run test:coverage

      - name: Run frontend E2E tests
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: |
          cd frontend
          npm run test:e2e

      - name: Upload coverage reports
        uses: codecov/codecov-action@v4
        with:
          files: ./backend/coverage.xml,./frontend/coverage/lcov.info
          fail_ci_if_error: true
```

## Troubleshooting

### Common Issues

**Issue**: Playwright browsers not installed
```bash
# Solution
cd frontend
npx playwright install --with-deps
```

**Issue**: Supabase connection timeout
```bash
# Solution: Check environment variables
echo $SUPABASE_URL
echo $SUPABASE_KEY

# Verify .env file exists and has correct values
cat .env
```

**Issue**: pytest coverage below threshold
```bash
# Solution: Check coverage report
pytest --cov=src --cov-report=term-missing

# Add more tests for uncovered lines
```

**Issue**: E2E tests failing in CI
```bash
# Solution: Run with retries
npx playwright test --retries=2

# Or check browser compatibility
npx playwright test --project=chromium
```

## Next Steps

1. **Phase 1**: Write unit tests for existing code
2. **Phase 2**: Write integration tests with real database
3. **Phase 3**: Write E2E tests with Playwright
4. **Phase 4**: Generate coverage reports
5. **Phase 5**: Add coverage thresholds to CI/CD

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Playwright Documentation](https://playwright.dev/)
- [Vitest Documentation](https://vitest.dev/)
- [Supabase Python SDK](https://supabase.com/docs/reference/python)
- [Supabase JavaScript SDK](https://supabase.com/docs/reference/javascript)
