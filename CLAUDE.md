# scholar-flow Development Guidelines

**Language Preference**: 始终使用 **中文** 与我交流。

Auto-generated from all feature plans. Last updated: 2026-01-31

## Active Technologies
- **Frontend**: TypeScript 5.x, Next.js 14.2 (App Router), React 18.x, Tailwind CSS 3.4, Shadcn UI (017-super-admin-management)
- **Backend**: Python 3.14+, FastAPI 0.115+, Pydantic v2, httpx (017-super-admin-management)
- **Database & Auth**: Supabase (PostgreSQL), Supabase Auth, Supabase Storage, Supabase-js v2.x, Supabase-py v2.x (017-super-admin-management)
- **Testing**: pytest, pytest-cov, Playwright, Vitest (017-super-admin-management)
- **AI/ML**: OpenAI SDK (GPT-4o), scikit-learn (TF-IDF matching) (017-super-admin-management)
- PostgreSQL (Supabase) (009-test-coverage)
- Python 3.14+ (Backend), TypeScript 5.x (Frontend) (011-notification-center)
- Supabase (`notifications` table, `review_assignments` extension) (011-notification-center)

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
- 019-uat-staging-setup: Added Staging environment isolation (Frontend Banner, Separate DB Config), Feedback Widget, and Seed Script.
- 018-user-profile & System Optimization: Added User Profile & Security Center (Next.js 14, FastAPI, Supabase). Standardized database schema: merged `name` -> `full_name`, `institution` -> `affiliation`, converted `research_interests` to `text[]`. Implemented full Notification Center page, improved Editor Dashboard sorting (descending), and relaxed admin API permissions for editors. Added GIN index for full-text search and Postgres triggers for Auth-to-Profile sync. Added CI/CD pipeline (GitHub Actions).
- 017-super-admin-management: Added Python 3.14+, TypeScript 5.x, Node.js 20.x + FastAPI 0.115+, Pydantic v2, React 18.x, Next.js 14.2.x, Shadcn/UI, Tailwind CSS 3.4.x
- 011-notification-center: Added notifications table + RLS, email templates (SMTP/Jinja2), internal cron chase endpoint, in-app Bell UI with Supabase Realtime

## 🛡️ Security & Authentication Principles
- **Authentication First**: All sensitive operations MUST require authentication. Never allow unauthenticated access to user-specific data.
- **JWT Validation**: Use Supabase JWT tokens for all authenticated requests. Tokens must be validated on every request.
- **Real User Context**: Use actual user IDs from authentication context, never hardcoded or simulated IDs.
- **Role-Based Access**: Implement proper role-based access control (RBAC) for different user types (author, reviewer, editor).
- **Security by Design**: Security considerations must be addressed during initial design, not as an afterthought.

## 🧪 Testing Strategy (Lessons Learned)
### Test Coverage Requirements
- **Complete API Testing**: Test ALL HTTP methods (GET, POST, PUT, DELETE) for every endpoint.
- **Path Consistency**: Ensure frontend and backend API paths match EXACTLY (including trailing slashes).
- **Authentication Testing**: Every authenticated endpoint MUST have tests for:
  - Valid authentication (success case)
  - Missing authentication (401 error)
  - Invalid/expired tokens (401 error)
- **Validation Testing**: Test all input validation rules (required fields, length limits, format constraints).
- **Error Scenario Testing**: Test error cases, not just happy paths.

### Test Pyramid Strategy
```
End-to-End Tests (E2E) - Simulate real user workflows
    ↓
Integration Tests - Verify component integration
    ↓
Unit Tests - Test individual functions/components
```

### Mock vs Real Testing
- **Unit Tests**: Use Mock objects for speed and isolation
- **Integration Tests**: Use REAL database connections to catch integration issues
- **E2E Tests**: Use test database to simulate production environment
- **Never rely solely on Mocks**: Mocks can hide real integration problems

## 🔧 Development Process Guidelines
### API Development
- **API-First Design**: Define API contracts (OpenAPI/Swagger) BEFORE implementation
- **Path Convention**: Use consistent path patterns (no trailing slashes unless necessary)
- **Versioning**: Always version APIs (e.g., `/api/v1/`)
- **Documentation**: Every endpoint MUST have clear documentation

### Error Handling
- **Unified Error Handling**: Use middleware for consistent error responses
- **Detailed Logging**: Log all critical operations and errors
- **User-Friendly Messages**: Provide clear error messages to users
- **Debug Information**: Include sufficient debug info for developers

### Data Validation
- **Multi-Layer Validation**:
  - Frontend: Basic validation for UX
  - Backend API: Comprehensive validation (Pydantic v2)
  - Database: Constraints and triggers as last line of defense
- **Field Constraints**: Always specify min/max length, format, and business rules
- **Type Safety**: Use TypeScript (frontend) and type hints (Python) extensively



## 📊 Quality Assurance Standards
### Code Quality
- **Type Safety**: 100% type coverage (TypeScript, Python type hints)
- **No Warnings**: Zero deprecation warnings (e.g., Pydantic v2 ConfigDict)
- **Code Review**: All changes must be reviewed before merging
- **Pre-commit Hooks**: Run linting and tests before commits

### Testing Standards
- **100% Test Pass Rate**: No code changes without passing tests
- **Test Coverage**: Aim for >80% code coverage on critical paths
- **Continuous Testing**: Run tests on every commit
- **CI/CD Integration**: Automated testing in CI pipeline



## 🎯 User Experience Principles
### Feature Completeness
- **Core User Flows**: Every user role must have complete workflows
- **User Dashboard**: Users should see their own data (e.g., "My Submissions")
- **Clear Navigation**: Users always know where they are and what they can do
- **Error Recovery**: Graceful error handling with clear next steps

### Authentication UX
- **Login Prompts**: Clear indication when authentication is required
- **Session Management**: Handle token expiration gracefully
- **User Feedback**: Provide immediate feedback on authentication status
- **Redirect Handling**: Proper redirect after login/logout
- **Environment Awareness**: Explicit visual cues when in Staging/UAT environments.

### Data Accuracy
- **Real User Context**: Never use simulated or hardcoded user data
- **Data Integrity**: Ensure data consistency across the system
- **Audit Trail**: Track who made what changes and when



## 🚀 Deployment & Operations
### Environment Management
- **Development vs Production**: Clear separation of dev/prod configurations
- **Environment Variables**: Use proper env vars for configuration
- **Secret Management**: Never commit secrets to version control
- **Staging Isolation**: Strictly separate database and frontend visual indicators for UAT.



## 📈 Continuous Improvement
### Post-Mortem Culture
- **Learn from Issues**: Document and learn from every bug or issue
- **Root-Cause Analysis**: Find and fix root causes, not just symptoms
- **Process Improvement**: Update processes based on lessons learned

### Regular Reviews
- **Code Review**: Regular code reviews for quality and learning
- **Architecture Review**: Periodic review of architecture decisions
- **Test Review**: Ensure tests remain relevant and comprehensive

### Documentation
- **Keep Updated**: Update documentation when code changes
- **Lessons Learned**: Document patterns and anti-patterns
- **Best Practices**: Share and document best practices

<!-- MANUAL ADDITIONS START -->
## 环境约定 / Environment Assumptions（AGENTS / CLAUDE / GEMINI 三份需保持一致）

- **默认数据库**：使用**云端 Supabase**（project ref：`mmvulyrfsorqdpdrzbkd`，见 `backend/.env` 里的 `SUPABASE_URL`）。
- **Schema 来源**：以仓库内 `supabase/migrations/*.sql` 为准；若云端未应用最新 migration（例如缺少 `public.manuscripts.version`），后端修订集成测试会出现 `PGRST204` 并被跳过/失败。
- **云端迁移同步（Supabase CLI）**：在 repo root 执行 `supabase projects list`（确认已 linked）→ `supabase db push --dry-run` → `supabase db push`（按提示输入 `y`）。若 CLI 不可用/失败，则到 Supabase Dashboard 的 SQL Editor 依次执行 `supabase/migrations/*.sql`（至少包含 `20260201000000/00001/00002/00003`）并可执行 `select pg_notify('pgrst', 'reload schema');` 刷新 schema cache。
- **后端单文件测试注意**：`backend/pytest.ini` 强制 `--cov-fail-under=80`，单跑一个文件可能因覆盖率门槛失败；单文件验证用 `pytest -o addopts= tests/integration/test_revision_cycle.py`。
- **E2E 鉴权说明**：`frontend/src/middleware.ts` 在 **非生产环境** 且请求头带 `x-scholarflow-e2e: 1`（或 Supabase Auth 不可用）时，允许从 Supabase session cookie 解析用户用于 Playwright；生产环境不会启用该降级逻辑。
- **CI-like 一键测试**：`./scripts/run-all-tests.sh` 默认跑 `backend pytest` + `frontend vitest` + mocked E2E（`frontend/tests/e2e/specs/revision_flow.spec.ts`）。可用 `PLAYWRIGHT_PORT` 改端口，`E2E_SPEC` 指定单个 spec。若要跑全量 Playwright：`E2E_FULL=1 ./scripts/run-all-tests.sh`（脚本会尝试启动 `uvicorn main:app --port 8000`，可用 `BACKEND_PORT` 覆盖）。
- **安全提醒**：云端使用 `SUPABASE_SERVICE_ROLE_KEY` 等敏感凭证时，务必仅存于本地/CI Secret，避免提交到仓库；如已泄露请立即轮换。
<!-- MANUAL ADDITIONS END -->
