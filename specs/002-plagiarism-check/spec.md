# Feature Specification: Manuscript Plagiarism Check

**Feature Branch**: `002-plagiarism-check`  
**Created**: 2026-01-27  
**Status**: Draft  
**Input**: User description: "实现作者投稿后的自动查重功能。系统在作者提交稿件后，自动调用 Crossref 或相似平台的 API 进行全文比对，并生成查重报告。如果查重率超过 30%，自动将稿件状态标记为 'high_similarity' 并通知编辑。查重报告需以 PDF 格式存储并关联至稿件。"

## User Scenarios & Testing

### User Story 1 - 自动触发查重流程 (Priority: P1)

作者完成稿件提交后，系统自动启动异步查重任务，无需人工干预。

**Why this priority**: 核心功能，确保每篇稿件都能在第一时间获得初步的合规性检查。

**Independent Test**: 作者点击“提交稿件”，系统后台立即生成一个处于“查重中”状态的任务，并记录外部 API 的调用请求。

**Acceptance Scenarios**:
1. **Given** 稿件已上传并提交，**When** 系统接收到提交信号，**Then** 自动触发查重异步服务。
2. **Given** 查重任务启动，**When** 任务在后台执行，**Then** 稿件详情页显示“正在查重...”状态。

---

### User Story 2 - 高重复率自动预警 (Priority: P2)

当查重报告返回的相似度超过预设门限（30%）时，系统自动拦截流程并发出预警。

**Why this priority**: 减少编辑的人工初筛工作量，通过自动化手段识别潜在的学术不端风险。

**Independent Test**: 模拟返回 35% 重复率的 API 结果，验证稿件状态是否自动变为 `high_similarity`，且编辑收到了包含链接的通知邮件。

**Acceptance Scenarios**:
1. **Given** 查重任务完成，**When** 相似度结果 > 30%，**Then** 稿件状态更新为 `high_similarity` 并向编辑发送邮件。
2. **Given** 查重任务完成，**When** 相似度结果 <= 30%，**Then** 稿件状态更新为 `submitted` (或进入常规质检流程)。

---

### User Story 3 - 查重报告查看与管理 (Priority: P3)

编辑和系统管理员可以在稿件详情页直接查看和下载生成的 PDF 查重报告。

**Why this priority**: 提供透明的证据支持，方便编辑对“高重复率”稿件进行最终判定。

**Independent Test**: 在稿件详情页点击“下载查重报告”，系统成功返回并下载对应的 PDF 文件。

**Acceptance Scenarios**:
1. **Given** 查重报告已生成并关联，**When** 编辑访问稿件详情页，**Then** 能够看到查重百分比及报告下载链接。

## Edge Cases

- **外部 API 故障**: 当 Crossref 等 API 响应超时或返回 5xx 错误时，系统应支持任务重试。在 3 次自动失败后，系统应在编辑管理后台为该稿件提供“手动重试查重”按钮，允许编辑在排查外部环境后重新发起请求。
- **PDF 格式不兼容**: 如果作者上传的 PDF 无法被外部查重引擎解析，系统应标记为 `check_failed` 并要求编辑介入。
- **并发超限**: 系统应具备队列管理，防止瞬时大量投稿导致外部 API 频率受限。

## Requirements

### Functional Requirements

- **FR-001**: 系统必须在稿件提交成功后 5 分钟内完成查重任务的排队与启动。
- **FR-002**: 必须集成外部查重 API (如 Crossref / iThenticate)。
- **FR-003**: 查重逻辑必须是异步执行的，不得阻塞用户的提交响应。
- **FR-004**: 相似度计算必须支持全文匹配，查重率门限默认为 30%。
- **FR-005**: 查重报告必须以 PDF 格式持久化存储至 Supabase Storage。
- **FR-006**: 当检测到高相似度时，通知邮件必须包含：稿件 ID、标题、重复率、报告链接。

### Key Entities

- **PlagiarismReport (查重任务/报告)**: 
  - `id`: 唯一标识
  - `manuscript_id`: 关联稿件
  - `similarity_score`: 重复率数字 (0-100)
  - `report_url`: PDF 存储路径
  - `status`: `pending`, `running`, `completed`, `failed`
  - `external_task_id`: 外部 API 的任务 ID

## Success Criteria

### Measurable Outcomes

- **SC-001**: 95% 的查重任务应在投稿后 30 分钟内生成结果（取决于外部 API 响应）。
- **SC-002**: 查重报告与稿件的关联正确率必须为 100%。
- **SC-003**: 相似度超过 30% 时的自动拦截和通知成功率必须为 100%。

## Assumptions

- 假设项目已具备有效的 Crossref 或 iThenticate API 访问凭证。
- 查重过程完全依赖外部服务提供的 PDF 报告，系统本身不进行文本比对计算。
- 查重率的计算标准遵循外部服务提供商的通用定义。