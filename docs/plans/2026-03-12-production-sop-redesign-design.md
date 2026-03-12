# Production SOP Redesign Design

**Date:** 2026-03-12

**Status:** approved for implementation

**Related Skills:** `brainstorming`, `writing-plans`, `api-design-principles`, `context7-docs-lookup`

## Problem

当前系统的 production 实现已经有可用的 MVP，但它和目标 SOP 之间仍有结构性偏差：

- 业务上希望是 `AE 主导 + 多角色交接`，当前实现实际上是 `ME / production_editor` 主导。
- 业务上希望稿件生产是单一链路，当前实现同时存在：
  - 稿件主状态线性推进：`approved -> layout -> english_editing -> proofreading -> published`
  - production cycle 子状态机：`draft -> awaiting_author -> author_confirmed/...`
- 业务上希望每一步都有明确责任人和产物，当前实现只有：
  - 一个 `layout_editor_id`
  - 作者校对反馈
  - 一个可发布 `galley_path`
- 业务上希望 `最终确认版` 是独立产物，当前实现会把当前 galley 直接写进 `final_pdf_path`。

这会带来三个直接问题：

1. 权限和责任边界错位，AE 在录用后反而被挡在 production 外。
2. 流程可审计性不足，看不到“谁在什么时候把稿件交给了谁”。
3. 双轨状态机会让页面、通知、门禁和真实业务进度发生漂移。

## Goals

- 让 production 流程与 10 步 SOP 语义对齐。
- 采用“少量稳定平台角色 + 每稿件责任人字段”的方式建模，而不是一开始把所有岗位硬编码成平台角色。
- 让 production cycle 成为 production 业务的唯一驱动状态机。
- 为每个关键步骤保留独立产物和可追踪的交接事件。
- 保持对现有 `approved/layout/english_editing/proofreading/published` 生态的兼容迁移，避免一次性冲击全仓。

## Non-Goals

- 本轮不重做 pre-check / reviewer / decision 主流程。
- 本轮不引入外部 BPM/工单系统。
- 本轮不把作者生产沟通升级成复杂的多人协作批注系统。
- 本轮不直接砍掉所有旧字段；允许阶段性兼容读写。

## Confirmed Product Decisions

### Role Strategy

采用“少角色 + 每稿件多责任人字段”方案。

平台级稳定角色保留：

- `assistant_editor`
- `production_editor`
- `managing_editor`
- `admin`

production cycle 内的流程责任人单独挂字段：

- `coordinator_ae_id`
- `typesetter_id`
- `language_editor_id`
- `pdf_editor_id`
- `proofreader_author_id`

说明：

- 同一个用户可以兼任多个责任节点。
- 队列按“当前阶段 + 当前责任人”生成，而不是按平台角色硬拆。

### Author Feedback Strategy

作者在 production 阶段提交的是“校对反馈包”，不是直接替换正式稿。

反馈包包含：

- 必填：结构化 correction list
- 可选：annotated PDF / proof attachment
- 可选：summary note

### Final Artifact Strategy

`最终确认版` 必须是独立文件产物，不能再把当前 galley 直接视为 `final_pdf_path`。

### Workflow Source of Truth

production 业务的真实进度由 `production_cycle.stage` 驱动。

`manuscripts.status` 在过渡期保留，但只作为兼容视图 / 外层粗粒度状态，不再作为 production 详细步骤的独立状态机。

## Options Considered

### Option A: 4 个硬编码平台角色

平台直接新增：

- `typesetter`
- `language_editor`
- `pdf_editor`

优点：

- 与 SOP 文案最直观一致。

缺点：

- 对组织结构过于刚性。
- 兼岗、代理、外包都会让权限模型快速复杂化。
- 需要全仓补角色枚举、权限和导航分支。

### Option B: 保留单一 `production_editor`，只细化状态

优点：

- 实现最快。

缺点：

- 责任人不清晰。
- 审计和队列不可读。
- 无法可靠支持“谁该接下一步”。

### Option C: 稳定平台角色 + per-cycle 责任人字段（推荐）

优点：

- 兼顾组织弹性与流程精确度。
- 可以逐步演进，不要求一次性角色大迁移。
- 更适合当前仓库已有的 `production_editor` / `assistant_editor` 基础。

结论：

采用 **Option C**。

## Recommended Domain Model

## 1. Aggregate

继续使用 `production_cycles` 作为 production 聚合根，但升级其字段语义。

新增/调整核心字段：

- `stage`
- `coordinator_ae_id`
- `typesetter_id`
- `language_editor_id`
- `pdf_editor_id`
- `current_assignee_id`
- `author_feedback_required bool`
- `final_confirmation_artifact_id`
- `publication_artifact_id`

保留现有：

- `manuscript_id`
- `cycle_no`
- `proofreader_author_id`
- `approved_by`
- `approved_at`

说明：

- `current_assignee_id` 是读优化字段，便于队列查询。
- 真正权限仍由 `stage + responsibility fields` 判定。

## 2. Versioned Artifacts

新增 `production_cycle_artifacts` 表，替代把不同阶段文件都塞进 `production_cycles`。

建议字段：

- `id`
- `cycle_id`
- `manuscript_id`
- `artifact_kind`
- `storage_bucket`
- `storage_path`
- `file_name`
- `mime_type`
- `uploaded_by`
- `created_at`
- `supersedes_artifact_id nullable`
- `metadata jsonb`

`artifact_kind` 建议枚举：

- `source_manuscript_snapshot`
- `typeset_output`
- `language_output`
- `ae_internal_proof`
- `author_annotated_proof`
- `final_confirmation_pdf`
- `publication_pdf`

这样可以保证：

- 每一步产物独立保存
- 可追踪替换关系
- 最终确认版与发布版不再混淆

## 3. Author Feedback

保留现有：

- `production_proofreading_responses`
- `production_correction_items`

并扩展作者反馈附件能力：

- `attachment_bucket nullable`
- `attachment_path nullable`
- `attachment_file_name nullable`

这样可以继续复用当前 correction list 逻辑，同时支持可选批注 PDF。

## 4. Audit / Handoff Events

新增 `production_cycle_events` 表，用 append-only 方式记录交接动作，而不是只依赖最终状态。

建议字段：

- `id`
- `cycle_id`
- `manuscript_id`
- `event_type`
- `from_stage`
- `to_stage`
- `actor_user_id`
- `target_user_id nullable`
- `artifact_id nullable`
- `comment nullable`
- `payload jsonb`
- `created_at`

典型 `event_type`：

- `cycle_created`
- `assigned_to_typesetter`
- `typeset_uploaded`
- `assigned_to_language_editor`
- `language_edit_uploaded`
- `ae_internal_proof_completed`
- `sent_to_author`
- `author_feedback_submitted`
- `returned_to_typesetter`
- `returned_to_language_editor`
- `final_confirmation_uploaded`
- `sent_to_pdf_editor`
- `publication_pdf_uploaded`
- `marked_ready_to_publish`
- `published`

## Recommended Workflow State Machine

## 1. Production Cycle Stages

推荐 `production_cycle.stage` 使用以下值：

- `received`
- `typesetting`
- `language_editing`
- `ae_internal_proof`
- `author_proofreading`
- `ae_final_review`
- `pdf_preparation`
- `ready_to_publish`
- `published`
- `cancelled`

说明：

- 状态表示“当前工作由谁持有 / 正在做什么”，而不是把每个按钮都编码成状态。
- 具体“发送给谁”“上传了什么文件”由 `production_cycle_events` 记录。

## 2. SOP Mapping

你给的 10 步 SOP 与建议状态/事件映射如下：

1. 接收稿件  
   - `stage = received`
   - event: `cycle_created`

2. AE -> 发送稿件给排版编辑  
   - transition: `received -> typesetting`
   - event: `assigned_to_typesetter`

3. 排版编辑下载稿件 -> 完成排版 -> 上传排版后稿件  
   - stage remains `typesetting`
   - artifact: `typeset_output`
   - transition to `language_editing`

4. 流转至英语语言修改编辑 -> 润色 -> 上传润色后稿件  
   - artifact: `language_output`
   - transition to `ae_internal_proof`

5. AE 下载排版+润色稿件 -> 进行内部校对  
   - stage `ae_internal_proof`
   - 可选 artifact: `ae_internal_proof`
   - transition to `author_proofreading`

6. AE -> 发送稿件给作者校对  
   - event: `sent_to_author`
   - stage `author_proofreading`

7. 作者完成校对 -> 提交校对反馈包  
   - response + correction items + optional `author_annotated_proof`
   - transition to `ae_final_review`

8. AE 检查作者校对后的稿件  
   - stage `ae_final_review`
   - 可选择：
     - 回 `typesetting`
     - 回 `language_editing`
     - 进入 `pdf_preparation`

9. 检查无误 -> AE 上传最终确认版本  
   - artifact: `final_confirmation_pdf`
   - event: `final_confirmation_uploaded`
   - transition to `pdf_preparation`

10. 发送给 PDF 编辑 -> 完成上线  
   - stage `pdf_preparation`
   - artifact: `publication_pdf`
   - transition to `ready_to_publish`
   - publish gate passed -> `published`

## 3. Loop Handling

SOP 主链是线性的，但系统必须支持回退闭环。

允许的回退：

- `ae_final_review -> typesetting`
- `ae_final_review -> language_editing`
- `pdf_preparation -> ae_final_review`

不允许作者直接把正式文件状态推到 `ready_to_publish`。

## Manuscript Status Compatibility

为减少对现有列表页、分析页、财务门禁的冲击，`manuscripts.status` 在过渡期继续存在，但从 `production_cycle.stage` 派生。

推荐映射：

- 无 active cycle 且已录用：`approved`
- `received | typesetting` -> `layout`
- `language_editing` -> `english_editing`
- `ae_internal_proof | author_proofreading | ae_final_review | pdf_preparation | ready_to_publish` -> `proofreading`
- `published` -> `published`

原则：

- 主状态只反映外层 bucket
- 真正详细节点只看 `production_cycle.stage`

这意味着：

- 旧的 `ProductionStatusCard` 不再拥有独立推进权
- 新 workspace 才是唯一合法的 production 详细操作入口

## Permissions Model

## Internal Roles

- `managing_editor` / `admin`
  - create cycle
  - assign / reassign all responsibilities
  - override stage transitions
  - publish approval

- `assistant_editor`
  - 当且仅当担任 `coordinator_ae_id` 时可进入 production workspace
  - 可执行：
    - handoff to typesetter
    - handoff to author
    - review author feedback
    - upload final confirmation

- `production_editor`
  - 只在被分配为以下任一字段时可访问该 cycle：
    - `typesetter_id`
    - `language_editor_id`
    - `pdf_editor_id`
  - 仅可执行与自己当前责任相匹配的上传/完成动作

- `author`
  - 只在 `stage = author_proofreading` 时可提交反馈包

## Permission Principle

权限由“是否为当前责任人 + 当前 stage 是否匹配”决定，不再由宽泛角色直接放行所有 production 写操作。

## API Design

遵循两个原则：

1. 资源仍然是 `production cycle / artifacts / feedback / events`
2. 状态机动作集中到少量可审计 endpoint，不再四散到多个 legacy endpoint

## Recommended Endpoints

### Cycle Read

- `GET /api/v1/editor/manuscripts/{id}/production-workspace`
- `GET /api/v1/editor/production/queue`

### Cycle Lifecycle

- `POST /api/v1/editor/manuscripts/{id}/production-cycles`
- `PATCH /api/v1/editor/manuscripts/{id}/production-cycles/{cycle_id}/assignments`
- `POST /api/v1/editor/manuscripts/{id}/production-cycles/{cycle_id}/transitions`

`transitions` 请求体建议：

- `action`
- `comment`
- `target_user_id nullable`
- `return_target_stage nullable`

示例 `action`：

- `handoff_to_typesetter`
- `complete_typesetting`
- `handoff_to_language_editor`
- `complete_language_edit`
- `send_to_author`
- `review_author_feedback`
- `return_to_typesetting`
- `return_to_language_editing`
- `send_to_pdf_editor`
- `mark_ready_to_publish`
- `publish`

### Artifact Upload / Download

- `POST /api/v1/editor/manuscripts/{id}/production-cycles/{cycle_id}/artifacts`
- `GET /api/v1/editor/manuscripts/{id}/production-cycles/{cycle_id}/artifacts/{artifact_id}/signed-url`

上传请求必须显式带：

- `artifact_kind`
- `comment`
- `replace_previous optional`

### Author Feedback

- `GET /api/v1/manuscripts/{id}/proofreading-context`
- `POST /api/v1/manuscripts/{id}/production-cycles/{cycle_id}/author-feedback`
- `GET /api/v1/manuscripts/{id}/production-cycles/{cycle_id}/artifacts/{artifact_id}/signed-url`

## Frontend Design

## Editor Workspace

`/editor/production/[id]` 改成真正的 cycle workspace：

- 左栏：当前可操作文件预览
- 中栏：阶段时间线 + artifact timeline + event log
- 右栏：当前 stage 动作面板 + assignments + warnings

动作面板根据当前登录人责任和 stage 动态裁剪。

## Manuscript Detail

稿件详情页保留：

- `Open Production Workspace`
- 只读 production summary

移除：

- 直接 `advance / revert production` 按钮

原因：

- 详细推进必须统一收口到 workspace

## Production Queue

`/editor/production` 继续保留，但队列项由“被分配到我 + 当前 stage”驱动。

可选筛选：

- `all assigned to me`
- `as coordinator AE`
- `as typesetter`
- `as language editor`
- `as PDF editor`

## Author Proofreading Page

`/proofreading/[id]` 继续保留，但升级为：

- proof PDF preview
- correction list
- optional annotated PDF upload
- 只读回显已提交反馈

作者仍然不能直接上传“最终正式版”。

## Migration Strategy

采用分阶段兼容迁移，而不是一次性切换。

### Phase 1: Schema Expansion

- 给 `production_cycles` 增加 `stage + assignments`
- 新建 `production_cycle_artifacts`
- 新建 `production_cycle_events`
- 扩展 `production_proofreading_responses` 附件字段

### Phase 2: Dual Read / Dual Write

- 新服务优先读 `stage`
- 旧页面继续读 `manuscripts.status`
- transition 同时写：
  - `production_cycle.stage`
  - 派生的 `manuscripts.status`

### Phase 3: UI Cutover

- 废弃详情页直接推进按钮
- 所有 production 详细动作切到 workspace

### Phase 4: Cleanup

- 逐步移除旧 `production cycle status` 语义
- 移除直接用 `galley_path` 覆盖 `final_pdf_path` 的逻辑

## Testing Strategy

高风险改动，必须按 TDD 推进。

### Backend

- 单元测试：
  - stage transition validation
  - permission matrix
  - compatibility status mapping
  - artifact kind validation

- 集成测试：
  - full SOP happy path
  - AE return to typesetting/language loop
  - author feedback with and without attachment
  - final confirmation artifact required before PDF stage
  - publish gate requires `ready_to_publish + paid + publication artifact`

### Frontend

- 单元测试：
  - workspace action visibility
  - assignment panel
  - proofreading form with attachment
  - production summary card read-only behavior

- E2E：
  - full SOP flow
  - author submits correction package
  - AE sends back to typesetter
  - PDF editor uploads publication PDF and publish succeeds

## Best-Practice Notes

这套设计与官方实践的关系：

- FastAPI 侧继续保持 `router + service + model` 分层，符合官方 “Bigger Applications” 思路。
- Next.js 侧应逐步把 production/proofreading 首屏数据移动到 App Router Server Component，交互部分再下沉为 Client Component，减少全页面 client-side 首屏拉取。

参考文档：

- FastAPI Bigger Applications: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- Next.js App Router Data Fetching: https://nextjs.org/docs/app/building-your-application/data-fetching

## Final Recommendation

本轮 production 改造不应该继续在现有双轨流程上打补丁。

正确方向是：

- 保留稳定平台角色
- 把责任人绑定到 production cycle
- 用 `production_cycle.stage` 作为唯一业务驱动状态机
- 用 `artifacts + events` 解决产物与交接可追踪性
- 让 `manuscripts.status` 退化为兼容 bucket

这既能对齐你的 10 步 SOP，也能避免一次性把全仓权限和角色体系打碎重来。
