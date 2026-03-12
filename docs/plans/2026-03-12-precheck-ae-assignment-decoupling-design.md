# Pre-check 技术退回与 AE 责任归属解耦设计说明

日期：2026-03-12  
范围：ME intake、AE technical return、作者修回回流、AE 分配/改派入口、预审读模型  
相关技能：`brainstorming`、`senior-architect`、`api-design-principles`、`architecture-decision-records`

## 背景

当前 UAT 暴露的问题不是单个按钮命名不准，而是工作流模型把两件不同的事绑在了一起：

- `技术退回作者`：表示流程当前被作者修改阻塞
- `分配/改派 AE`：表示下一位或当前责任执行人是谁

真实编辑业务里，这两件事不冲突：

1. ME 可以先把稿件技术退回给作者
2. 随后仍然可以指定或改派 AE
3. 作者修回后，稿件应直接进入当前责任 AE 的 workspace

当前系统只做对了一半：

- 后端 `assign_ae()` 已允许在 `pre_check/intake` 与 `pre_check/technical` 分配或重分配 AE
- 作者修回链路也已支持回到 `intake` 或 `technical`

但另一半实现仍然把“等待作者修回”视为“不可再分配 AE”，导致前端呈现与业务冲突。

## 现状审计

### 当前正确的部分

1. `backend/app/services/editor_service_precheck_intake.py`
- `assign_ae()` 已支持：
  - `status='pre_check'`
  - `pre_check_status in {'intake', 'technical'}`
- 说明系统服务层已经承认 “AE 分配” 不是 Intake 一次性动作。

2. `backend/app/services/revision_service.py`
- 作者修回时，`submit_revision()` 已支持：
  - `precheck_resubmit_stage='intake'` -> 回 `pre_check/intake`
  - `precheck_resubmit_stage='technical'` -> 回 `pre_check/technical`
- 若回 `technical`，会保留 `assistant_editor_id`

这说明“作者修回直接回 AE”在后端逻辑上已经是成立的业务能力。

### 当前错误的部分

1. `frontend/src/app/(admin)/editor/intake/page.tsx`
- Intake 页文案明确写成：
  - “技术退回稿会以灰态保留，直至作者修回”
- 对等待作者修回的行直接渲染为：
  - `等待作者修回（不可操作）`

2. `backend/app/services/editor_service_precheck_intake.py`
- `get_intake_queue()` 会把 `revision_before_review` 且来源于 `precheck_intake_revision` 的稿件拼接进 Intake 列表
- 这些行天然被当作“被动占位”，不是“可继续管理责任归属的稿件”

3. `frontend/src/components/AssignAEModal.tsx`
- 当前只在 Intake 页复用
- 稿件详情页和 Managing Workspace 没有统一的 AE 改派入口

因此，现状的问题不是“缺一个第三按钮”，而是：

- 页面把队列视图和责任管理混成了同一概念
- 导致“等待作者修回”错误推导成“不能分配/改派 AE”

## 目标

### 目标 1：解耦流程阻塞与责任归属

- 作者待修回，不影响记录当前 AE
- AE 可在作者修回前被指定或改派

### 目标 2：统一作者修回回流规则

- 若稿件在退回时已绑定 AE 且目标恢复阶段为 `technical`
  - 作者修回后直接进入 AE workspace
- 若未绑定 AE 或目标恢复阶段为 `intake`
  - 作者修回后回到 ME intake

### 目标 3：让 AE 改派成为全流程通用动作

- 不再把 “分配 AE” 视为 Intake 专属按钮
- 稿件详情页应成为稳定入口
- Managing Workspace 可作为全局管理入口

## 非目标

本轮不做：

- 新建独立核心业务表
- 重做完整编辑台 IA
- 改写 reviewer / decision / production 主要流程
- 引入复杂的多 AE 协作模型

## 候选方案

### 方案 A：只在 Intake 灰态行补一个“分配/改派 AE”按钮

做法：

- 保留当前 `revision_before_review` 灰态占位
- 在灰态行上直接打开 `AssignAEModal`

优点：

- 改动最小
- 能立刻解决 UAT 表面痛点

缺点：

- `Intake Queue` 会继续混合两种完全不同的对象：
  - 真正待 Intake 审查稿件
  - 只是等待作者但允许改派责任人的稿件
- 页面语义继续失真
- 以后还会继续出现“为什么在 Intake 里能改派一个其实不归 Intake 处理的稿件”

### 方案 B：保持现有表结构，采用“双轴模型”解耦（推荐）

做法：

- 不新增核心表
- 明确：
  - `status` 只表示流程状态
  - `pre_check_status` 表示当前或恢复目标预审子阶段
  - `assistant_editor_id` 只表示 AE 责任归属
- 允许在等待作者修回期间继续设置 `assistant_editor_id`

优点：

- 贴合真实业务
- 与现有代码基础兼容度高
- 不需要大规模数据库迁移
- 能统一“作者修回回到 ME 还是 AE”的规则

缺点：

- 需要澄清 `pre_check_status` 在 `revision_before_review` 下的语义
- 需要同步调整队列读模型与 UI 文案

### 方案 C：新增独立字段 `resume_stage` / `blocking_state`

做法：

- 为 `revision_before_review` 增加专门的恢复目标字段与阻塞态字段

优点：

- 领域模型最干净

缺点：

- 迁移与读模型改造更重
- 对当前 MVP 过度设计

## 推荐结论

采用 **方案 B**。

理由：

1. 这是最符合真实业务的最小正确模型  
   不是用页面按钮弥补状态机缺陷，而是直接把“状态”和“责任人”分开。

2. 现有后端已经部分按这个方向实现  
   继续顺着现有代码修正，比全量重构更稳。

3. 风险可控  
   不需要新增核心业务表，只需澄清字段语义、放宽 guard、补齐统一入口与测试。

## 目标设计

## 一、字段语义

### 1. `status`

表示稿件此刻主流程状态：

- `pre_check`
- `revision_before_review`
- `under_review`
- ...

不再承载“是否已有 AE”这类责任信息。

### 2. `assistant_editor_id`

表示当前负责或下一步负责该稿件 technical follow-up 的 AE。

规则：

- 可为空
- 一旦设置，不因“等待作者修回”而自动清空
- 仅在明确要回 ME intake 时才清空

### 3. `pre_check_status`

在本轮设计中，`pre_check_status` 语义扩展为：

- 当 `status='pre_check'` 时：当前预审子阶段
- 当 `status='revision_before_review'` 时：作者修回后应恢复到的预审子阶段

允许值仍为：

- `intake`
- `technical`
- `academic`

但本轮只使用前两种恢复目标：

- `revision_before_review + pre_check_status='intake'`
- `revision_before_review + pre_check_status='technical'`

不引入 `revision_before_review + academic` 的产品能力。

## 二、规范状态组合

### 1. ME 入口技术退回

目标状态：

- `status='revision_before_review'`
- `pre_check_status='intake'`
- `assistant_editor_id=null`

含义：

- 稿件等待作者修回
- 修回后先回 ME intake

### 2. AE technical 退回

目标状态：

- `status='revision_before_review'`
- `pre_check_status='technical'`
- `assistant_editor_id=<当前 AE>`

含义：

- 稿件等待作者修回
- 修回后直接回原 AE workspace

### 3. ME 在等待作者期间指定/改派 AE

允许状态：

- `status='revision_before_review'`
- `pre_check_status in {'intake', 'technical'}`

行为：

- 设置或更新 `assistant_editor_id`
- 同步把 `pre_check_status` 置为 `technical`

含义：

- 即使此前由 ME 退回，ME 也可以在作者修回前先把后续责任人指定好
- 作者修回后直接进入 AE workspace

## 三、作者修回回流规则

作者提交修回稿时，服务端按以下规则恢复：

1. 若当前稿件为：
- `status='revision_before_review'`
- `pre_check_status='technical'`
- `assistant_editor_id` 非空

则恢复为：

- `status='pre_check'`
- `pre_check_status='technical'`
- 保留 `assistant_editor_id`

2. 其他 `revision_before_review` 情况，恢复为：

- `status='pre_check'`
- `pre_check_status='intake'`
- `assistant_editor_id=null`

这条规则应成为唯一 canonical rule，避免依赖零散日志推断。

## 四、API 设计

### 1. 继续复用 `POST /api/v1/editor/manuscripts/{id}/assign-ae`

不新建 “退回后分配 AE” 专门接口。

原因：

- 这是同一资源上的同一职责变更
- 复用现有接口更符合 REST 资源语义

新的允许条件：

- `status='pre_check' AND pre_check_status in {'intake','technical'}`
- `status='revision_before_review' AND pre_check_status in {'intake','technical'}`

新的行为规则：

- 在 `revision_before_review` 下分配 AE 时：
  - `assistant_editor_id=<new_ae>`
  - `pre_check_status='technical'`

### 2. `POST /api/v1/editor/manuscripts/{id}/intake-return`

返回作者时应显式写入：

- `status='revision_before_review'`
- `pre_check_status='intake'`
- `assistant_editor_id=null`

不能再只依赖旧状态残留。

### 3. `POST /api/v1/editor/manuscripts/{id}/submit-check`

AE technical return 时应显式写入：

- `status='revision_before_review'`
- `pre_check_status='technical'`
- 保留 `assistant_editor_id`

## 五、审计日志设计

保留既有动作名：

- `precheck_assign_ae`
- `precheck_reassign_ae`
- `precheck_intake_revision`
- `precheck_technical_revision`

新增 payload 约定：

```json
{
  "action": "precheck_assign_ae",
  "source_status": "revision_before_review",
  "source_pre_check_status": "intake",
  "assistant_editor_before": null,
  "assistant_editor_after": "ae-uuid",
  "pre_check_from": "intake",
  "pre_check_to": "technical"
}
```

这样可以在不引入新动作名的前提下，区分“等待作者期间的改派”。

## 六、UI 设计

### 1. Intake Queue

目标语义：

- 只展示需要 ME 做入口审查决策的稿件

因此推荐：

- `pre_check/intake` 仍在 Intake Queue 中作为主对象
- `revision_before_review` 等待作者的稿件不再强调为 Intake 的“不可操作灰态主对象”

为了兼顾过渡期，可接受两种落地顺序：

#### Phase 1（推荐先做）

- Intake 页保留等待作者行，但不再写死“不可操作”
- 至少提供一个显式入口：
  - `打开详情`
  - 或 `改派 AE`

#### Phase 2（推荐收敛）

- 把等待作者的稿件移出 Intake Queue
- 统一放入 Managing Workspace 的 `awaiting_author` 分组

### 2. Managing Workspace

新增 bucket：

- `awaiting_author`

展示对象：

- `status='revision_before_review'`

展示信息：

- 当前恢复目标：`回 ME intake` / `回 AE technical`
- 当前 AE：有则显示，没有则显示未分配
- 最近退回原因
- 更新时间

可执行动作：

- `分配/改派 AE`
- `打开稿件详情`

### 3. Manuscript Detail

稿件详情页应成为正式的全局 AE 分配入口。

规则：

- 只要稿件未终态，ME/Admin 都可以看到 `Assign/Change AE`
- 文案依据当前状态调整：
  - `pre_check/intake`：分配 AE
  - `pre_check/technical`：改派 AE
  - `revision_before_review`：为修回后指定/改派 AE
  - `under_review/resubmitted/decision`：改派 AE

这是本轮最重要的交互调整之一，因为它把 AE 归属从单页面按钮升级成稿件级通用能力。

## 七、通知设计

### 1. 改派 AE 当下不立即催办

在 `revision_before_review` 等待作者期间改派 AE 时：

- 记录审计
- 可发内部站内通知
- 但不应把稿件放进 AE 的 actionable technical 列表

### 2. 作者修回时通知当前责任人

作者修回成功后：

- 若恢复到 `pre_check/technical`
  - 通知当前 `assistant_editor_id`
- 若恢复到 `pre_check/intake`
  - 通知 ME / owner / 最近操作的 managing editor

## 八、兼容性与迁移策略

本轮不要求新增表或新增数据库列。

兼容策略：

1. 继续复用：
- `status`
- `pre_check_status`
- `assistant_editor_id`

2. 修复所有关键写路径的显式赋值

不能依赖“旧值恰好残留正确”：

- ME intake return 明确写 `pre_check_status='intake'`
- AE technical return 明确写 `pre_check_status='technical'`
- 等待作者期间 assign AE 明确写 `pre_check_status='technical'`

3. 读模型统一解释

凡是读 `revision_before_review` 的地方，都要把 `pre_check_status` 解释为“恢复目标”，而不是当前活跃 pre-check 子阶段。

## 九、测试策略

### 后端单测

必须覆盖：

- `request_intake_revision()` 后显式写入 `pre_check_status='intake'`
- `submit_technical_check(decision='revision')` 后显式保留 `pre_check_status='technical'`
- `assign_ae()` 允许在 `revision_before_review/intake|technical` 下执行
- 在等待作者期间 assign AE 后，作者修回进入 `pre_check/technical`

### 后端集成测试

必须覆盖：

1. ME 退回 -> ME 指派 AE -> 作者修回 -> 进入 AE workspace
2. AE 退回 -> ME 改派 AE -> 作者修回 -> 进入新 AE workspace
3. 等待作者期间未分配 AE -> 作者修回 -> 回 Intake

### 前端回归

必须覆盖：

- Intake / Managing Workspace / Detail 中至少有一个稳定入口允许等待作者期间改派 AE
- 作者修回后页面跳转和通知落到正确 workspace

## 十、结论

这次问题的根因不是按钮数量不够，而是模型把“流程阻塞”和“责任归属”绑成了一件事。

本轮设计采用的核心原则是：

- `技术退回` 只表示作者必须修回
- `AE 分配/改派` 只表示谁负责下一步 technical follow-up

两者正交后，流程会恢复为更符合真实编辑部运作的状态：

- ME 可以先退回
- 再指定或改派 AE
- 作者修回后系统自动把稿件送到正确的人手里

