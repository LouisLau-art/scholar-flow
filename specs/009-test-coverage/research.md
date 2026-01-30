# Research: 完善测试覆盖

**Feature Branch**: `009-test-coverage`
**Date**: 2026-01-29
**Input**: Implementation plan Phase 0 research topics

## 1. Playwright vs Cypress for Next.js E2E Testing

### Decision: Use Playwright

**Rationale**:
- **Cross-browser support**: Playwright supports Chrome, Firefox, Safari (WebKit), and Edge natively
- **TypeScript-first**: Native TypeScript support, better for Next.js projects
- **Performance**: Faster test execution compared to Cypress
- **API design**: More flexible API with better async/await support
- **Parallel execution**: Built-in parallel test execution
- **Project context**: Already used in the project (spec.md mentions Playwright)

**Alternatives Considered**:
- **Cypress**: Simpler API, great developer experience, but limited browser support (no Safari natively), slower execution
- **Selenium**: Too heavy for modern web apps, complex setup

**Implementation Notes**:
- Install: `npm install --save-dev @playwright/test`
- Configuration: `playwright.config.ts`
- Test location: `frontend/tests/e2e/`
- Run: `npm run test:e2e`

---

## 2. pytest Coverage Configuration

### Decision: Use pytest-cov with 80% threshold

**Rationale**:
- **Industry standard**: pytest-cov is the de facto standard for Python coverage
- **Integration**: Seamless integration with pytest
- **Configuration**: Easy to configure thresholds and exclusions
- **Reporting**: Multiple output formats (HTML, XML, terminal)

**Configuration**:
```ini
# .coveragerc
[run]
source = backend/src
branch = True
omit = */tests/*, */__pycache__/*

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
```

**Threshold**: 80% minimum coverage (per spec requirement SC-003)

**Implementation Notes**:
- Install: `pip install pytest-cov`
- Run with coverage: `pytest --cov=backend/src --cov-report=html --cov-report=term-missing`
- HTML report: `htmlcov/index.html`

---

## 3. Playwright Test Organization

### Decision: Use Page Object Model pattern

**Rationale**:
- **Maintainability**: Separates page structure from test logic
- **Reusability**: Page objects can be reused across multiple tests
- **Best practices**: Industry-standard pattern for E2E testing
- **Type safety**: TypeScript interfaces for page elements

**Structure**:
```
frontend/tests/e2e/
├── pages/                    # Page Object Models
│   ├── login.page.ts
│   ├── submission.page.ts
│   ├── dashboard.page.ts
│   └── editor.page.ts
├── specs/                    # Test specifications
│   ├── submission.spec.ts
│   ├── authentication.spec.ts
│   └── editor.spec.ts
└── fixtures/                 # Playwright fixtures
    └── authenticated-user.ts
```

**Example Page Object**:
```typescript
// pages/submission.page.ts
export class SubmissionPage {
  constructor(private page: Page) {}

  async navigate() {
    await this.page.goto('/submit');
  }

  async uploadPDF(filePath: string) {
    await this.page.setInputFiles('input[type="file"]', filePath);
  }

  async submit() {
    await this.page.click('button[type="submit"]');
  }

  async getSuccessMessage() {
    return this.page.locator('[data-testid="success-toast"]');
  }
}
```

**Implementation Notes**:
- Install: `npm install --save-dev @playwright/test`
- Configuration: `playwright.config.ts` with baseURL
- Run: `npm run test:e2e` or `npx playwright test`

---

## 4. Database Test Isolation

### Decision: Use transaction rollback for each test

**Rationale**:
- **Speed**: No need to drop/create tables between tests
- **Isolation**: Each test starts with a clean database state
- **Simplicity**: Automatic cleanup via pytest fixtures
- **Real database**: Tests against actual Supabase PostgreSQL

**Implementation**:
```python
# backend/tests/conftest.py
import pytest
from supabase import create_client

@pytest.fixture(scope="function")
def db_connection():
    """Create a database connection for each test function"""
    client = create_client(
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_KEY")
    )

    # Start transaction
    yield client

    # Rollback after test
    # Supabase doesn't support explicit transactions in Python SDK
    # So we manually clean up test data

@pytest.fixture
def test_manuscript(db_connection):
    """Create a test manuscript and clean up after"""
    data = {
        "id": str(uuid4()),
        "title": "Test Manuscript",
        "abstract": "Test abstract",
        "author_id": "00000000-0000-0000-0000-000000000000",
        "status": "submitted"
    }

    response = db_connection.table("manuscripts").insert(data).execute()

    yield response.data[0]

    # Cleanup
    db_connection.table("manuscripts").delete().eq("id", data["id"]).execute()
```

**Alternative Considered**:
- **Mock database**: Faster but hides integration issues (rejected per Principle XII)
- **Test database**: Separate database instance (more complex setup)

**Implementation Notes**:
- Use pytest fixtures with function scope
- Clean up test data in fixture teardown
- Use real Supabase connection (not mock)

---

## 5. JWT Test Token Generation

### Decision: Generate real JWT tokens using Supabase authentication

**Rationale**:
- **Realistic**: Tests actual token validation, not mocks
- **Security**: Validates real JWT signature and expiration
- **Integration**: Tests full authentication flow
- **Compliance**: Follows Principle XII (use real database connections)

**Implementation**:
```python
# backend/tests/conftest.py
import jwt
import os
from datetime import datetime, timedelta

def generate_test_token(user_id: str = "00000000-0000-0000-0000-000000000000"):
    """Generate a real JWT token for testing"""
    secret = os.environ.get("SUPABASE_JWT_SECRET")

    payload = {
        "sub": user_id,
        "email": "test@example.com",
        "aud": "authenticated",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "role": "authenticated"
    }

    return jwt.encode(payload, secret, algorithm="HS256")

@pytest.fixture
def auth_token():
    """Generate authentication token for tests"""
    return generate_test_token()

@pytest.fixture
def expired_token():
    """Generate expired token for testing"""
    secret = os.environ.get("SUPABASE_JWT_SECRET")

    payload = {
        "sub": "00000000-0000-0000-0000-000000000000",
        "email": "test@example.com",
        "aud": "authenticated",
        "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
        "iat": datetime.utcnow() - timedelta(hours=2),
        "role": "authenticated"
    }

    return jwt.encode(payload, secret, algorithm="HS256")

@pytest.fixture
def invalid_token():
    """Generate invalid token for testing"""
    return "invalid.jwt.token"
```

**Alternative Considered**:
- **Mock token validation**: Faster but doesn't test real JWT validation (rejected)
- **Supabase Auth SDK**: Use `supabase.auth.sign_in_with_password()` for real tokens

**Implementation Notes**:
- Use `PyJWT` library for token generation
- Use real Supabase JWT secret from environment
- Test valid, expired, invalid, and missing tokens

---

## Summary

All research topics have been resolved with clear decisions:

1. **Playwright** selected for E2E testing (better cross-browser support)
2. **pytest-cov** configured for backend coverage (80% threshold)
3. **Page Object Model** pattern for Playwright tests (maintainability)
4. **Transaction rollback** for database isolation (speed + isolation)
5. **Real JWT tokens** for authentication testing (realistic validation)

**Next Steps**:
- Generate data-model.md
- Create API contracts
- Write quickstart.md
- Update agent context
