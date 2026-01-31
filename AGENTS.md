# Repository Guidelines

**Language Preference**: 始终使用 **中文** 与我交流。

Auto-generated from all feature plans. Last updated: 2026-01-30

## Active Technologies
- **Frontend**: TypeScript 5.x, Next.js 14.2 (App Router), React 18.x, Tailwind CSS 3.4, Shadcn UI
- **Backend**: Python 3.14+, FastAPI 0.115+, Pydantic v2, httpx
- **Database & Auth**: Supabase (PostgreSQL), Supabase Auth, Supabase Storage, Supabase-js v2.x, Supabase-py v2.x
- **Testing**: pytest, pytest-cov, Playwright, Vitest
- **AI/ML**: OpenAI SDK (GPT-4o), scikit-learn (TF-IDF matching)
- PostgreSQL (Supabase) (009-test-coverage)
- Python 3.14+ (Backend), TypeScript 5.x (Frontend) + FastAPI 0.115+, Pydantic v2, httpx, lxml (Backend); Next.js 14.2, React 18.x (Frontend) (015-academic-indexing)
- PostgreSQL (Supabase) - 新增 `doi_registrations` 和 `doi_tasks` 表 (015-academic-indexing)

## Project Structure

```text
backend/
├── app/
│   ├── api/v1/          # FastAPI Routes (Manuscripts, Reviews, Plagiarism, Editor)
│   ├── core/            # Business Logic & Workers (AI Engine, PDF Processor, Workers)
│   ├── models/          # Pydantic v2 Schemas
│   └── services/        # Third-party Integrations (Crossref Client, Editorial)
├── scripts/             # Verification & Utility Scripts
└── tests/               # Pytest Suite (unit, integration, contract)

frontend/
├── src/
│   ├── app/             # Next.js App Router (submit, admin, finance, review, editor)
│   ├── components/      # UI Components (SubmissionForm, PlagiarismActions, EditorDashboard, etc.)
│   ├── lib/             # API Client & Supabase Config
│   └── types/           # TypeScript Interfaces
└── tests/               # Vitest (unit) + Playwright (e2e)
```

## Commands

### Backend
- **Run**: `uvicorn main:app --reload`
- **Tests**: `pytest` (all tests), `pytest --cov=src --cov-report=html` (with coverage)
- **Linting**: `ruff check .`

### Frontend
- **Run**: `pnpm dev`
- **Tests**: `npm run test` (Vitest unit tests), `npm run test:coverage` (with coverage)
- **E2E Tests**: `npm run test:e2e` (Playwright), `npm run test:e2e:ui` (with UI)
- **Linting**: `pnpm lint`

### Combined
- **All Tests**: `./scripts/run-all-tests.sh`
- **Coverage Report**: `./scripts/generate-coverage-report.sh`

### Database
- **Migration**: `supabase migration new [name]`

## Code Style
- **Naming**: camelCase for Frontend, snake_case for Backend.
- **Comments**: Mandatory **Chinese comments** for core logic (algorithms, security).
- **Architecture**: Server Components first, unified API client encapsulation.
- **Strict QA**: **100% test pass rate** required for all feature deliveries.
- **Native Only**: Use native Supabase SDKs; explicit full-path routing only.
- **Type Safety**: TypeScript (frontend) and Python type hints (backend) required.

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

### Performance Standards
- **Response Time**: API responses < 500ms for standard requests
- **Page Load**: Frontend page loads < 2 seconds
- **Database Queries**: Optimize queries to avoid N+1 problems
- **Caching Strategy**: Implement caching for frequently accessed data

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

### Data Accuracy
- **Real User Context**: Never use simulated or hardcoded user data
- **Data Integrity**: Ensure data consistency across the system
- **Audit Trail**: Track who made what changes and when

## 🚀 Deployment & Operations
### Environment Management
- **Development vs Production**: Clear separation of dev/prod configurations
- **Environment Variables**: Use proper env vars for configuration
- **Secret Management**: Never commit secrets to version control

### Hot Reload Awareness
- **Development**: Use `--reload` for automatic restart (FastAPI) and HMR (Next.js)
- **Production**: Manual restart required; hot reload disabled
- **State Management**: Be aware that restarts clear in-memory state

### Monitoring & Logging
- **Structured Logging**: Use consistent log format with timestamps
- **Error Tracking**: Monitor and track all errors
- **Performance Monitoring**: Monitor response times and resource usage
- **Security Auditing**: Log security-relevant events

## 📈 Continuous Improvement
### Post-Mortem Culture
- **Learn from Issues**: Document and learn from every bug or issue
- **Root Cause Analysis**: Find and fix root causes, not just symptoms
- **Process Improvement**: Update processes based on lessons learned

### Regular Reviews
- **Code Review**: Regular code reviews for quality and learning
- **Architecture Review**: Periodic review of architecture decisions
- **Test Review**: Ensure tests remain relevant and comprehensive

### Documentation
- **Keep Updated**: Update documentation when code changes
- **Lessons Learned**: Document patterns and anti-patterns
- **Best Practices**: Share and document best practices

## Recent Changes
- 015-academic-indexing: Added Python 3.14+ (Backend), TypeScript 5.x (Frontend) + FastAPI 0.115+, Pydantic v2, httpx, lxml (Backend); Next.js 14.2, React 18.x (Frontend)
- 010-ui-standardization: Added Shadcn config + CSS variables, new UI primitives (Button/Card/Label/RadioGroup), updated Tabs, refactored DecisionPanel/Reviewer modal/Editor pipeline for legibility and filtering

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
