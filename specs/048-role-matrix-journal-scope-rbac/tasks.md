# Tasks: GAP-P1-05 Role Matrix + Journal-scope RBAC

**Input**: Design docs from `/root/scholar-flow/specs/048-role-matrix-journal-scope-rbac/`  
**Prerequisites**: `spec.md`, `plan.md`

**Tests**: 本特性为安全与权限收敛特性，必须补齐自动化测试（contract + backend integration/unit + frontend unit + mocked E2E）。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无依赖）
- **[Story]**: 对应用户故事（US1/US2/US3）

## Phase 1: Setup (Shared)

**Purpose**: 建立角色矩阵与期刊作用域实现脚手架。

- [x] T001 新增迁移 `supabase/migrations/20260210110000_create_journal_role_scopes.sql`（`journal_role_scopes` 表 + 唯一索引 + 基础约束）
- [x] T002 新增 `backend/app/core/role_matrix.py`（角色常量、动作常量、权限映射）
- [x] T003 [P] 新增 `backend/app/core/journal_scope.py`（scope 查询与 manuscript journal 校验 helper）
- [x] T004 [P] 在 `frontend/src/types/user.ts` 扩展角色定义（`managing_editor`/`assistant_editor`/`editor_in_chief`）
- [x] T005 [P] 新增 `frontend/src/types/rbac.ts`（capability + scope DTO）

---

## Phase 2: Foundational (Blocking)

**Purpose**: 统一权限判定入口，避免每个接口重复拼装逻辑。

- [x] T006 在 `backend/app/core/role_matrix.py` 增加 legacy `editor -> managing_editor` 兼容映射函数
- [x] T007 在 `backend/app/core/journal_scope.py` 增加 `ensure_manuscript_scope_access()`（admin bypass + 非 admin 严格 scope）
- [x] T008 [P] 在 `backend/app/services/editor_service.py` 增加按 `allowed_journal_ids` 的 process 列表过滤能力
- [ ] T009 [P] 在 `backend/app/services/decision_service.py` 抽离统一权限校验入口（角色 + scope）
- [x] T010 [P] 在 `backend/tests/contract/test_api_paths.py` 增加 scope 管理/高风险接口契约占位

**Checkpoint**: 具备统一权限底座后，再进入各用户故事实现。

---

## Phase 3: User Story 1 - 角色矩阵显式化 (Priority: P1) 🎯

**Goal**: 系统具备可执行的角色矩阵，前后端行为一致。

**Independent Test**: 不同角色访问 editor 关键页面与操作，按钮可见性和后端授权结果一致。

### Tests for US1

- [x] T011 [P] [US1] 新增 `backend/tests/unit/test_role_matrix_scope.py`（动作权限矩阵单测）
- [x] T012 [P] [US1] 在 `backend/tests/integration/test_rbac_journal_scope.py` 增加“角色允许/拒绝”接口测试
- [x] T013 [P] [US1] 新增 `frontend/tests/unit/rbac-visibility.test.tsx`（按钮显隐/禁用）

### Implementation for US1

- [x] T014 [US1] 在 `backend/app/api/v1/editor.py` 为 process/detail/decision/owner/invoice 接口接入权限底座（首批 scope 校验 + 兼容开关）
- [x] T015 [US1] 在 `backend/app/api/v1/admin/users.py` 新增 scope 管理接口（list/upsert/deactivate）
- [x] T016 [US1] 在 `frontend/src/services/editorApi.ts` 增加 capability/scope 读取封装
- [x] T017 [US1] 在 `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx` 按 capability 控制高风险按钮
- [ ] T018 [US1] 在 `frontend/src/components/DecisionPanel.tsx` 区分“first decision 建议”与“final decision 提交”动作入口

**Checkpoint**: 角色矩阵在 UI 与 API 侧均可观测。

---

## Phase 4: User Story 2 - Journal Scope 隔离 (Priority: P1)

**Goal**: 非 admin 角色默认只能访问其授权期刊数据。

**Independent Test**: 同角色跨刊读取/写入全部返回 403；admin 跨刊访问不受限。

### Tests for US2

- [x] T019 [P] [US2] 在 `backend/tests/integration/test_rbac_journal_scope.py` 增加“跨刊 process 列表裁剪”测试
- [x] T020 [P] [US2] 在 `backend/tests/integration/test_rbac_journal_scope.py` 增加“跨刊详情读取 403”测试
- [x] T021 [P] [US2] 在 `backend/tests/integration/test_rbac_journal_scope.py` 增加“跨刊 owner/APC 写入 403”测试
- [ ] T022 [P] [US2] 新增 `frontend/tests/e2e/specs/rbac-journal-scope.spec.ts`（跨刊按钮不可用 + 后端拒绝）

### Implementation for US2

- [x] T023 [US2] 在 `backend/app/services/editor_service.py` 的 `list_manuscripts_process()` 接入 scope 过滤
- [x] T024 [US2] 在 `backend/app/api/v1/editor.py` 的 `GET /editor/manuscripts/{id}` 接入 scope 校验
- [x] T025 [US2] 在 `backend/app/api/v1/editor.py` 的 `PUT /editor/manuscripts/{id}/invoice-info` 接入 scope + 最小权限
- [x] T026 [US2] 在 `backend/app/api/v1/editor.py` 的 `POST /editor/manuscripts/{id}/bind-owner` 接入 scope + 最小权限
- [x] T027 [US2] 在 `backend/app/api/v1/editor.py` 的 `POST /editor/invoices/confirm` 接入 scope + 最小权限
- [x] T028 [US2] 在 `frontend/src/app/(admin)/editor/process/page.tsx` 增加 scope 命中提示与空态文案

**Checkpoint**: 期刊隔离能力在关键读写链路可验证。

---

## Phase 5: User Story 3 - first/final decision + 高风险审计 (Priority: P1)

**Goal**: 决策语义显式化，final decision/APC/owner 全量审计。

**Independent Test**: first decision 不触发终态，final decision 才触发状态机；高风险操作审计字段完整。

### Tests for US3

- [ ] T029 [P] [US3] 在 `backend/tests/integration/test_rbac_journal_scope.py` 增加 first/final decision 语义测试
- [ ] T030 [P] [US3] 在 `backend/tests/integration/test_rbac_journal_scope.py` 增加 final decision 最小权限测试（ME/AE 拒绝，EIC/Admin 允许）
- [ ] T031 [P] [US3] 在 `backend/tests/integration/test_rbac_journal_scope.py` 增加 APC override 审计字段测试
- [ ] T032 [P] [US3] 在 `frontend/tests/unit/rbac-visibility.test.tsx` 增加 first/final decision 按钮状态测试

### Implementation for US3

- [ ] T033 [US3] 在 `backend/app/services/decision_service.py` 增加 `first_decision` 草稿事件记录（不触发状态流转）
- [ ] T034 [US3] 在 `backend/app/services/decision_service.py` 收紧 `final decision` 提交角色（`editor_in_chief/admin`）
- [ ] T035 [US3] 在 `backend/app/api/v1/editor.py` 的 legacy `/editor/decision` 对齐 same rule（保留兼容）
- [ ] T036 [US3] 在 `backend/app/api/v1/editor.py` 为 APC/owner/final decision 写入统一审计 payload（before/after/reason/source）
- [ ] T037 [US3] 在 `frontend/src/app/(admin)/editor/decision/[id]/page.tsx` 展示 first/final decision 语义提示
- [ ] T038 [US3] 在 `frontend/src/components/DecisionPanel.tsx` 提交参数增加 `decision_stage`（first/final）

**Checkpoint**: 决策语义与高风险审计闭环完成。

---

## Phase 6: Polish & Cross-cutting

- [ ] T039 [P] 回写 `docs/GAP_ANALYSIS_AND_ACTION_PLAN.md` 的 GAP-P1-05 子项状态与验收记录
- [ ] T040 [P] 更新 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md` 的“环境约定 + 近期快照”
- [x] T041 执行后端测试：`pytest -o addopts= backend/tests/integration/test_rbac_journal_scope.py backend/tests/unit/test_role_matrix_scope.py`
- [x] T042 执行前端测试：`bun run test:run frontend/tests/unit/rbac-visibility.test.tsx`
- [ ] T043 执行 mocked E2E：`bun run test:e2e frontend/tests/e2e/specs/rbac-journal-scope.spec.ts --project=chromium`

---

## Dependencies & Order

1. 先做 Phase 1-2（权限底座）。
2. 再做 US1（角色矩阵），随后 US2（scope 隔离）。
3. 最后做 US3（决策语义与高风险审计）。
4. Phase 6 收尾并更新主线文档。

## Parallel Opportunities

- Phase 1: T003/T004/T005 可并行。
- Phase 2: T008/T009/T010 可并行。
- US1 Tests: T011/T012/T013 可并行。
- US2 Tests: T019/T020/T021/T022 可并行。
- US3 Tests: T029/T030/T031/T032 可并行。
- Polish: T039/T040 可并行。
