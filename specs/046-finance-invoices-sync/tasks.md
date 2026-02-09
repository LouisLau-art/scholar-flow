# Tasks: GAP-P1-01 Finance Real Invoices Sync

**Input**: Design documents from `/root/scholar-flow/specs/046-finance-invoices-sync/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.yaml, quickstart.md

**Tests**: 本特性包含测试任务。规格明确要求“列表真实性、筛选/导出一致性、跨入口状态一致与并发冲突可识别”，必须补齐后端与前端自动化测试。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All tasks include exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 为 Finance 真账单改造建立最小脚手架与迁移占位。

- [x] T001 新建索引迁移文件 `supabase/migrations/20260209xxxxxx_finance_invoices_indexes.sql`（`invoices.status/confirmed_at/created_at`）
- [x] T002 在 `backend/app/models/invoices.py` 增加 Finance 列表与导出所需响应模型（query/meta/row）
- [x] T003 [P] 在 `frontend/src/types/finance.ts` 新建 Finance 列表、筛选、导出、确认支付类型定义
- [x] T004 [P] 在 `frontend/src/components/finance/FinanceInvoicesTable.tsx` 创建组件骨架（表头、状态 badge、动作位）

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 所有用户故事共享的基础能力；未完成前不得进入 US1/US2/US3。

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T005 在 `backend/app/services/editor_service.py` 新增 Finance 查询核心方法骨架（分页、排序、状态归一化）
- [x] T006 [P] 在 `backend/app/services/editor_service.py` 新增 CSV 导出构建方法骨架（同筛选参数复用）
- [x] T007 [P] 在 `backend/app/api/v1/editor.py` 增加 Finance 路由 DTO（list/export query 参数与响应结构）
- [x] T008 [P] 在 `backend/tests/contract/test_api_paths.py` 增加 `/api/v1/editor/finance/invoices` 与 `/api/v1/editor/finance/invoices/export` 路径契约
- [x] T009 在 `frontend/src/services/editorApi.ts` 增加 `listFinanceInvoices`、`exportFinanceInvoices`、`confirmInvoicePaid`（扩展参数）方法签名
- [x] T010 [P] 在 `frontend/src/services/editorService.ts` 增加 Finance 页服务封装与错误映射
- [x] T011 [P] 在 `frontend/src/middleware.ts` 将 `/finance` 纳入受保护路由 matcher 与登录重定向链路
- [x] T012 在 `frontend/src/app/finance/page.tsx` 移除本地演示 state，改为 API 驱动的加载骨架与错误态
- [x] T013 在 `backend/app/api/v1/editor.py` 增加 Finance 相关统一错误码映射（401/403/409/422/500）

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - 真实账单列表替换演示数据 (Priority: P1) 🎯 MVP

**Goal**: Finance 页面展示真实账单并具备内部权限访问控制。

**Independent Test**: 准备多条真实账单后访问 `/finance`，验证列表来自后端真实数据且非内部角色被拒绝。

### Tests for User Story 1

- [x] T014 [P] [US1] 在 `backend/tests/unit/test_finance_invoice_mapping.py` 新增 `effective_status` 与缺失字段兜底映射单测
- [x] T015 [P] [US1] 在 `backend/tests/integration/test_finance_invoices_sync.py` 新增 Finance 列表接口成功场景测试（真实数据返回）
- [x] T016 [P] [US1] 在 `backend/tests/integration/test_finance_invoices_sync.py` 新增 Finance 列表权限测试（无 token 401、非内部 403）
- [x] T017 [P] [US1] 在 `frontend/src/tests/finance-dashboard.test.tsx` 新增 Finance 页面首屏加载与列表渲染单测
- [x] T018 [P] [US1] 在 `frontend/tests/e2e/specs/finance-invoices-sync.spec.ts` 新增“内部角色可见列表/非内部受限”E2E 场景

### Implementation for User Story 1

- [x] T019 [US1] 在 `backend/app/services/editor_service.py` 实现 Finance 列表查询（`invoices + manuscripts + user_profiles` 读模型映射）
- [x] T020 [US1] 在 `backend/app/services/editor_service.py` 实现 `effective_status` 推导与 `payment_gate_blocked` 字段
- [x] T021 [US1] 在 `backend/app/api/v1/editor.py` 实现 `GET /api/v1/editor/finance/invoices`（RBAC + 分页 meta）
- [x] T022 [US1] 在 `frontend/src/services/editorApi.ts` 实现 `listFinanceInvoices` 实际请求与响应解析
- [x] T023 [US1] 在 `frontend/src/components/finance/FinanceInvoicesTable.tsx` 实现真实行渲染（invoice id/title/amount/status/updated_at）
- [x] T024 [US1] 在 `frontend/src/app/finance/page.tsx` 接入列表请求、loading/error/empty 状态
- [x] T025 [US1] 在 `frontend/src/app/finance/page.tsx` 增加权限失败（403）一致提示与回退导航

**Checkpoint**: User Story 1 should be fully functional and independently testable.

---

## Phase 4: User Story 2 - 账单状态筛选与对账导出 (Priority: P1)

**Goal**: 支持 `unpaid/paid/waived` 筛选并导出当前筛选快照 CSV。

**Independent Test**: 在 Finance 页面切换状态筛选并导出，验证 CSV 字段/条数与当前筛选结果一致，空结果也能导出并提示。

### Tests for User Story 2

- [x] T026 [P] [US2] 在 `backend/tests/integration/test_finance_invoices_sync.py` 新增 `unpaid/paid/waived` 筛选正确性测试
- [x] T027 [P] [US2] 在 `backend/tests/integration/test_finance_invoices_sync.py` 新增导出接口 CSV 内容与筛选一致测试
- [x] T028 [P] [US2] 在 `backend/tests/integration/test_finance_invoices_sync.py` 新增空结果导出测试（表头 + `X-Export-Empty`）
- [x] T029 [P] [US2] 在 `frontend/src/tests/finance-dashboard.test.tsx` 新增筛选切换与列表联动单测
- [x] T030 [P] [US2] 在 `frontend/src/tests/services/editor-api-finance.test.ts` 新增导出请求参数与错误处理单测
- [x] T031 [P] [US2] 在 `frontend/tests/e2e/specs/finance-invoices-sync.spec.ts` 新增“筛选后导出”E2E 场景

### Implementation for User Story 2

- [x] T032 [US2] 在 `backend/app/services/editor_service.py` 完成 Finance 列表筛选/搜索/排序实现（`status/q/sort/page`）
- [x] T033 [US2] 在 `backend/app/services/editor_service.py` 实现 CSV 生成与导出快照时间戳（`snapshot_at`）
- [x] T034 [US2] 在 `backend/app/api/v1/editor.py` 实现 `GET /api/v1/editor/finance/invoices/export`（`text/csv` + 头信息）
- [x] T035 [US2] 在 `frontend/src/services/editorApi.ts` 实现 `exportFinanceInvoices` 下载流处理
- [x] T036 [US2] 在 `frontend/src/app/finance/page.tsx` 新增筛选控件（all/unpaid/paid/waived）与查询参数同步
- [x] T037 [US2] 在 `frontend/src/app/finance/page.tsx` 新增导出按钮与导出中状态文案（含失败提示）
- [x] T038 [US2] 在 `frontend/src/components/finance/FinanceInvoicesTable.tsx` 增加空结果视图与“当前无匹配账单”提示

**Checkpoint**: User Stories 1 and 2 should both work independently.

---

## Phase 5: User Story 3 - 与编辑端 Mark Paid 行为一致 (Priority: P2)

**Goal**: Finance 与 Editor Pipeline 共享确认支付事实源，支持并发冲突提示与审计留痕。

**Independent Test**: 在 Pipeline 执行 Mark Paid 后，Finance 刷新一致；Finance 执行确认支付时能处理并发冲突并写入审计。

### Tests for User Story 3

- [x] T039 [P] [US3] 在 `backend/tests/integration/test_finance_invoices_sync.py` 新增“Pipeline -> Finance 一致性”集成测试
- [x] T040 [P] [US3] 在 `backend/tests/integration/test_finance_invoices_sync.py` 新增并发确认支付冲突（409）测试
- [x] T041 [P] [US3] 在 `backend/tests/integration/test_finance_invoices_sync.py` 新增审计日志写入测试（`payload.action=finance_invoice_confirm_paid`）
- [x] T042 [P] [US3] 在 `frontend/src/tests/finance-dashboard.test.tsx` 新增 Finance Confirm 成功/冲突提示单测
- [x] T043 [P] [US3] 在 `frontend/tests/e2e/specs/finance-invoices-sync.spec.ts` 新增“Mark Paid 后跨入口一致”E2E 场景

### Implementation for User Story 3

- [x] T044 [US3] 在 `backend/app/api/v1/editor.py` 扩展 `POST /api/v1/editor/invoices/confirm` 请求体（`expected_status`、`source`）
- [x] T045 [US3] 在 `backend/app/api/v1/editor.py` 实现条件更新并发控制（状态不匹配返回 409）
- [x] T046 [US3] 在 `backend/app/api/v1/editor.py` 确认支付成功后写入 `status_transition_logs.payload` 财务审计记录
- [x] T047 [US3] 在 `frontend/src/services/editorApi.ts` 扩展 `confirmInvoicePaid` 入参（`expectedStatus`、`source`）
- [x] T048 [US3] 在 `frontend/src/app/finance/page.tsx` 接入 Confirm 动作（调用统一接口 + 刷新列表）
- [x] T049 [US3] 在 `frontend/src/components/EditorPipeline.tsx` 调整 Mark Paid 调用参数（`source=editor_pipeline`）确保双入口语义一致
- [x] T050 [US3] 在 `frontend/src/app/finance/page.tsx` 增加并发冲突提示与刷新策略（避免展示过期状态）

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 收尾验证、文档同步、发布前检查。

- [x] T051 [P] 按最终实现回写 `specs/046-finance-invoices-sync/contracts/api.yaml`（错误码、示例、字段约束）
- [x] T052 [P] 按最终命令与验收结果回写 `specs/046-finance-invoices-sync/quickstart.md`
- [x] T053 执行后端 Finance 相关测试并记录结果到 `specs/046-finance-invoices-sync/quickstart.md`
- [x] T054 执行前端 Vitest + Playwright（finance）并记录结果到 `specs/046-finance-invoices-sync/quickstart.md`
- [x] T055 更新 `docs/GAP_ANALYSIS_AND_ACTION_PLAN.md` 中 GAP-P1-01 的进度与下一步
- [x] T056 同步上下文快照到 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`（Feature 046 实施结果）

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies, can start immediately.
- **Phase 2 (Foundational)**: depends on Phase 1 and blocks all user stories.
- **Phase 3-5 (User Stories)**: all depend on Phase 2 completion.
- **Phase 6 (Polish)**: depends on completed user stories.

### User Story Dependencies

- **US1 (P1)**: can start after Foundational; delivers MVP value by replacing demo data with real invoices.
- **US2 (P1)**: can start after Foundational and builds on US1 list query outputs; recommends implementing after US1 API is stable.
- **US3 (P2)**: depends on US1/US2 Finance read model and confirm action wiring; requires stable Mark Paid call path.

### Within Each User Story

- 测试任务先于实现任务。
- 后端 service 先于 API 路由。
- API 完成后再接前端页面与交互。
- 每个故事完成后执行其独立验收标准。

### Parallel Opportunities

- Phase 1: T003/T004 can run in parallel.
- Phase 2: T006/T007/T008/T010/T011 can run in parallel.
- US1: T014/T015/T016/T017/T018 can run in parallel.
- US2: T026/T027/T028/T029/T030/T031 can run in parallel.
- US3: T039/T040/T041/T042/T043 can run in parallel.
- Phase 6: T051/T052 can run in parallel.

---

## Parallel Example: User Story 1

```bash
Task: "T014 [US1] effective_status mapping unit test in backend/tests/unit/test_finance_invoice_mapping.py"
Task: "T015 [US1] finance list integration test in backend/tests/integration/test_finance_invoices_sync.py"
Task: "T017 [US1] finance dashboard rendering test in frontend/src/tests/finance-dashboard.test.tsx"
```

## Parallel Example: User Story 2

```bash
Task: "T026 [US2] finance status filter integration test in backend/tests/integration/test_finance_invoices_sync.py"
Task: "T030 [US2] finance export service test in frontend/src/tests/services/editor-api-finance.test.ts"
Task: "T031 [US2] filter + export e2e in frontend/tests/e2e/specs/finance-invoices-sync.spec.ts"
```

## Parallel Example: User Story 3

```bash
Task: "T040 [US3] invoice confirm conflict integration test in backend/tests/integration/test_finance_invoices_sync.py"
Task: "T041 [US3] audit log integration test in backend/tests/integration/test_finance_invoices_sync.py"
Task: "T042 [US3] finance confirm conflict ui test in frontend/src/tests/finance-dashboard.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. 完成 Phase 1 和 Phase 2。
2. 完成 US1（真实账单列表 + 权限控制）。
3. 独立验收 US1 后即可演示“Finance 不再是演示页”。

### Incremental Delivery

1. 先交付 US1，建立真实数据读模型。
2. 再交付 US2，补齐筛选与导出对账闭环。
3. 最后交付 US3，打通跨入口一致性、并发冲突与审计追溯。

### Parallel Team Strategy

1. 开发者 A：后端 service/API 与迁移（T019-T021, T032-T034, T044-T046）。
2. 开发者 B：前端页面/组件与 API 封装（T022-T025, T035-T038, T047-T050）。
3. 开发者 C：测试与文档验收（T014-T018, T026-T031, T039-T043, T053-T054）。
