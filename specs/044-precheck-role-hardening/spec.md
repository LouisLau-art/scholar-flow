# Feature Specification: GAP-P0-01 Pre-check Workflow Closure

**Feature Branch**: `044-precheck-role-hardening`  
**Created**: 2026-02-09  
**Status**: Draft  
**Input**: User description: "GAP-P0-01 预审角色工作流落地补齐（ME→AE→EIC）"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 预审分派与角色流转闭环 (Priority: P1)

作为 Managing Editor（ME），我需要把稿件从 Intake 阶段分派给 Assistant Editor（AE），并确保后续只能由对应角色推进，这样才能保证预审链路责任清晰。

**Why this priority**: 这是预审链路能否稳定运行的起点，若分派和权限不严谨，后续所有决策都不可追责。

**Independent Test**: 准备一篇 `pre_check` 稿件，执行 “ME 分派 AE -> AE 技术质检（通过或修回）” 流程，验证角色限制、状态变化和时间戳均正确。

**Acceptance Scenarios**:

1. **Given** 稿件处于 Intake 阶段，**When** ME 指派 AE，**Then** 系统更新责任人并记录分派时间。
2. **Given** 非 ME 用户尝试分派 AE，**When** 提交分派操作，**Then** 系统拒绝并保持稿件状态不变。
3. **Given** 稿件已分派 AE，**When** AE 完成技术质检并给出结果，**Then** 系统按规则流转到下一预审阶段并写入审计记录。

---

### User Story 2 - 学术初审与决策入口规范化 (Priority: P1)

作为 Editor-in-Chief（EIC），我需要在 Academic 阶段完成学术初审，并把稿件送入外审或决策阶段，这样才能保证拒稿和放行都遵循统一状态机约束。

**Why this priority**: 这是预审终点和正式评审入口，若规则松散会导致错误拒稿或越级流转。

**Independent Test**: 准备一篇进入 Academic 阶段的稿件，执行 “EIC 初审 -> 送外审/进入决策” 两条路径，验证禁止路径和允许路径都符合规则。

**Acceptance Scenarios**:

1. **Given** 稿件处于 Academic 阶段，**When** EIC 选择进入外审，**Then** 稿件进入可外审状态并记录处理人/时间。
2. **Given** 稿件处于 Academic 阶段，**When** EIC 选择进入决策阶段，**Then** 稿件进入决策链路并保留预审轨迹。
3. **Given** 稿件仍在预审中，**When** 任意角色尝试直接拒稿，**Then** 系统拒绝该操作并提示需先进入决策阶段。

---

### User Story 3 - 过程可视化与验收可回归 (Priority: P2)

作为编辑团队负责人，我需要在 Process 列表和稿件详情中看到角色队列、责任人和关键时间戳，并有可重复的端到端验收流程，这样才能稳定上线和复盘。

**Why this priority**: 前两条故事解决“能运行”，该故事解决“可观测、可验收、可复盘”。

**Independent Test**: 通过一轮完整预审（ME->AE->EIC）后，核对列表与详情显示，并执行关键端到端回归，确认结果一致。

**Acceptance Scenarios**:

1. **Given** 稿件在预审各阶段流转过，**When** 团队查看流程列表与详情，**Then** 能看到当前阶段、当前责任人和完整时间线。
2. **Given** 团队执行标准回归场景，**When** 回归结束，**Then** 能得到通过/失败结论并定位失败环节。

### Edge Cases

- AE 被重新分派后，历史分派记录与时间戳必须保留，不能覆盖旧轨迹。
- AE 选择“修回”时若未填写说明，系统必须阻止提交。
- 稿件在 `pre_check` / `under_review` / `resubmitted` 阶段禁止直接进入拒稿终态。
- 同一稿件被重复提交同类操作时，系统应保持幂等结果，避免重复写入冲突轨迹。
- 稿件责任人变更与阶段变更并发发生时，最终状态必须一致且可审计。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统 MUST 将预审阶段显式划分为 Intake、Technical、Academic 三个子阶段。
- **FR-002**: 系统 MUST 仅允许 ME 执行 AE 分派与重分派操作。
- **FR-003**: 系统 MUST 在每次分派/重分派时记录操作者、目标责任人和时间戳。
- **FR-004**: 系统 MUST 仅允许被分派的 AE 执行 Technical 阶段处理。
- **FR-005**: 系统 MUST 要求 AE 在“修回”结论下提供必填说明。
- **FR-006**: 系统 MUST 仅允许 EIC 执行 Academic 阶段的学术初审决定。
- **FR-007**: 系统 MUST 限制拒稿路径：稿件在预审中不得直接拒稿，必须先进入决策阶段后再执行拒稿终态。
- **FR-008**: 系统 MUST 在每次阶段流转时保留前后状态、操作者、时间和备注，形成可审计链路。
- **FR-009**: 系统 MUST 在流程列表中展示预审子阶段、当前责任角色和关键处理时间。
- **FR-010**: 系统 MUST 在稿件详情中展示角色队列及分派/决策时间线。
- **FR-011**: 系统 MUST 保证同一稿件重复提交同类指令时结果可预测且不产生重复冲突记录。
- **FR-012**: 系统 MUST 提供覆盖 ME→AE→EIC 主路径的标准验收场景，并可重复执行。

### Key Entities *(include if feature involves data)*

- **Precheck Queue Item**: 表示稿件在预审中的当前阶段、当前责任角色与责任人。
- **Role Assignment Record**: 表示 ME 对 AE 的分派与重分派记录，包含操作者、目标用户和时间。
- **Precheck Decision Record**: 表示 AE 或 EIC 在各阶段给出的处理决定与说明。
- **Precheck Timeline Event**: 表示预审链路中每次关键状态变更与审计信息。

### Assumptions

- 编辑团队角色信息已存在并可用于权限判定。
- 稿件状态机主规则（尤其拒稿约束）继续沿用当前项目约定。
- Process 列表与详情页仍作为编辑团队的统一操作入口。

### Dependencies

- 依赖既有稿件状态机与角色权限体系。
- 依赖现有审计日志能力用于记录流转与分派轨迹。
- 依赖现有测试体系支持端到端回归场景执行。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% 处于预审中的稿件都能显示明确的预审子阶段与当前责任角色。
- **SC-002**: 100% 预审分派与阶段流转操作都可追溯到操作者和时间戳。
- **SC-003**: 预审阶段越权操作拦截率达到 100%（不允许角色越级推进）。
- **SC-004**: AE 的“修回”决定中说明字段完整率达到 100%。
- **SC-005**: 标准回归场景（ME 分派、AE 质检、EIC 初审）在发布前验收中连续两次通过。
