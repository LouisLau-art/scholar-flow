---

description: "Task list for test coverage feature implementation"
---

# Tasks: 完善测试覆盖

**Input**: Design documents from `/specs/009-test-coverage/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are explicitly requested in the feature specification (spec.md). All tasks include test tasks following TDD approach.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`
- **Backend tests**: `backend/tests/` (pytest)
- **Frontend unit tests**: `frontend/tests/unit/` (Vitest)
- **Frontend E2E tests**: `frontend/tests/e2e/` (Playwright)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and test framework setup

- [X] T001 Create test directory structure (backend/tests/, frontend/tests/)
- [X] T002 [P] Install pytest and pytest-cov for backend testing
- [X] T003 [P] Install Playwright for frontend E2E testing
- [X] T004 [P] Install Vitest for frontend unit testing
- [X] T005 [P] Create pytest configuration (backend/pytest.ini)
- [X] T006 [P] Create pytest coverage configuration (backend/.coveragerc)
- [X] T007 [P] Create Playwright configuration (frontend/playwright.config.ts)
- [X] T008 [P] Create Vitest configuration (frontend/vitest.config.ts)
- [X] T009 [P] Create test helper utilities (backend/tests/conftest.py)
- [X] T010 [P] Create test data factories (backend/tests/fixtures.py)

**Checkpoint**: Test framework ready - can start writing tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core test infrastructure that MUST be complete before user story tests

**⚠️ CRITICAL**: No user story test implementation can begin until this phase is complete

- [X] T011 Implement JWT token generation for tests (backend/tests/conftest.py)
- [X] T012 [P] Implement database connection fixture with cleanup (backend/tests/conftest.py)
- [X] T013 [P] Create test data cleanup strategy (backend/tests/conftest.py)
- [X] T014 [P] Install PyJWT library for token generation (backend/requirements.txt)
- [X] T015 [P] Create test environment variables template (.env.test.example)
- [X] T016 [P] Install httpx for API testing (backend/requirements.txt)
- [X] T017 [P] Create test utilities for API client (backend/tests/utils/api_client.py)
- [X] T018 [P] Install Playwright browsers (npx playwright install)
- [X] T019 [P] Create test data cleanup script (scripts/cleanup-test-data.sh)

**Checkpoint**: Foundation ready - user story test implementation can now begin

---

## Phase 3: User Story 1 - 增加后端测试场景 (Priority: P1) 🎯 MVP

**Goal**: Add 13+ backend tests covering authentication, error handling, boundary conditions, and concurrent requests to reach 30+ total tests

**Independent Test**: Run `pytest` to verify all new tests pass independently

### Tests for User Story 1 (REQUIRED - explicitly requested in spec)

**Security & Authentication Tests** (Principle XIII):
- [X] T020 [P] [US1] Create test for missing JWT token (backend/tests/integration/test_auth_missing_token.py)
- [X] T021 [P] [US1] Create test for expired JWT token (backend/tests/integration/test_auth_expired_token.py)
- [X] T022 [P] [US1] Create test for invalid JWT token (backend/tests/integration/test_auth_invalid_token.py)
- [X] T023 [P] [US1] Create test for cross-user data access (backend/tests/integration/test_auth_cross_user.py)

**API Development Tests** (Principle XIV):
- [X] T024 [P] [US1] Create test for all HTTP methods on manuscripts endpoint (backend/tests/integration/test_manuscripts_http_methods.py)
- [X] T025 [P] [US1] Create test for all HTTP methods on editor endpoint (backend/tests/integration/test_editor_http_methods.py)
- [X] T026 [P] [US1] Create test for API path consistency (backend/tests/contract/test_api_paths.py)

**Error Scenario Tests** (Principle XII):
- [X] T027 [P] [US1] Create test for 404 error handling (backend/tests/integration/test_error_handling.py)
- [X] T028 [P] [US1] Create test for 500 error handling (backend/tests/integration/test_error_handling.py)
- [X] T029 [P] [US1] Create test for validation error responses (backend/tests/integration/test_validation_errors.py)

**Boundary Condition Tests** (Principle XII):
- [X] T030 [P] [US1] Create test for title min/max length validation (backend/tests/integration/test_boundary_title.py)
- [X] T031 [P] [US1] Create test for abstract min/max length validation (backend/tests/integration/test_boundary_abstract.py)
- [X] T032 [P] [US1] Create test for empty/null field validation (backend/tests/integration/test_boundary_empty_fields.py)
- [X] T033 [P] [US1] Create test for special character handling (backend/tests/integration/test_boundary_special_chars.py)

**Concurrent Request Tests** (Principle XII):
- [X] T034 [P] [US1] Create test for concurrent manuscript submissions (backend/tests/integration/test_concurrent_submissions.py)
- [X] T035 [P] [US1] Create test for concurrent editor assignments (backend/tests/integration/test_concurrent_assignments.py)
- [X] T036 [P] [US1] Create test for data consistency under concurrent load (backend/tests/integration/test_concurrent_consistency.py)

**Integration Tests** (Principle XII):
- [X] T037 [P] [US1] Create test for manuscript creation with real database (backend/tests/integration/test_manuscript_creation.py)
- [X] T038 [P] [US1] Create test for manuscript retrieval with real database (backend/tests/integration/test_manuscript_retrieval.py)
- [X] T039 [P] [US1] Create test for manuscript update with real database (backend/tests/integration/test_manuscript_update.py)
- [X] T040 [P] [US1] Create test for manuscript deletion with real database (backend/tests/integration/test_manuscript_deletion.py)

**Checkpoint**: All backend tests written and ready for implementation

### Implementation for User Story 1

**Security & Authentication Implementation** (Principle XIII):
- [ ] T041 [P] [US1] Add authentication middleware to protect manuscripts endpoints (backend/src/api/v1/manuscripts.py)
- [ ] T042 [P] [US1] Add authentication middleware to protect editor endpoints (backend/src/api/v1/editor.py)
- [ ] T043 [P] [US1] Implement JWT token validation in middleware (backend/src/middleware/auth.py)
- [ ] T044 [P] [US1] Implement RBAC for author role (backend/src/middleware/auth.py)
- [ ] T045 [P] [US1] Implement RBAC for editor role (backend/src/middleware/auth.py)

**API Development Implementation** (Principle XIV):
- [ ] T046 [P] [US1] Add unified error handling middleware (backend/src/middleware/error_handler.py)
- [ ] T047 [P] [US1] Add detailed logging for authentication operations (backend/src/middleware/auth.py)
- [ ] T048 [P] [US1] Add detailed logging for manuscript operations (backend/src/api/v1/manuscripts.py)

**Data Validation Implementation** (Principle XIV):
- [ ] T049 [P] [US1] Add Pydantic v2 validation for manuscript creation (backend/src/models/schemas.py)
- [ ] T050 [P] [US1] Add Pydantic v2 validation for manuscript update (backend/src/models/schemas.py)
- [ ] T051 [P] [US1] Add field constraints (min/max length) for title (backend/src/models/schemas.py)
- [ ] T052 [P] [US1] Add field constraints (min/max length) for abstract (backend/src/models/schemas.py)

**Checkpoint**: User Story 1 backend tests and implementation complete

---

## Phase 4: User Story 2 - 添加前端E2E测试 (Priority: P2)

**Goal**: Add 5+ E2E tests using Playwright to verify frontend user workflows

**Independent Test**: Run `npm run test:e2e` to verify all E2E tests pass independently

### Tests for User Story 2 (REQUIRED - explicitly requested in spec)

**E2E Tests with Playwright** (Principle XII):
- [X] T053 [P] [US2] Create Page Object Model for login page (frontend/tests/e2e/pages/login.page.ts)
- [X] T054 [P] [US2] Create Page Object Model for submission page (frontend/tests/e2e/pages/submission.page.ts)
- [X] T055 [P] [US2] Create Page Object Model for dashboard page (frontend/tests/e2e/pages/dashboard.page.ts)
- [X] T056 [P] [US2] Create Page Object Model for editor page (frontend/tests/e2e/pages/editor.page.ts)
- [X] T057 [P] [US2] Create test for unauthenticated user access restriction (frontend/tests/e2e/specs/authentication.spec.ts)
- [X] T058 [P] [US2] Create test for PDF upload and submission (frontend/tests/e2e/specs/submission.spec.ts)
- [X] T059 [P] [US2] Create test for empty form validation (frontend/tests/e2e/specs/submission.spec.ts)
- [X] T060 [P] [US2] Create test for editor dashboard pending manuscripts list (frontend/tests/e2e/specs/editor.spec.ts)
- [X] T061 [P] [US2] Create test for editor reviewer assignment (frontend/tests/e2e/specs/editor.spec.ts)

**Security & Authentication Tests** (Principle XIII):
- [X] T062 [P] [US2] Create E2E test for login prompt when unauthenticated (frontend/tests/e2e/specs/authentication.spec.ts)
- [X] T063 [P] [US2] Create E2E test for session persistence (frontend/tests/e2e/specs/authentication.spec.ts)

**API Development Tests** (Principle XIV):
- [X] T064 [P] [US2] Create E2E test for API path consistency (frontend/tests/e2e/specs/api_paths.spec.ts)
- [X] T065 [P] [US2] Create E2E test for error message display (frontend/tests/e2e/specs/error_handling.spec.ts)

**Test Coverage Tests** (Principle XII):
- [X] T066 [P] [US2] Create E2E test for all user roles (author, editor) (frontend/tests/e2e/specs/roles.spec.ts)
- [X] T067 [P] [US2] Create E2E test for browser compatibility (Chrome, Firefox, Safari) (frontend/tests/e2e/specs/browser_compat.spec.ts)

**Checkpoint**: All E2E tests written and ready for implementation

### Implementation for User Story 2

**Frontend E2E Implementation** (Principle XII):
- [ ] T068 [P] [US2] Implement login page interactions in Page Object (frontend/tests/e2e/pages/login.page.ts)
- [ ] T069 [P] [US2] Implement submission page interactions in Page Object (frontend/tests/e2e/pages/submission.page.ts)
- [ ] T070 [P] [US2] Implement dashboard page interactions in Page Object (frontend/tests/e2e/pages/dashboard.page.ts)
- [ ] T071 [P] [US2] Implement editor page interactions in Page Object (frontend/tests/e2e/pages/editor.page.ts)
- [ ] T072 [P] [US2] Add data-testid attributes to frontend components for E2E testing (frontend/src/components/SubmissionForm.tsx)
- [ ] T073 [P] [US2] Add data-testid attributes to editor dashboard components (frontend/src/components/EditorDashboard.tsx)
- [ ] T074 [P] [US2] Add data-testid attributes to login components (frontend/src/components/LoginForm.tsx)

**Security & Authentication Implementation** (Principle XIII):
- [ ] T075 [P] [US2] Ensure frontend properly handles JWT token storage (frontend/src/services/auth.ts)
- [ ] T076 [P] [US2] Add login prompt UI for unauthenticated users (frontend/src/components/LoginPrompt.tsx)
- [ ] T077 [P] [US2] Add session persistence logic (frontend/src/services/auth.ts)

**API Development Implementation** (Principle XIV):
- [ ] T078 [P] [US2] Add error message display component (frontend/src/components/ErrorMessage.tsx)
- [ ] T079 [P] [US2] Add toast notification for success/error feedback (frontend/src/components/Toast.tsx)

**Checkpoint**: User Story 2 E2E tests and implementation complete

---

## Phase 5: User Story 3 - 生成测试覆盖率报告 (Priority: P3)

**Goal**: Generate coverage reports for backend (>80%) and frontend (>70%)

**Independent Test**: Run coverage tools to verify report generation and thresholds

### Tests for User Story 3 (REQUIRED - explicitly requested in spec)

**Coverage Report Tests** (Principle XII):
- [X] T080 [P] [US3] Create test for backend coverage report generation (backend/tests/integration/test_coverage_report.py)
- [X] T081 [P] [US3] Create test for frontend coverage report generation (frontend/tests/unit/coverage.test.ts)
- [X] T082 [P] [US3] Create test for coverage threshold validation (backend/tests/integration/test_coverage_threshold.py)
- [X] T083 [P] [US3] Create test for uncovered code path identification (backend/tests/integration/test_uncovered_paths.py)
- [X] T084 [P] [US3] Create test for key business logic 100% coverage (backend/tests/integration/test_critical_coverage.py)

**Test Coverage Tests** (Principle XII):
- [X] T085 [P] [US3] Create test for line coverage calculation (backend/tests/integration/test_line_coverage.py)
- [X] T086 [P] [US3] Create test for branch coverage calculation (backend/tests/integration/test_branch_coverage.py)
- [X] T087 [P] [US3] Create test for function coverage calculation (backend/tests/integration/test_function_coverage.py)

**Checkpoint**: All coverage tests written and ready for implementation

### Implementation for User Story 3

**Coverage Report Implementation** (Principle XII):
- [X] T088 [P] [US3] Configure pytest-cov with 80% threshold (backend/.coveragerc)
- [X] T089 [P] [US3] Configure Vitest coverage with 70% threshold (frontend/vitest.config.ts)
- [X] T090 [P] [US3] Create coverage report generation script (scripts/generate-coverage-report.sh)
- [X] T091 [P] [US3] Add coverage HTML report generation (backend/pytest.ini)
- [X] T092 [P] [US3] Add coverage XML report generation for CI (backend/pytest.ini)
- [X] T093 [P] [US3] Create coverage summary script (scripts/coverage-summary.sh)
- [X] T094 [P] [US3] Add uncovered file identification logic (scripts/identify-uncovered.sh)

**Test Implementation** (Principle XII):
- [X] T095 [P] [US3] Implement coverage report API endpoint (backend/src/api/v1/coverage.py)
- [X] T096 [P] [US3] Implement coverage threshold validation (backend/src/services/coverage_service.py)
- [X] T097 [P] [US3] Add coverage dashboard UI (frontend/src/components/CoverageDashboard.tsx)

**Checkpoint**: User Story 3 coverage reports and implementation complete

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T098 [P] Update test documentation in quickstart.md
- [ ] T099 [P] Add test badges to README.md
- [X] T100 [P] Create test execution summary script (scripts/run-all-tests.sh)
- [ ] T101 [P] Add test performance optimization (parallel execution)
- [ ] T102 [P] Security hardening - verify all sensitive operations have tests (Principle XIII)
- [ ] T103 [P] Test coverage review - ensure all scenarios covered (Principle XII)
- [ ] T104 [P] API documentation review - verify OpenAPI/Swagger is complete (Principle XIV)
- [ ] T105 [P] Run quickstart.md validation
- [ ] T106 [P] User experience review - verify all user flows are tested (Principle XV)
- [ ] T107 [P] Add CI/CD integration for automated testing (GitHub Actions)
- [ ] T108 [P] Create test failure notification system

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational completion
- **User Story 3 (Phase 5)**: Depends on Foundational completion
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent of US1/US2

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all authentication tests together:
Task: "Create test for missing JWT token"
Task: "Create test for expired JWT token"
Task: "Create test for invalid JWT token"
Task: "Create test for cross-user data access"

# Launch all boundary tests together:
Task: "Create test for title min/max length validation"
Task: "Create test for abstract min/max length validation"
Task: "Create test for empty/null field validation"
Task: "Create test for special character handling"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Backend tests)
   - Developer B: User Story 2 (E2E tests)
   - Developer C: User Story 3 (Coverage reports)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- **原子化原则**: 每个任务应保持极小粒度，单次实施严禁修改超过 5 个文件。
- **注释规范**: 实现代码必须包含核心逻辑的中文注释。
- **文档同步**: 任务完成后必须确认是否需要同步更新设计文档。
- **即时存档**: 每个任务（Issue）完成后，必须立即 `git push` 到 GitHub 以防意外。
- **环境准则 (Arch Linux)**:
  - 依赖安装优先顺序: `pacman` > `paru` (使用用户 `louis`) > `pip`/`pnpm`。
  - 包冲突处理: 优先保留系统包，可清理对应的 `npm`/`pip` 全局包。
  - Python 强制安装: 若 `pip` 被拒，使用 `--break-system-packages`。
  - Docker 任务需显式包含镜像源配置校验。
- **DoD 验收**:
  - 后端：接口必须在 Swagger (/docs) 显式定义且可点。
  - 前端：页面必须有从主页或导航栏的可达入口。
  - **QA**: 自动化测试（Backend/Frontend）必须 100% 通过。
  - **Security**: 所有敏感操作必须有身份验证（Principle XIII）
  - **API**: API 路径必须前后端一致，使用 OpenAPI 规范（Principle XIV）
  - **Test Coverage**: 必须测试所有 HTTP 方法、错误场景、身份验证（Principle XII）
- Stop at any checkpoint to validate story independently
