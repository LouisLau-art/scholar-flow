# Research: GAP-P0-03 Internal Collaboration Enhancement

## Research Scope

围绕 GAP-P0-03，聚焦以下设计决策：
- Notebook 提及对象如何识别并避免“文本解析歧义”。
- 提及提醒是否复用既有通知中心，还是新增专用通知通道。
- 内部任务数据是否拆分为“主表 + 轨迹表”。
- Process 的逾期标识是写时冗余还是读时聚合。
- 任务编辑权限如何在“负责人效率”和“管理可控”间平衡。

## Decisions

### 1. 提及对象采用“显式 ID 提交 + 服务端二次校验”

- **Decision**: 前端在提交评论时传递 `mention_user_ids`，服务端按内部成员身份二次校验后落库。
- **Rationale**:
  - 仅靠评论文本解析 `@名字` 容易受重名、改名、格式噪声影响。
  - 显式 ID 可避免误提及并支持去重通知。
  - 服务端校验可防止伪造提及 ID。
- **Alternatives considered**:
  - 纯文本正则解析：实现快但误判率高，且难处理同名用户。
  - 仅前端校验：安全边界不足，易被绕过。

### 2. 提及提醒复用 `notifications`，不新建消息子系统

- **Decision**: 提及提醒写入现有 `notifications` 表，新增协作通知类型，沿用已有通知读取与已读流程。
- **Rationale**:
  - 已有通知中心和 API 路径完备，符合胶水编程原则。
  - 避免引入新消息基础设施与额外运维复杂度。
- **Alternatives considered**:
  - 新建 `mention_notifications` 表：可专用但会复制通知链路能力。
  - 邮件即时提醒：MVP 成本高且会引入噪声。

### 3. 内部任务采用“主表 + 活动日志表”模型

- **Decision**: 新增 `internal_tasks` 记录当前任务态；新增 `internal_task_activity_logs` 记录状态和字段变化轨迹。
- **Rationale**:
  - 主表用于高频查询，日志表用于审计与复盘，读写职责清晰。
  - 满足“可执行 + 可追责”双目标。
- **Alternatives considered**:
  - 仅主表覆盖写入：历史轨迹丢失，难以复盘。
  - 全量事件溯源单表：查询成本高，MVP 不必要。

### 4. 逾期标识采用“读时聚合”，不做冗余快照列

- **Decision**: 在 Process 查询时按任务截止时间与状态聚合计算 `is_overdue` 与 `overdue_tasks_count`。
- **Rationale**:
  - 避免维护冗余字段导致一致性问题。
  - 结合分页查询可在当前规模下满足性能目标。
- **Alternatives considered**:
  - 在 `manuscripts` 存冗余逾期字段：更新路径复杂，容易出现脏数据。
  - 定时任务回填快照：引入额外异步链路和延迟。

### 5. 任务权限采用“负责人主改 + editor/admin 托底”

- **Decision**:
  - 任务负责人可更新状态与执行备注。
  - `editor/admin` 可更新负责人、截止时间、状态等全部字段。
  - 非负责人且非管理角色仅可读。
- **Rationale**:
  - 保证执行效率，同时保留管理纠偏能力。
  - 与当前编辑角色模型一致，避免引入新权限体系。
- **Alternatives considered**:
  - 全员可编辑：责任边界模糊，易误改。
  - 仅负责人可编辑：管理场景下缺乏干预能力。

## Resolved Clarifications

- 提及协作不依赖新前端入口，直接增强现有 `InternalNotebook`。
- 任务逾期规则统一为“`now > due_at` 且 `status != done`”，不引入复杂 SLA 权重模型。
- Process 只展示“稿件级是否逾期 + 逾期任务数量”，任务明细留在稿件详情页查看。
