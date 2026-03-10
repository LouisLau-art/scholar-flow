# Academic Editor 角色与稿件绑定设计说明

日期：2026-03-10  
范围：pre-check academic 分支、academic queue、decision 默认承接人、期刊 scope 角色扩展  
相关技能：`brainstorming`、`api-design-principles`、`postgresql-table-design`

## 背景

当前系统里的 academic 流程只是一个状态分支：

- AE 在 technical check 里选择 `academic`
- 稿件进入 `pre_check/academic`
- `editor_in_chief` 角色在 academic queue 里看到它
- EIC 决定继续送外审或进入 decision

这套实现能跑通流程，但有两个根本缺口：

1. 没有真实的“学术编辑/编委”实体与角色模型  
   当前只有 `editor_in_chief`，没有可以按期刊配置的多个 academic editor。

2. 没有稿件级 academic 责任人绑定  
   同一篇稿件在 pre-check 阶段如果送给张三，后续任何 academic 相关动作都无法默认继续交给张三；系统当前只能按队列和角色兜底。

这与目标业务不符：

- 一本期刊有一个主编和多个编委
- 某篇稿件一旦指定给某个 academic editor，后续默认沿用这同一人
- 但允许在必要时改派

## 现状审计

### 当前角色模型

当前标准角色集合为：

- `author`
- `reviewer`
- `assistant_editor`
- `production_editor`
- `owner`
- `managing_editor`
- `editor_in_chief`
- `admin`

不存在 `academic_editor` 角色。

### 当前 academic 状态流

1. AE 送 academic：
- 路由：`POST /api/v1/editor/manuscripts/{id}/submit-check`
- 请求体：`decision=pass|revision|academic`
- 效果：将稿件改为 `status='pre_check'` + `pre_check_status='academic'`
- 不会指定具体学术编辑

2. academic queue：
- 路由：`GET /api/v1/editor/academic`
- 当前筛选：`status='pre_check' AND pre_check_status='academic'`
- 角色限制：`editor_in_chief` / `admin`

3. academic check：
- 路由：`POST /api/v1/editor/manuscripts/{id}/academic-check`
- 请求体：`decision=review|decision_phase`
- `review` -> `under_review`
- `decision_phase` -> `decision`

### 当前稿件字段

稿件表 `public.manuscripts` 已有：

- `owner_id`
- `journal_id`
- `assistant_editor_id`
- `pre_check_status`
- `status`

但没有：

- `academic_editor_id`
- `academic_submitted_at`
- `academic_completed_at`

当前 `academic_completed_at` 只是详情页读模型根据 `status_transition_logs.payload.action` 反推，不是正式字段。

### 当前 academic assignee 的实际问题

现在 academic 阶段虽然 `current_role` 会显示成 `editor_in_chief`，但 `current_assignee` 本质仍然延续 `assistant_editor_id` 或者干脆没有真实 assignee。  
也就是说，系统没有“这篇稿件当前由哪位学术编辑负责”的第一类事实。

## 目标

### 目标 1：新增正式角色 `academic_editor`

该角色代表：

- 主编
- 编委
- 学术委员会成员

系统不再把 academic 流程全部强绑在 `editor_in_chief` 上。

### 目标 2：为稿件增加真实的 academic 责任人绑定

同一篇稿件需要有正式字段记录：

- 当前 academic editor 是谁
- 什么时候送达 academic
- 什么时候完成 academic

### 目标 3：后续 academic 相关动作默认沿用这同一人

包括但不限于：

- pre-check 阶段送 academic
- `send_first_decision`
- 后续需要再次 academic 介入的场景

默认都走 `academic_editor_id`，但允许改派。

## 非目标

本轮不做：

- academic editor 独立仪表盘的全新视觉重构
- 主编/编委的复杂层级审批链
- 多个 academic editor 并行会签
- decision workspace 的全流程重构

## 候选方案

### 方案 A：新增正式 `academic_editor` 角色 + 稿件绑定字段（推荐）

新增：

- 角色：`academic_editor`
- 稿件字段：
  - `academic_editor_id`
  - `academic_submitted_at`
  - `academic_completed_at`

期刊 scope 允许：

- `academic_editor`
- `editor_in_chief`
- `managing_editor`

当 AE 送 academic 时：

- 必须明确指定一个 academic editor
- 若稿件已有 `academic_editor_id`，默认带出该人
- 允许改派

#### 优点

- 真正表达“主编 + 多个编委”
- 能把 academic assignee 作为一等事实管理
- 后续默认沿用同一人实现简单且可靠
- 与 reviewer / AE / owner 的 assignment 语义一致

#### 缺点

- 需要扩展角色矩阵、scope、数据库字段、前后端 UI

### 方案 B：继续复用 `editor_in_chief`，只增加稿件 academic 绑定字段

新增：

- `academic_editor_id`

但此字段只允许绑定现有 `editor_in_chief` 用户。

#### 优点

- 改动较小

#### 缺点

- 无法表达多个编委
- 与业务真实组织结构不一致
- 后续还要重做

### 方案 C：不加字段，只在审计日志里记录 academic actor

不增加正式 assignee 字段，只靠：

- `status_transition_logs`
- `changed_by`
- payload

来间接推断“最近处理 academic 的人”。

#### 优点

- 最省改动

#### 缺点

- 不是正式分配模型
- 默认沿用同一 academic editor 很脆弱
- 查询和改派都不稳

## 推荐结论

采用 **方案 A**。

理由：

- 目标业务本质上是“新增一个正式工作角色，并把稿件级默认承接人持久化”
- 这不是 UI rename，也不是审计日志能替代的
- 一次建对模型，后面 reviewer / decision / pre-check 的人机流转才不会继续别扭

## 目标设计

### 数据库设计

在 `public.manuscripts` 新增：

- `academic_editor_id uuid null references public.user_profiles(id)`
- `academic_submitted_at timestamptz null`
- `academic_completed_at timestamptz null`

索引：

- `(academic_editor_id, status, updated_at desc)`
- 如有需要，补 `(journal_id, status, academic_editor_id)`

约束：

- 不要求 `academic_editor_id` 永远非空
- 但在稿件进入 `pre_check/academic` 时，服务层必须保证已指定该字段

### 角色与权限

新增角色：

- `academic_editor`

新增动作：

- `academic:view_queue`
- `academic:process`
- `decision:record_first`（按需授予）

权限建议：

- `academic_editor`
  - 可查看分配给自己的 academic queue
  - 可执行 `academic-check`
  - 可在被绑定稿件上进入 first decision workspace
- `editor_in_chief`
  - 继续保留全局学术决策能力
  - 视为 academic 的上位兜底角色
- `managing_editor`
  - 继续可见但不代替 academic assignee

### 期刊 scope

`journal_role_scopes` 允许角色扩展为：

- `managing_editor`
- `assistant_editor`
- `editor_in_chief`
- `academic_editor`

这样一个 academic editor 可以只绑定某些期刊。

### 送 academic 的交互

AE 在 technical check 里选择 `academic` 时：

- 必须指定一个 `academic_editor_id`
- 如果稿件已有 `academic_editor_id`：
  - 默认带出该人
  - AE 可修改
- 提交后：
  - `pre_check_status='academic'`
  - `academic_editor_id=...`
  - `academic_submitted_at=now()`

### academic queue

列表只显示：

- `status='pre_check'`
- `pre_check_status='academic'`

并按 viewer 不同做裁剪：

- `academic_editor`：只看 `academic_editor_id == 自己`
- `editor_in_chief` / `admin`：可看全局（仍受 scope/超管规则控制）
- `managing_editor`：只做管理视图，不作为默认处理人

### academic check 完成

提交 `academic-check` 时：

- `review` -> `under_review`
- `decision_phase` -> `decision`
- 同时写：
  - `academic_completed_at = now()`
- 保留 `academic_editor_id`

这样 decision/workspace 后续都能默认知道这篇稿件的 academic 责任人是谁。

### 后续默认沿用规则

后续凡是“需要 academic 介入”的节点：

- 优先读取 `manuscripts.academic_editor_id`
- 默认发给这个人
- UI 提供改派入口，但不是强制每次重选

### 详情页展示

稿件详情页补充：

- `Academic Editor`
- `Academic Submitted At`
- `Academic Completed At`

Pre-check Role Queue 也要把 `academic` 阶段的 `Current Assignee` 改成真实 `academic_editor_id`，而不是现在这种角色兜底推断。

## 错误处理

### 送 academic 时未指定人

返回：
- `422 academic_editor_id is required when routing to academic`

### 指定的人没有 `academic_editor`/`editor_in_chief` 资格

返回：
- `422 selected academic editor is not eligible`

### 指定的人不在稿件所属 journal scope 内

返回：
- `403 forbidden by journal scope`

### academic editor 访问非自己稿件

返回：
- `403 forbidden`

## 测试策略

### 后端

1. 单元测试
- 送 academic 必须带 `academic_editor_id`
- 送 academic 时默认沿用旧 `academic_editor_id`
- `academic_editor` 只能看自己的 queue
- `editor_in_chief` 可看全队列
- academic check 完成后 `academic_completed_at` 正确写入

2. 集成测试
- `technical -> academic -> review`
- `technical -> academic -> decision`
- 同一稿件多次 academic 介入时默认沿用同一人
- 改派后 queue 归属切换正确

### 前端

1. technical check 弹窗
- 显示 academic editor picker
- 已有 assignee 时默认选中
- 未选中时不能提交 `academic`

2. academic queue
- academic editor 只能看到自己的稿件
- EIC/admin 可看到全局

3. 详情页
- `Academic Editor` 展示正确
- `Pre-check Role Queue` 的 assignee 正确

## 分阶段实施建议

### 第一期

- 新增角色 `academic_editor`
- 扩展 `journal_role_scopes`
- 新增 `manuscripts.academic_*` 字段
- technical check 接入 `academic_editor_id`
- academic queue 按 assignee 裁剪
- 稿件详情页显示真实 assignee

### 第二期

- Admin / User Management 增加 academic editor 管理入口
- 详情页支持改派 academic editor
- decision / send_first_decision 默认沿用同一 academic editor

## 成功标准

满足以下条件视为完成：

1. AE 送 academic 时必须明确一个学术编辑
2. 同一篇稿件进入 academic 阶段后，有真实 `academic_editor_id`
3. academic editor 登录后，只看到属于自己的 academic 稿件
4. `editor_in_chief` 仍可作为上位兜底查看/处理
5. academic 完成后，后续流程默认沿用同一位学术编辑
6. 详情页和队列页不再靠 `assistant_editor_id + role 推断` 冒充 academic assignee
