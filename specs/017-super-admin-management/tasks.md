# Tasks: 超级用户管理后台 (Super Admin User Management)

**Input**: Design documents from `/specs/017-super-admin-management/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume web app structure (backend/ + frontend/)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Verify backend and frontend directory structure exists
- [ ] T002 [P] Verify Supabase connection and service role key configuration in backend
- [ ] T003 [P] Verify frontend Shadcn UI components availability (Table, Dialog, Form, etc.)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Database Migration (Blocking)

- [X] T004 Create database migration file for role_change_logs table in backend/migrations/
- [X] T005 Create database migration file for account_creation_logs table in backend/migrations/
- [X] T006 Create database migration file for email_notification_logs table in backend/migrations/
- [X] T007 Apply database migrations to Supabase

### Backend Models (Blocking)

- [X] T008 [P] Create RoleChangeLog Pydantic model in backend/app/models/user_management.py
- [X] T009 [P] Create AccountCreationLog Pydantic model in backend/app/models/user_management.py
- [X] T010 [P] Create EmailNotificationLog Pydantic model in backend/app/models/user_management.py
- [X] T011 Create UserResponse, UserListResponse, Pagination models in backend/app/models/user_management.py
- [X] T012 Create request models (CreateUserRequest, UpdateRoleRequest, InviteReviewerRequest) in backend/app/models/user_management.py

### Backend Services (Blocking)

- [X] T013 Create UserManagementService base class in backend/app/services/user_management.py
- [X] T014 Implement Supabase client initialization with service role key in backend/app/services/user_management.py
- [X] T015 Implement audit logging helper functions in backend/app/services/user_management.py

### Backend API Structure (Blocking)

- [X] T016 Create admin users API router file in backend/app/api/v1/admin/users.py
- [X] T017 Register admin users router in backend/app/api/v1/__init__.py
- [X] T018 Create admin package __init__.py in backend/app/api/v1/admin/__init__.py

### Frontend Services (Blocking)

- [X] T019 Create admin user service in frontend/src/services/admin/userService.ts
- [X] T020 [P] Create TypeScript types for user management in frontend/src/types/user.ts

### Frontend Components Structure (Blocking)

- [X] T021 Create admin components directory in frontend/src/components/admin/
- [X] T022 Create admin pages directory in frontend/src/app/admin/users/

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 查看和管理用户列表 (Priority: P1) 🎯 MVP

**Goal**: 超级管理员可以查看所有注册用户，支持分页、搜索和筛选

**Independent Test**: 管理员登录后，可以在管理后台看到"用户管理"菜单，点击后显示所有注册用户的列表，并可以使用搜索框和筛选器查找特定用户。

### Tests for User Story 1 (Principle XII & XIII & XIV)

**Security & Authentication Tests** (Principle XIII):
- [X] T023 [P] [US1] Authentication test: GET /api/v1/admin/users requires valid JWT token in backend/tests/integration/test_admin_users.py
- [X] T024 [P] [US1] Authorization test: Non-admin users cannot access user list in backend/tests/integration/test_admin_users.py
- [X] T025 [P] [US1] Security test: Unauthenticated access returns 401 in backend/tests/integration/test_admin_users.py

**API Development Tests** (Principle XIV):
- [X] T026 [P] [US1] Path consistency test: Verify frontend/backend API paths match exactly in backend/tests/contract/test_user_contracts.py
- [X] T027 [P] [US1] Error handling test: Verify unified error responses for invalid pagination in backend/tests/integration/test_admin_users.py
- [X] T028 [P] [US1] Validation test: Verify pagination parameters (page, per_page, search, role) in backend/tests/integration/test_admin_users.py

**Test Coverage Tests** (Principle XII):
- [X] T029 [P] [US1] HTTP method test: Test GET /api/v1/admin/users with all query parameters in backend/tests/integration/test_admin_users.py
- [X] T030 [P] [US1] Integration test: Use REAL database connection to fetch users in backend/tests/integration/test_admin_users.py
- [X] T031 [P] [US1] Error scenario test: Test empty search results, invalid role filter in backend/tests/integration/test_admin_users.py

### Implementation for User Story 1

**Backend API Implementation**:
- [X] T032 [US1] Implement GET /api/v1/admin/users endpoint with pagination in backend/app/api/v1/admin/users.py
- [X] T033 [US1] Implement search and filter logic (email, name, role) in backend/app/services/user_management.py
- [X] T034 [US1] Implement pagination logic (offset, limit, total count) in backend/app/services/user_management.py
- [X] T035 [US1] Add authentication middleware to admin users endpoints in backend/app/api/v1/admin/users.py
- [X] T036 [US1] Implement admin role verification in backend/app/api/v1/admin/users.py

**Frontend API Service Implementation**:
- [X] T037 [US1] Implement getUsers() method in frontend/src/services/admin/userService.ts
- [X] T038 [US1] Add TypeScript types for UserListResponse in frontend/src/types/user.ts

**Frontend Components Implementation**:
- [X] T039 [P] [US1] Create UserTable component in frontend/src/components/admin/UserTable.tsx
- [X] T040 [P] [US1] Create UserFilters component in frontend/src/components/admin/UserFilters.tsx
- [X] T041 [US1] Create user list page in frontend/src/app/admin/users/page.tsx
- [X] T042 [US1] Add "用户管理" menu item to admin navigation in frontend/src/app/admin/layout.tsx

**Frontend Styling & UX**:
- [X] T043 [US1] Add empty state UI for "未找到匹配用户" in frontend/src/components/admin/UserTable.tsx
- [X] T044 [US1] Add loading state for user list in frontend/src/components/admin/UserTable.tsx
- [X] T045 [US1] Add error handling and toast notifications in frontend/src/app/admin/users/page.tsx

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - 修改用户角色 (Priority: P2)

**Goal**: 超级管理员可以修改用户角色，记录变更原因和审计日志

**Independent Test**: 管理员在用户详情页可以修改用户角色，系统会验证管理员权限并记录角色变更操作。

### Tests for User Story 2 (Principle XII & XIII & XIV)

**Security & Authentication Tests** (Principle XIII):
- [X] T046 [P] [US2] Authentication test: PUT /api/v1/admin/users/{id}/role requires valid JWT token in backend/tests/integration/test_admin_users.py
- [X] T047 [P] [US2] Authorization test: Non-admin users cannot modify roles in backend/tests/integration/test_admin_users.py
- [X] T048 [P] [US2] Security test: User cannot modify their own role in backend/tests/integration/test_admin_users.py

**API Development Tests** (Principle XIV):
- [X] T049 [P] [US2] Validation test: Verify reason field is required (min 10 chars) in backend/tests/integration/test_admin_users.py
- [X] T050 [P] [US2] Error handling test: Verify error when old_role == new_role in backend/tests/integration/test_admin_users.py
- [X] T051 [P] [US2] Error handling test: Verify error when modifying admin role in backend/tests/integration/test_admin_users.py

**Test Coverage Tests** (Principle XII):
- [X] T052 [P] [US2] HTTP method test: Test PUT /api/v1/admin/users/{id}/role in backend/tests/integration/test_admin_users.py
- [X] T053 [P] [US2] Integration test: Role change creates audit log in backend/tests/integration/test_admin_users.py
- [X] T054 [P] [US2] Error scenario test: Test invalid user ID, missing reason in backend/tests/integration/test_admin_users.py

### Implementation for User Story 2

**Backend API Implementation**:
- [X] T055 [US2] Implement GET /api/v1/admin/users/{user_id} endpoint in backend/src/api/v1/admin/users.py
- [X] T056 [US2] Implement PUT /api/v1/admin/users/{user_id}/role endpoint in backend/src/api/v1/admin/users.py
- [X] T057 [US2] Implement role change logic with validation in backend/src/services/user_management.py
- [X] T058 [US2] Implement audit log creation for role changes in backend/src/services/user_management.py
- [X] T059 [US2] Add validation: prevent self role modification in backend/src/services/user_management.py
- [X] T060 [US2] Add validation: prevent admin role modification in backend/src/services/user_management.py

**Backend API Extension**:
- [X] T061 [US2] Implement GET /api/v1/admin/users/{user_id}/role-changes endpoint in backend/src/api/v1/admin/users.py

**Frontend API Service Implementation**:
- [X] T062 [US2] Implement getUserDetail() method in frontend/src/services/admin/userService.ts
- [X] T063 [US2] Implement updateUserRole() method in frontend/src/services/admin/userService.ts
- [X] T064 [US2] Implement getRoleChanges() method in frontend/src/services/admin/userService.ts
- [X] T065 [US2] Add TypeScript types for role change in frontend/src/types/user.ts

**Frontend Components Implementation**:
- [X] T066 [P] [US2] Create UserRoleDialog component in frontend/src/components/admin/UserRoleDialog.tsx
- [X] T067 [US2] Create user detail page in frontend/src/app/admin/users/[id]/page.tsx
- [X] T068 [US2] Add "详情" button to UserTable component in frontend/src/components/admin/UserTable.tsx
- [X] T069 [US2] Add role change history display in user detail page in frontend/src/app/admin/users/[id]/page.tsx

**Frontend Styling & UX**:
- [X] T070 [US2] Add form validation for role change reason (min 10 chars) in frontend/src/components/admin/UserRoleDialog.tsx
- [X] T071 [US2] Add confirmation dialog for role change in frontend/src/components/admin/UserRoleDialog.tsx
- [X] T072 [US2] Add success/error toast notifications in frontend/src/components/admin/UserRoleDialog.tsx

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - 直接创建内部编辑账号 (Priority: P3)

**Goal**: 超级管理员可以直接创建已验证的内部编辑账号，系统自动发送账户开通通知

**Independent Test**: 管理员可以输入邮箱和姓名创建新的Editor账号，系统会自动发送账户通知邮件。

### Tests for User Story 3 (Principle XII & XIII & XIV)

**Security & Authentication Tests** (Principle XIII):
- [X] T073 [P] [US3] Authentication test: POST /api/v1/admin/users requires valid JWT token in backend/tests/integration/test_admin_users.py
- [X] T074 [P] [US3] Authorization test: Non-admin users cannot create users in backend/tests/integration/test_admin_users.py
- [X] T075 [P] [US3] Security test: Service role key is used securely in backend/tests/integration/test_admin_users.py

**API Development Tests** (Principle XIV):
- [X] T076 [P] [US3] Validation test: Verify email uniqueness check in backend/tests/integration/test_admin_users.py
- [X] T077 [P] [US3] Error handling test: Verify error when email already exists (409) in backend/tests/integration/test_admin_users.py
- [X] T078 [P] [US3] Validation test: Verify name field validation (1-100 chars) in backend/tests/integration/test_admin_users.py

**Test Coverage Tests** (Principle XII):
- [X] T079 [P] [US3] HTTP method test: Test POST /api/v1/admin/users in backend/tests/integration/test_admin_users.py
- [X] T080 [P] [US3] Integration test: User creation creates account creation log in backend/tests/integration/test_admin_users.py
- [X] T081 [P] [US3] Error scenario test: Test email send failure rollback in backend/tests/integration/test_admin_users.py

### Implementation for User Story 3

**Backend API Implementation**:
- [X] T082 [US3] Implement POST /api/v1/admin/users endpoint in backend/app/api/v1/admin/users.py
- [X] T083 [US3] Implement user creation with Supabase Admin API in backend/app/services/user_management.py
- [X] T084 [US3] Implement email uniqueness check in backend/app/services/user_management.py
- [X] T085 [US3] Implement account creation log in backend/app/services/user_management.py
- [X] T086 [US3] Integrate with email service for account notification in backend/app/services/user_management.py
- [X] T087 [US3] Add rollback logic for email send failure in backend/app/services/user_management.py

**Frontend API Service Implementation**:
- [X] T088 [US3] Implement createInternalEditor() method in frontend/src/services/admin/userService.ts
- [X] T089 [US3] Add TypeScript types for CreateUserRequest in frontend/src/types/user.ts

**Frontend Components Implementation**:
- [X] T090 [P] [US3] Create CreateUserForm component in frontend/src/components/admin/CreateUserForm.tsx
- [X] T091 [US3] Add "新增内部成员" button to user list page in frontend/src/app/admin/users/page.tsx
- [X] T092 [US3] Integrate CreateUserForm with user list page in frontend/src/app/admin/users/page.tsx

**Frontend Styling & UX**:
- [X] T093 [US3] Add form validation (email format, name length) in frontend/src/components/admin/CreateUserForm.tsx
- [X] T094 [US3] Add email uniqueness check on client side in frontend/src/components/admin/CreateUserForm.tsx
- [X] T095 [US3] Add success/error toast notifications in frontend/src/components/admin/CreateUserForm.tsx

**Checkpoint**: User Stories 1, 2, and 3 should now be independently functional

---

## Phase 6: User Story 4 - 审稿人临时账号创建 (Priority: P3)

**Goal**: 编辑在指派审稿人时，可以为不存在的邮箱创建临时审稿人账号并发送Magic Link邀请

**Independent Test**: 编辑在指派审稿人时输入新邮箱，系统提示创建临时账号，确认后系统创建Reviewer账号并发送邀请链接。

### Tests for User Story 4 (Principle XII & XIII & XIV)

**Security & Authentication Tests** (Principle XIII):
- [X] T096 [P] [US4] Authentication test: POST /api/v1/admin/users/invite-reviewer requires valid JWT token in backend/tests/integration/test_admin_users.py
- [X] T097 [P] [US4] Authorization test: Only editors and admins can invite reviewers in backend/tests/integration/test_admin_users.py
- [X] T098 [P] [US4] Security test: Magic Link is used for temporary accounts in backend/tests/integration/test_admin_users.py

**API Development Tests** (Principle XIV):
- [X] T099 [P] [US4] Validation test: Verify email format validation in backend/tests/integration/test_admin_users.py
- [X] T100 [P] [US4] Error handling test: Verify error when email already exists (409) in backend/tests/integration/test_admin_users.py
- [X] T101 [P] [US4] Validation test: Verify name field validation in backend/tests/integration/test_admin_users.py

**Test Coverage Tests** (Principle XII):
- [X] T102 [P] [US4] HTTP method test: Test POST /api/v1/admin/users/invite-reviewer in backend/tests/integration/test_admin_users.py
- [X] T103 [P] [US4] Integration test: Reviewer creation uses Magic Link in backend/tests/integration/test_admin_users.py
- [X] T104 [P] [US4] Error scenario test: Test concurrent invite requests in backend/tests/integration/test_admin_users.py

### Implementation for User Story 4

**Backend API Implementation**:
- [X] T105 [US4] Implement POST /api/v1/admin/users/invite-reviewer endpoint in backend/src/api/v1/admin/users.py
- [X] T106 [US4] Implement temporary reviewer creation with Magic Link in backend/src/services/user_management.py
- [X] T107 [US4] Implement editor/admin role permission check in backend/src/api/v1/admin/users.py
- [X] T108 [US4] Implement Magic Link generation for reviewer invitation in backend/src/services/user_management.py
- [X] T109 [US4] Integrate with email service for reviewer invitation in backend/src/services/user_management.py

**Frontend API Service Implementation**:
- [X] T110 [US4] Implement inviteReviewer() method in frontend/src/services/admin/userService.ts
- [X] T111 [US4] Add TypeScript types for InviteReviewerRequest in frontend/src/types/user.ts

**Frontend Components Implementation**:
- [X] T112 [P] [US4] Create InviteReviewerDialog component in frontend/src/components/admin/InviteReviewerDialog.tsx
- [X] T113 [US4] Integrate reviewer invitation in manuscript assignment flow (existing page)
- [X] T114 [US4] Add confirmation dialog for temporary account creation in frontend/src/components/admin/InviteReviewerDialog.tsx

**Frontend Styling & UX**:
- [X] T115 [US4] Add prompt: "用户不存在，是否创建临时审稿账号？" in frontend/src/components/admin/InviteReviewerDialog.tsx
- [X] T116 [US4] Add success/error toast notifications in frontend/src/components/admin/InviteReviewerDialog.tsx

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T117 [P] Update API documentation in backend/src/api/v1/admin/users.py
- [ ] T118 [P] Add error boundary for admin pages in frontend/src/app/admin/error.tsx
- [ ] T119 [P] Add loading skeleton for user table in frontend/src/components/admin/UserTable.tsx
- [ ] T120 [P] Add accessibility attributes (ARIA) to admin components
- [ ] T121 [P] Add unit tests for user management service in backend/tests/unit/test_user_management.py
- [ ] T122 [P] Add unit tests for user service in frontend/tests/unit/userService.spec.ts
- [ ] T123 [P] Add unit tests for UserTable component in frontend/tests/unit/UserTable.spec.ts
- [ ] T124 [P] Add unit tests for UserRoleDialog component in frontend/tests/unit/UserRoleDialog.spec.ts
- [ ] T125 [P] Add unit tests for CreateUserForm component in frontend/tests/unit/CreateUserForm.spec.ts
- [ ] T126 [P] Add E2E test for user management flow in frontend/tests/e2e/admin-users.spec.ts
- [ ] T127 [P] Add E2E test for role change flow in frontend/tests/e2e/admin-users.spec.ts
- [ ] T128 [P] Add E2E test for user creation flow in frontend/tests/e2e/admin-users.spec.ts
- [ ] T129 [P] Add E2E test for reviewer invitation flow in frontend/tests/e2e/admin-users.spec.ts
- [ ] T130 Security review: Verify all endpoints have proper authentication and authorization
- [ ] T131 Security review: Verify service role key is not exposed in frontend
- [ ] T132 Test coverage review: Ensure all scenarios covered (backend >80%, frontend >70%)
- [ ] T133 API documentation review: Verify OpenAPI/Swagger is complete
- [ ] T134 User experience review: Verify all user flows are complete
- [ ] T135 Run quickstart.md validation
- [ ] T136 Update AGENTS.md, CLAUDE.md, GEMINI.md with any new learnings

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P3)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Depends on US1 for navigation integration
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Depends on US1 for navigation integration
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Independent, integrates with existing manuscript assignment flow

### Within Each User Story

- Tests MUST be written and FAIL before implementation (if TDD approach)
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
# Launch all tests for User Story 1 together:
Task: "Authentication test: GET /api/v1/admin/users requires valid JWT token in backend/tests/integration/test_admin_users.py"
Task: "Authorization test: Non-admin users cannot access user list in backend/tests/integration/test_admin_users.py"
Task: "Security test: Unauthenticated access returns 401 in backend/tests/integration/test_admin_users.py"
Task: "Path consistency test: Verify frontend/backend API paths match exactly in backend/tests/contract/test_user_contracts.py"
Task: "Error handling test: Verify unified error responses for invalid pagination in backend/tests/integration/test_admin_users.py"
Task: "Validation test: Verify pagination parameters (page, per_page, search, role) in backend/tests/integration/test_admin_users.py"
Task: "HTTP method test: Test GET /api/v1/admin/users with all query parameters in backend/tests/integration/test_admin_users.py"
Task: "Integration test: Use REAL database connection to fetch users in backend/tests/integration/test_admin_users.py"
Task: "Error scenario test: Test empty search results, invalid role filter in backend/tests/integration/test_admin_users.py"

# Launch all components for User Story 1 together:
Task: "Create UserTable component in frontend/src/components/admin/UserTable.tsx"
Task: "Create UserFilters component in frontend/src/components/admin/UserFilters.tsx"
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
5. Add User Story 4 → Test independently → Deploy/Demo
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (P1)
   - Developer B: User Story 2 (P2)
   - Developer C: User Story 3 (P3)
   - Developer D: User Story 4 (P3)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- **原子化原则**: 每个任务应保持极小粒粒度，单次实施严禁修改超过 5 个文件。
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
  - **API**: API 路径必须前后端与其他一致，使用 OpenAPI 规范（Principle XIV）
  - **Test Coverage**: 必须测试所有 HTTP 方法、错误场景、身份验证（Principle XII）
- Stop at any checkpoint to validate story independently

---

## Summary

**Total Tasks**: 136

**Tasks per User Story**:
- User Story 1 (P1): 23 tasks (T023-T045)
- User Story 2 (P2): 27 tasks (T046-T072)
- User Story 3 (P3): 23 tasks (T073-T095)
- User Story 4 (P3): 21 tasks (T096-T116)

**Parallel Opportunities**:
- Phase 1: 2 parallel tasks
- Phase 2: 13 parallel tasks (models, services, structure)
- Each User Story: 3-9 parallel test tasks, 2-4 parallel component tasks
- Phase 7: 10 parallel tasks

**Independent Test Criteria**:
- **US1**: Admin can view user list with pagination, search, and filters
- **US2**: Admin can modify user roles with audit logging
- **US3**: Admin can create internal editor accounts with email notification
- **US4**: Editor can invite temporary reviewers with Magic
