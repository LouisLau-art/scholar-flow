# Feature Specification: GAP-P1-01 Finance Real Invoices Sync

**Feature Branch**: `046-finance-invoices-sync`  
**Created**: 2026-02-09  
**Status**: Draft  
**Input**: User description: "GAP-P1-01：Finance 页面接入真实 invoices（替换演示数据），支持 unpaid/paid/waived 筛选与对账导出，并与编辑端 Mark Paid 行为一致"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 真实账单列表替换演示数据 (Priority: P1)

作为内部运营/编辑人员，我希望 Finance 页面展示真实账单，而不是本地演示数据，这样我能基于真实收款状态做日常管理。

**Why this priority**: 当前页面为演示态，无法支撑真实财务流程，是该功能最核心的可用性缺口。

**Independent Test**: 在真实账单存在的前提下打开 Finance 页面，验证列表内容与账单源数据一致，刷新后结果稳定。

**Acceptance Scenarios**:

1. **Given** 系统已有多条不同状态的账单，**When** 内部人员进入 Finance 页面，**Then** 页面展示真实账单记录（而非固定演示条目）。
2. **Given** 某账单状态在其他页面被更新，**When** 用户刷新或重新进入 Finance 页面，**Then** 页面显示最新状态。
3. **Given** 用户无内部权限，**When** 访问 Finance 页面，**Then** 系统拒绝访问并给出一致的权限提示。

---

### User Story 2 - 账单状态筛选与对账导出 (Priority: P1)

作为内部运营/编辑人员，我希望按 `unpaid/paid/waived` 快速筛选账单并导出当前结果，用于对账、归档和沟通。

**Why this priority**: 真实列表若没有筛选和导出，仍无法形成可执行的财务协作闭环。

**Independent Test**: 在账单列表执行状态筛选并触发导出，验证导出文件与当前筛选结果一致且字段完整。

**Acceptance Scenarios**:

1. **Given** 页面已加载真实账单列表，**When** 用户切换到 `paid` 筛选，**Then** 列表仅展示已支付账单。
2. **Given** 用户选择任一状态筛选后点击导出，**When** 导出完成，**Then** 导出内容与当前筛选结果逐条一致。
3. **Given** 当前筛选结果为空，**When** 用户发起导出，**Then** 系统返回可识别的空结果导出并提示“当前无匹配账单”。

---

### User Story 3 - 与编辑端 Mark Paid 行为一致 (Priority: P2)

作为编辑负责人，我希望 Finance 页面与稿件详情页的支付确认结果完全一致，避免多入口状态不一致导致误判。

**Why this priority**: 财务状态不一致会直接影响发布门禁与人工判断，属于高风险数据一致性问题。

**Independent Test**: 在稿件详情页执行 Mark Paid，再进入 Finance 页面检查；反向在 Finance 页面变更后回看稿件详情，状态应一致。

**Acceptance Scenarios**:

1. **Given** 某账单初始为 `unpaid`，**When** 在编辑端执行 Mark Paid，**Then** Finance 页面同一账单同步显示为 `paid`。
2. **Given** 财务状态发生变更，**When** 用户在两个入口分别查看，**Then** 状态、更新时间与关键金额信息一致。
3. **Given** 同一账单被并发操作，**When** 后到请求提交，**Then** 系统给出冲突提示并避免静默覆盖。

### Edge Cases

- 账单关联稿件缺少标题或作者信息时，页面仍可展示并明确标记“信息缺失”，不阻断列表加载。
- 账单金额为 0（如减免）时，应按 `waived` 或等价状态正确归类，不应误判为 `paid`。
- 筛选条件快速切换时，页面应避免展示过期结果（例如先显示旧筛选再跳变）。
- 导出过程中若数据发生变化，应保证导出文件使用同一时点快照，避免半新半旧。
- 单次结果量较大时（如 1000+ 条），系统应保持可用并给出清晰的加载/导出进度反馈。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统 MUST 将 Finance 页面账单列表切换为真实账单数据源，移除固定演示数据依赖。
- **FR-002**: 系统 MUST 在 Finance 页面展示账单核心字段：账单标识、关联稿件、金额、支付状态、最近更新时间。
- **FR-003**: 系统 MUST 支持按账单状态筛选，至少包含 `unpaid`、`paid`、`waived`。
- **FR-004**: 系统 MUST 支持导出当前筛选结果，并保证导出结果与页面筛选一致。
- **FR-005**: 系统 MUST 在空筛选结果时提供可识别反馈，不得让用户误判为系统异常。
- **FR-006**: 系统 MUST 对 Finance 页面施加内部权限控制，仅允许授权内部角色访问。
- **FR-007**: 系统 MUST 保证 Finance 页面与编辑端支付确认结果一致，任一入口变更后可在另一入口看到相同状态。
- **FR-008**: 系统 MUST 对并发状态变更提供冲突处理，避免后写请求无提示覆盖先写结果。
- **FR-009**: 系统 MUST 记录支付状态相关关键操作（操作者、时间、前后状态）以支持审计追溯。
- **FR-010**: 系统 MUST 在导出失败时返回可操作提示（例如重试、缩小筛选范围），而非静默失败。

### Key Entities *(include if feature involves data)*

- **Invoice Record**: 账单主记录，包含金额、状态、关联稿件、更新时间等信息。
- **Invoice Status Snapshot**: 某一时刻的账单状态视图，用于页面展示与跨入口一致性校验。
- **Reconciliation Export Batch**: 一次导出动作对应的数据快照，包含筛选条件、记录集合、导出时间。
- **Payment Status Audit Entry**: 支付状态变更审计记录，包含操作者、变更前后状态、发生时间。

### Assumptions

- 账单状态标准继续使用 `unpaid`、`paid`、`waived`，并作为筛选与导出分类基础。
- Finance 页面面向内部角色使用，不对作者或外部审稿人开放。
- 现有编辑端支付确认流程继续保留，Finance 页面需要与其共享同一状态事实。

### Dependencies

- 依赖现有账单生成与支付确认链路提供稳定账单数据。
- 依赖现有内部权限体系判定 Finance 页面访问权限。
- 依赖现有审计能力或等价机制记录支付状态变更。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Finance 页面中 100% 的账单条目来自真实账单数据源，不再出现固定演示条目。
- **SC-002**: 在抽样验收中，筛选结果与源账单数据一致率达到 100%。
- **SC-003**: 导出文件与导出时页面筛选结果的一致率达到 100%（字段与记录条数均一致）。
- **SC-004**: 编辑端与 Finance 页面之间的支付状态一致性达到 100%（同一账单在两入口状态无分歧）。
- **SC-005**: 内部用户完成“筛选并导出对账数据”的操作用时在 2 分钟内（P95）。
