# Feature Specification: Final Decision Workspace (沉浸式决策工作间)

**Feature Branch**: `041-final-decision-workspace`  
**Created**: 2026-02-06  
**Status**: Draft  
**Context**: 针对外审结束后的主编决策环节，从现有侧边栏升级为沉浸式、多维参考的决策工作台。

## Clarifications

### Session 2026-02-06
- Q: 决策信存储方式？ → A: 采用独立实体存储，在数据库中新增 `decision_letters` 表。
- Q: 是否支持决策草稿？ → A: 全面支持，`decision_letters` 增加 `status` (draft/final) 字段并提供保存草稿按钮。
- Q: 并发编辑处理？ → A: 采用乐观锁机制，提交时校验 `updated_at`，若已被他人修改则提示冲突。
- Q: 是否支持决策附件？ → A: 支持，使用 Supabase Storage `decision-attachments` 桶保存。
- Q: 作者可见性？ → A: 仅在点击“Submit Final Decision”后作者可见，草稿对作者不可见。
- Q: 决策编辑器类型？ → A: MVP 统一为结构化文本（Markdown）编辑器，不引入富文本 HTML。
- Q: 谁可以做最终决策？ → A: `editor_in_chief`、该稿件 `assigned_editor`，以及用于应急的 `admin`。
- Q: 拒稿阶段约束？ → A: 拒稿只能在 `decision` / `decision_done` 阶段执行，禁止 `under_review` / `resubmitted` 直接拒稿。

---

## 1. 用户场景 (User Stories)

### US1 - 沉浸式查阅审稿意见 (Priority: P1)
**角色**: Editor-in-Chief (EIC) / Assigned Editor / Admin(应急)  
**目标**: 在一个界面内查看审稿材料并完成决策。  
**验收标准**:
1. 点击“Make Final Decision”后进入全屏沉浸式界面（无全站导航）。
2. 支持并排或垂直列表展示所有已提交审稿报告（含打分、对作者意见、内部意见）。
3. 界面内可直接预览稿件 PDF。
4. 仅展示 `submitted` 状态的审稿报告。

### US2 - 智能生成决策信草稿 (Priority: P1)
**角色**: Editor  
**目标**: 自动汇聚审稿人意见，减少手动复制粘贴。  
**验收标准**:
1. 提供“Generate Letter Draft”按钮。
2. 系统自动提取各审稿人的“对作者意见”，按统一模板填入编辑器（Reviewer 1/2/...）。
3. 编辑可继续修改并保存草稿，二次进入页面可恢复草稿内容。

### US3 - 强制流程约束与审计 (Priority: P1)
**角色**: 系统  
**目标**: 拒稿流程符合状态机约束，并保留完整决策依据。  
**验收标准**:
1. 仅当稿件有至少 1 份 `submitted` 报告时，决策入口才可用。
2. `under_review` / `resubmitted` 阶段不允许直接 `Reject -> rejected`；拒稿只能在 `decision` / `decision_done` 阶段提交。
3. `Accept/Reject/Revision` 必须关联“给作者的信”；`status='final'` 才能对作者可见。
4. 决策动作必须在 `status_transition_logs` 中记录 payload（含决策信、附件、操作者）。

---

## 2. 功能需求 (Functional Requirements)

### FR-001: 决策上下文聚合接口
- 系统必须提供后端接口，一次性返回：
  - 稿件基础信息与 PDF 预览地址（signed URL 或等效安全地址）。
  - 所有 `submitted` 审稿报告及其附件。
  - AE（副主编）的预审建议（如有）。
  - 当前编辑人的最近草稿（如有）与模板内容。

### FR-002: 三栏式工作空间 UI
- 左侧：稿件 PDF 阅读器。
- 中间：审稿报告对比区（支持折叠/展开）。
- 右侧：决策操作区（结论选择 + 决策信编辑器 + 附件管理）。

### FR-003: 决策信编辑器（MVP）
- MVP 必须使用 Markdown 结构化文本编辑器。
- 必须支持一键导入审稿人意见。
- 必须提供显式的“Save Draft”和“Submit Final Decision”按钮。

### FR-004: 状态机强制流转与阶段校验
- `Accept -> approved`
- `Reject -> rejected`
- `Major/Minor Revision -> revision_requested`
- 后端必须校验 workflow stage：
  - `Reject` 仅允许在 `decision` 或 `decision_done`。
  - 禁止 `under_review`、`resubmitted` 直接进入 `rejected`。
- 必须校验当前稿件状态与版本，防止并发下误流转。

### FR-005: 决策信持久化与并发控制
- 决策信存储在 `decision_letters`，关联 `manuscript_id`、`editor_id`、`manuscript_version`。
- 必须支持草稿保存（`status=draft`）和最终提交（`status=final`）。
- 必须实现乐观锁（`updated_at`）避免并发覆盖。

### FR-006: 决策附件上传与下载
- 编辑可上传决策附件并绑定到 `decision_letters`。
- 附件存储于 `decision-attachments` 桶。
- 作者仅能在决策信 `status=final` 后下载对应附件，草稿附件对作者不可见。

### FR-007: 作者通知与可见性
- 决策信及附件仅在 `status=final` 时对作者公开。
- 提交最终决策后必须向作者发送站内通知，包含决策结果与决策信入口。

### FR-008: 权限控制
- 决策工作空间仅 `editor_in_chief`、该稿件 `assigned_editor`、`admin` 可访问。
- 所有写操作必须校验用户身份与稿件归属，禁止越权操作。

---

## 3. 非功能需求 (Non-Functional Requirements)

- **性能**: 决策上下文聚合接口在 UAT 数据规模下需满足 `P95 < 500ms`。
- **易用性**: 必须提供“返回详情页”显著退出路径；退出前若有未保存草稿需提示“内容将丢失”。
- **一致性**: 视觉风格需与 Reviewer Workspace (Feature 040) 对齐（布局节奏、操作区风格、交互反馈）。
- **反馈**: `Save Draft`、`Submit Final Decision`、附件上传均需给出明确成功/失败反馈。
- **安全**: 作者端不得读取草稿内容或草稿附件。

---

## 4. 成功标准 (Success Criteria)

- **SC-001**: 编辑处理 3 位审稿人稿件时，从“查阅意见”到“发出决策信”的平均耗时缩短 40% 以上（UAT 模拟）。
- **SC-002**: 100% 的决策动作在审计日志中包含完整决策信副本与操作者信息。
- **SC-003**: EIC/Assigned Editor 无需打开新标签页即可完成决策。
- **SC-004**: 拒稿路径 100% 满足阶段约束（无 `under_review/resubmitted -> rejected` 直达记录）。

---

## 5. 约束与假设

- 假设 PDF 预览组件已在 Reviewer Workspace 中稳定可复用。
- 仅支持展示 `submitted` 的审稿报告。
- 决策信发送不接入真实邮件网关，MVP 以站内通知为准。
