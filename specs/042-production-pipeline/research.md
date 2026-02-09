# Research: Production Pipeline Workspace (Feature 042)

## Research Scope

根据 `plan.md` 的技术上下文与集成点，聚焦以下问题：
- 生产轮次数据是否独立建模。
- 清样与核准版本的存储边界。
- 作者校对反馈的结构化表达。
- 权限模型如何与现有角色体系兼容。
- 发布门禁如何绑定“已核准生产版本”。

## Decisions

### 1. 生产流程采用独立轮次实体，而非堆叠到 `manuscripts` 单表

- **Decision**: 新增 `production_cycles`（轮次）和 `production_proofreading_responses`（作者反馈）等实体，`manuscripts.status` 继续承担全局状态机。
- **Rationale**: 轮次数据（截止时间、清样版本、作者反馈）具有一稿多次迭代特征，若放在 `manuscripts` 会导致字段拥挤且难追溯。
- **Alternatives considered**:
  - 将轮次字段直接加到 `manuscripts`：实现快，但无法支持多轮历史与审计回放。
  - 用 JSON 字段存所有轮次：灵活但查询/校验复杂，测试与运维成本高。

### 2. 清样文件使用独立私有桶 `production-proofs`

- **Decision**: 新建私有 Storage bucket `production-proofs` 存储清样；最终可发布版本在核准后同步回填到发布门禁可读取的字段。
- **Rationale**: 与作者原稿桶、审稿附件桶隔离后，权限策略更清晰，避免误读误写。
- **Alternatives considered**:
  - 复用 `manuscripts` 桶并用路径前缀区分：改造成本低，但权限边界与历史治理容易耦合。
  - 复用 `review-attachments` 桶：语义不匹配，且会污染审稿附件访问策略。

### 3. 作者校对反馈采用“二选一 + 条目化修正”

- **Decision**: 反馈模式固定为 `confirm_clean` 或 `submit_corrections`；选择修正时需提交至少一条 correction item。
- **Rationale**: 结构化反馈比自由文本更易驱动后续处理和验收，且能直接支持审计与统计。
- **Alternatives considered**:
  - 仅允许自由文本：实现简单，但难以判断“是否完成校对”和“修正项是否闭环”。
  - 强制逐页批注工具：体验更强，但超出 MVP 范围，复杂度过高。

### 4. 权限策略按“角色 + 归属 + 轮次指派”三重校验

- **Decision**: 编辑端操作要求 `editor/admin` 且具备稿件归属；作者端提交要求命中 `proofreader_author_id`；所有文件下载均通过后端签名 URL。
- **Rationale**: 单纯角色校验不足以避免越权访问，必须叠加稿件与轮次绑定关系。
- **Alternatives considered**:
  - 仅角色校验：实现最省，但存在“同角色跨稿件越权”风险。
  - 完全依赖 RLS：与当前 MVP 的后端鉴权策略不一致，改造范围过大。

### 5. 发布门禁绑定“核准轮次”，并保持对现有 `Production Gate` 的兼容

- **Decision**: 发布前必须存在 `production_cycles.status=approved_for_publish` 的最新轮次；若环境启用了 `PRODUCTION_GATE_ENABLED`，仍需满足 `final_pdf_path` 规则。
- **Rationale**: 既满足“只能发布已核准生产版本”的业务要求，又兼容现有部署中的可选门禁逻辑。
- **Alternatives considered**:
  - 仅保留旧 `final_pdf_path` 门禁：无法证明该文件来自作者确认后的生产轮次。
  - 仅保留新轮次门禁并移除旧门禁：会破坏已有生产流程兼容性。

### 6. 通知策略沿用“最小触达”原则

- **Decision**: 仅向 `owner_id/editor_id` 与责任作者发送生产节点通知，不进行 editor/admin 群发。
- **Rationale**: 遵循现有 MVP 约束，避免群发导致噪声与 409 日志刷屏。
- **Alternatives considered**:
  - 全员广播：感知范围大，但噪声过高且与既有约束冲突。
  - 完全不通知：流程可执行但协作效率差，易错过 SLA。

## Resolved Clarifications

本阶段无未决 `NEEDS CLARIFICATION` 项，所有关键设计选择已形成明确结论，可进入 Phase 1 设计与合同定义。
