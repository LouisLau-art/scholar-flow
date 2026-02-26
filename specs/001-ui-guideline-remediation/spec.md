# Feature Specification: UI Guideline Remediation

**Feature Branch**: `001-ui-guideline-remediation`  
**Created**: 2026-02-26  
**Status**: Draft  
**Input**: User description: "处理 problem.md 里面的问题，遵循 specify 开发范式"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 可访问表单与弹窗闭环 (Priority: P1)

作为作者、审稿人和编辑，我需要在登录、注册、搜索、审稿提交、管理筛选等关键页面中，通过键盘与读屏器顺畅完成输入和提交，且弹窗具备一致且可预测的可关闭行为。

**Why this priority**: 这是基础可用性与合规底线，若缺失会直接阻断一部分用户完成核心业务。

**Independent Test**: 仅实施本故事后，可独立通过“键盘-only + 读屏器”验证关键流程是否可完成，且用户可关闭弹窗并返回原上下文。

**Acceptance Scenarios**:

1. **Given** 用户进入任一关键表单页，**When** 逐项 Tab 到输入控件，**Then** 每个控件都能被读出明确标签而非仅 placeholder。
2. **Given** 用户打开任一业务弹窗，**When** 使用键盘关闭操作，**Then** 弹窗关闭且焦点返回触发入口，页面上下文不丢失。

---

### User Story 2 - 语义化交互与键盘可达导航 (Priority: P2)

作为门户和后台用户，我希望所有可点击元素都是真正可交互语义元素（链接或按钮），并可通过键盘访问，不出现“看起来可点但实际不可达”的伪交互。

**Why this priority**: 该问题会造成误导交互和无障碍失败，影响导航效率与信任。

**Independent Test**: 仅实施本故事后，可独立通过全页面 Tab 导航验证所有操作入口是否可聚焦、可触发、可到达目标。

**Acceptance Scenarios**:

1. **Given** 用户浏览导航、页脚和主题分类区域，**When** 使用键盘遍历交互元素，**Then** 所有可见操作项均可聚焦并具备明确行为。
2. **Given** 存在尚未开放的目标入口，**When** 用户触发该入口，**Then** 不会出现无意义跳转，系统提供清晰的不可用反馈或真实目标。

---

### User Story 3 - 文案与时间展示一致性 (Priority: P3)

作为全角色用户，我希望加载文案、反馈提示、时间展示风格在全站一致，避免混杂格式造成理解成本。

**Why this priority**: 不一致不会立即阻断流程，但会持续降低产品专业性和可读性。

**Independent Test**: 仅实施本故事后，可独立通过抽样页面检查文案和时间展示是否统一规范。

**Acceptance Scenarios**:

1. **Given** 用户查看加载/处理中提示，**When** 对比不同页面，**Then** 文案格式保持一致并符合统一标点规范。
2. **Given** 用户查看时间字段，**When** 在不同页面对比，**Then** 时间展示采用统一且本地化友好的格式策略。

### Edge Cases

- 当页面无结果、无数据、无权限时，交互状态仍需保持语义正确，且提示文案清晰。
- 当用户仅使用键盘且未使用鼠标时，所有关键流程必须可完整闭环。
- 当弹窗内容较长或视口较小（移动端）时，关闭路径和焦点行为仍需稳定。
- 当部分导航目标暂不可用时，不应出现空跳转、回顶或无反馈状态。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统 MUST 为关键业务表单中的所有可编辑字段提供可访问名称（显式标签或等价可访问文本）。
- **FR-002**: 系统 MUST 确保关键弹窗具备统一可关闭机制和可预测的焦点返回行为。
- **FR-003**: 系统 MUST 将所有面向用户的可点击操作实现为语义化可交互元素（链接或按钮），并支持键盘触发。
- **FR-004**: 系统 MUST 对伪交互项执行清零审计，禁止出现仅通过 `cursor` 样式暗示可点击但无真实行为的入口。
- **FR-005**: 系统 MUST 移除或替换无业务意义的占位导航入口，避免用户进入无效路径。
- **FR-006**: 系统 MUST 保证图标型操作具备清晰可访问名称。
- **FR-007**: 系统 MUST 在输入聚焦态提供可见焦点指示，确保键盘用户可感知当前位置。
- **FR-008**: 系统 MUST 统一全站加载/处理中短文案的标点与格式规范。
- **FR-009**: 系统 MUST 统一面向终端用户的日期时间展示策略，避免跨页面格式割裂。
- **FR-010**: 系统 MUST 在不改变既有业务权限规则的前提下完成以上 UI 规范修复。

### Key Entities *(include if feature involves data)*

- **UI Finding**: 来自 `problem.md` 的问题条目，属性包括严重级别、问题描述、定位、验收条件、处理状态。
- **Interaction Surface**: 用户可见交互面，包含页面、弹窗、表单、导航区与反馈区。
- **Accessibility Contract**: 每个交互面的可访问约束集合，包括标签、焦点、键盘行为、关闭机制与可读性要求。

### Assumptions

- 本次范围聚焦 `problem.md` 中前端 UI/可访问性/一致性问题，不包含后端业务逻辑改造。
- 已存在的权限策略与流程规则保持不变，本次仅做前端体验与可访问性修复。
- 验收以关键路径抽样与定向测试为主，不要求一次性覆盖所有历史页面。

### Key Path Surface List

- `/login`
- `/signup`
- `/search`
- `/review/[token]`
- `/review/assignment/[assignmentId]`
- 首页 Newsletter 区块（`/`）
- Header 搜索弹窗与 Mega Menu（`SiteHeader`）
- 管理员用户筛选（`UserFilters`）
- 审稿相关弹窗（`AcademicCheckModal`、`ReviewerAssignModal`、`ReviewerDashboard`）

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `problem.md` 中高优先级（High）UI 问题在本次范围内关闭率达到 100%。
- **SC-002**: 关键路径（登录、注册、站内搜索、审稿提交、管理员筛选）可通过键盘完成端到端操作，任务完成率达到 100%。
- **SC-003**: 抽样页面中的表单字段可访问名称覆盖率达到 100%（关键路径内）。
- **SC-004**: 抽样页面中的加载文案与时间展示格式一致性达到 100%（按本次定义的统一规则）。
