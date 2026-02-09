# Research: GAP-P0-01 Pre-check Role Hardening

## Research Scope

围绕 044 的落地缺口，聚焦以下决策点：
- 预审轨迹是否需要新建表，还是复用现有审计日志。
- 预审状态流转如何与现有状态机门禁（拒稿限制）兼容。
- AE 技术质检接口如何表达“通过/修回”并满足必填校验。
- 如何保证“路由层 RBAC + 服务层归属校验”双保险。
- 前端应继续依赖 `pages/editor/*` 旧入口，还是并入现有 Process 主入口。
- E2E 如何从占位注释升级为可重复回归。

## Decisions

### 1. 审计模型复用 `status_transition_logs`，不新增 pre-check 专表

- **Decision**: 预审关键动作（分派/重分派/技术质检/学术初审）统一写入 `status_transition_logs`，并在 `payload` 中记录 pre-check 细节。
- **Rationale**:
  - 已有审计链路与查询入口（详情页 audit timeline）可直接复用。
  - 满足 FR-003/FR-008 对“操作者+时间戳+前后状态”的追踪要求。
  - 避免引入新表带来的迁移和维护成本。
- **Alternatives considered**:
  - 新建 `precheck_assignment_logs`：结构更专用，但会重复审计能力，MVP 成本过高。
  - 仅打印日志文件：无法在产品内可视化，也不利于查询和回归。

### 2. 状态门禁统一走 `EditorialService.update_status`，子阶段变更单独审计

- **Decision**:
  - 发生主状态变化（如 `pre_check -> under_review/decision/minor_revision`）必须通过 `EditorialService.update_status`。
  - 仅 `pre_check_status` 变化（如 `intake -> technical -> academic`）使用条件更新，并补写 audit log。
- **Rationale**:
  - 复用已有 `allowed_next` 规则，天然满足“预审中不可直接拒稿”约束。
  - 保持 pre-check 子阶段语义清晰，不污染主状态机。
- **Alternatives considered**:
  - 全部改为直接 SQL update：会绕过状态机校验，风险高。
  - 让前端控制状态规则：会导致多端漂移，不可审计。

### 3. AE 技术质检改为显式 decision 接口

- **Decision**: `POST /editor/manuscripts/{id}/submit-check` 增加请求体 `decision`（`pass`/`revision`）和 `comment`；`revision` 时 `comment` 必填。
- **Rationale**:
  - 对齐 FR-005（修回必填说明）。
  - 与当前 Quick Pre-check 的 decision 模型保持一致，降低心智负担。
- **Alternatives considered**:
  - 继续“无参提交默认通过”：无法表达修回，且不可审计。
  - 拆两个端点（pass/revision）：接口数量增加且重复逻辑高。

### 4. RBAC 采用“路由角色校验 + 服务归属校验”

- **Decision**:
  - 路由层继续用 `require_any_role(...)` 做角色门禁。
  - 服务层再验证稿件阶段与归属（尤其 AE 必须匹配 `assistant_editor_id`）。
- **Rationale**:
  - 防止“角色正确但稿件不归属”的越权操作。
  - 满足 FR-002/FR-004/FR-006 的细粒度限制。
- **Alternatives considered**:
  - 只做路由角色校验：无法约束 AE 操作他人稿件。
  - 仅靠前端隐藏按钮：不具备安全意义。

### 5. 前端以 `/editor/process` 与详情页为主入口，逐步淘汰旧 `pages/editor/*`

- **Decision**: 预审可视化与操作优先集成到现有 App Router 的 Process/Detail 体系；`frontend/src/pages/editor/*` 作为兼容遗留，后续迁移下线。
- **Rationale**:
  - Process 已是编辑团队统一入口，避免再维护平行入口。
  - 当前 `editorService.ts` 对 pre-check 仍是 stub，应改为调用 `EditorApi` 真接口。
- **Alternatives considered**:
  - 继续扩展旧 `pages/editor/*`：会加剧双路由和双数据源问题。
  - 新建独立 pre-check 页面簇：与现有工作台重复。

### 6. E2E 采用 mocked 可重复回归，覆盖 ME->AE->EIC 主路径

- **Decision**: 把 `frontend/tests/e2e/specs/precheck_workflow.spec.ts` 从注释骨架改成真实断言场景，沿用 mocked `/api/v1/*` 路由和 `x-scholarflow-e2e: 1` 机制。
- **Rationale**:
  - 回归稳定、执行快，适合 P0 迭代。
  - 可覆盖主要交互与状态显示逻辑，满足 FR-012。
- **Alternatives considered**:
  - 只依赖后端集成测试：无法发现前端流程回归。
  - 全真实端到端：环境依赖重、波动大，不利于快速迭代。

## Resolved Clarifications

- `assistant_editor_id` 与 `pre_check_status` 字段已存在（迁移 `20260206150000_add_precheck_fields.sql`），本轮可直接基于现有 schema 实施。
- 当前实现确有基础端点，但服务层缺少强校验、幂等和完整审计，需要在本特性补齐。
- 本轮不需要新增外部依赖或新部署组件，全部在现有栈内完成。
