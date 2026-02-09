# Feature Specification: GAP-P1-05 Role Matrix + Journal-scope RBAC

**Feature Branch**: `048-role-matrix-journal-scope-rbac`  
**Created**: 2026-02-09  
**Status**: Draft  
**Input**: User description: "GAP-P1-05：角色矩阵与期刊作用域 RBAC 收敛，补齐 first decision/final decision 语义与 APC/Owner 高风险权限审计"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 角色矩阵显式化并落到系统行为 (Priority: P1)

作为管理编辑，我希望系统对不同内部角色（ME/AE/EIC/Admin）的页面、按钮、操作权限有明确且一致的约束，避免“同入口不同人行为不一致”。

**Why this priority**: 当前角色虽可用，但权限边界分散在多个页面与接口中，存在灰区与隐性越权风险。

**Independent Test**: 使用不同角色账号访问 `/editor/process`、`/editor/manuscript/[id]`、`/editor/decision/[id]`，验证按钮显示与接口授权一致。

**Acceptance Scenarios**:

1. **Given** 用户为 `assistant_editor`，**When** 访问决策工作台，**Then** 只能查看其职责范围信息，不能提交最终决策。
2. **Given** 用户为 `managing_editor`，**When** 访问稿件详情，**Then** 可处理 owner/APC 相关准备操作，但不能执行 final accept/reject。
3. **Given** 用户为 `editor_in_chief`，**When** 决策阶段完成评估，**Then** 可以提交 final decision 并触发状态流转与审计。

---

### User Story 2 - 同角色跨期刊默认隔离（Journal Scope）(Priority: P1)

作为多刊运营管理员，我希望同一角色默认只能操作其授权期刊的数据，防止跨期刊误读/误改。

**Why this priority**: 这是对方需求中的关键治理能力，属于高优先级安全与合规要求。

**Independent Test**: 准备 A/B 两个期刊与同角色账号，仅授予 A 期刊 scope；验证其读取/写入 B 期刊数据全部被拒绝。

**Acceptance Scenarios**:

1. **Given** `managing_editor` 仅绑定 Journal A，**When** 查询 process 列表，**Then** 只返回 Journal A 稿件。
2. **Given** 同一用户尝试对 Journal B 稿件执行 owner 绑定或 invoice 更新，**When** 请求到达后端，**Then** 返回 403。
3. **Given** `admin` 用户，**When** 访问任意期刊稿件，**Then** 保持全局可访问（平台级运维例外）。

---

### User Story 3 - first/final decision 语义与高风险操作审计 (Priority: P1)

作为主编，我希望 first decision 与 final decision 在产品和审计上明确区分，并且 APC/Owner/final decision 这类高风险操作都有最小权限和可追溯记录。

**Why this priority**: 决策语义不清和审计缺失会直接影响出版责任边界与财务风险控制。

**Independent Test**: 依次执行 first decision（建议）、final decision（生效）与 APC override，检查状态、权限、审计字段是否符合预期。

**Acceptance Scenarios**:

1. **Given** 处于 decision 阶段，**When** `managing_editor` 保存 first decision 建议，**Then** 系统记录建议事件但不触发终态流转。
2. **Given** 已有 first decision 建议，**When** `editor_in_chief` 提交 final decision，**Then** 系统执行真实状态流转并通知作者。
3. **Given** APC 金额被改写（override），**When** 操作成功，**Then** 审计日志必须包含 `before/after/reason/operator/source`。

### Edge Cases

- 旧账号仅有 `editor` 角色但无细分角色时，应按兼容策略映射（例如映射到 `managing_editor`），并在日志中标记 legacy role。
- 稿件 `journal_id` 为空时，默认按“拒绝敏感写操作”处理，避免落入跨刊越权灰区。
- 用户具备角色但未绑定任何 journal scope 时，除 admin 外默认拒绝敏感读写（403）。
- 并发写入高风险字段（如 APC）时，后写请求需显式冲突提示，不得静默覆盖。
- first decision 重复提交需幂等处理（可覆盖草稿，但不能制造重复“生效决策”记录）。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统 MUST 定义并集中维护角色矩阵（角色 -> 页面可见 -> 操作权限 -> 状态流转权限）。
- **FR-002**: 系统 MUST 对编辑域关键接口执行“双重校验”：角色校验 + journal scope 校验。
- **FR-003**: 系统 MUST 对 `admin` 提供平台级全局访问豁免；非 admin 按 journal scope 严格隔离。
- **FR-004**: 系统 MUST 为 `editor` 旧角色提供兼容映射策略，并在响应或审计中可识别该兼容路径。
- **FR-005**: 系统 MUST 显式区分 `first decision`（建议，不生效）与 `final decision`（生效，触发状态机）。
- **FR-006**: 系统 MUST 将 `final decision` 归为高风险操作，仅允许 `editor_in_chief/admin`（且通过 scope）执行。
- **FR-007**: 系统 MUST 将 `owner` 绑定与 `APC` 关键变更归为高风险操作，限制最小权限并写入审计日志。
- **FR-008**: 系统 MUST 在 Process 列表和详情读取场景中按 journal scope 自动裁剪可见数据。
- **FR-009**: 系统 MUST 在前端对无权限按钮进行隐藏/禁用，并在后端保持最终强校验（前后端一致）。
- **FR-010**: 系统 MUST 补齐关键 RBAC 回归测试：401、403、跨刊越权读、跨刊越权写、并发冲突。

### Key Entities *(include if feature involves data)*

- **Role Matrix Entry**: 角色与能力映射项（页面、动作、状态流转、字段可编辑权限）。
- **Journal Scope Binding**: 用户与期刊的授权关系（user_id, journal_id, role, active）。
- **Decision Event**: 决策事件记录，区分 `first_decision` 与 `final_decision`。
- **High-risk Audit Record**: 高风险操作审计（owner/APC/final decision）包含 before/after/reason/operator/source。

### Assumptions

- 保持现有 `user_profiles.roles` 作为角色来源，不引入外部 IAM。
- `journals` 与 `manuscripts.journal_id` 已可用；新增 journal scope 关系表后由后端应用层强制执行。
- 现有 `status_transition_logs` 继续作为主要审计落点，必要时扩展 payload 字段。

### Dependencies

- 依赖 `supabase/migrations` 新增 journal scope 关系表。
- 依赖现有 editor/decision/finance/owner 相关 API 路由进行权限收敛。
- 依赖前端 Process/Manuscript/Decision 页面进行角色与 scope UX 对齐。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 关键编辑接口（process/detail/decision/invoice/owner）RBAC + scope 回归测试通过率 100%。
- **SC-002**: 跨期刊越权读取/写入场景全部返回 403（无漏网）。
- **SC-003**: final decision、owner 绑定、APC override 三类高风险操作审计覆盖率 100%。
- **SC-004**: first decision 与 final decision 在 UI 文案、接口语义、审计记录三层保持一致。
- **SC-005**: legacy `editor` 账号在兼容策略下不阻断现有流程，且可观测到兼容命中日志。

## OJS/Janeway 对标映射

- **Role Matrix**：借鉴 OJS context role 与 Janeway editorial hierarchy，明确 `ME/AE/EIC/Admin` 在“读/写/决策”三层权限边界。
- **Journal Scope 隔离**：对齐多刊系统“同角色跨刊默认隔离”的治理原则，非 admin 一律受 journal binding 裁剪。
- **Decision 语义分层**：借鉴 OJS 的建议决策与最终决策分离模式，保留 `first decision` 讨论态与 `final decision` 生效态的审计差异。
