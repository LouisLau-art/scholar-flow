# Managing Workspace 单页收口与首屏稳定性修复设计

日期：2026-03-12  
范围：Managing Editor Intake / Managing Workspace 信息架构收口、首屏受保护请求稳定性、缓存失效、错误态  
相关技能：`brainstorming`、`senior-architect`、`systematic-debugging`、`context7`

## 背景

当前 ME 侧存在两个并行问题：

1. 信息架构重复  
   `Intake Queue` 与 `Managing Workspace` 都会展示部分相同稿件，尤其是 `pre_check/intake` 与 `revision_before_review` 相关对象，用户很容易感知为“两个差不多的页面”。

2. 首屏体验不稳定  
   两个页面都采用客户端 `useEffect` 首屏拉取受保护数据；鉴权恢复、组件缓存、API 缓存和后端短缓存叠加后，容易出现：
   - 首次进入空列表
   - 手动刷新后才有数据
   - mutation 后视图未及时更新
   - 实际请求失败但 UI 表现为空态

本设计的目标不是继续给现有双页面打补丁，而是把 ME 工作面收口成一个主页面，同时在同一轮修复真实的稳定性根因。

## 问题拆解

### 一、产品层问题

当前后端语义其实并不完全错误：

- `Intake Queue` 本意是“ME 当前要做首次入口处理的动作队列”
- `Managing Workspace` 本意是“ME 跟踪全流程非终态稿件的控制台”

真正的问题是：

- `Managing Workspace` 仍然包含 `intake` bucket
- 前端文案没有明确“动作队列”和“跟踪台”的差异
- 用户从结果上会得到“两个页面都在列相同稿件”的体验

这意味着“保留两个页面并继续解释差异”不是一个足够好的终态设计。

### 二、实现层问题

从代码与 handoff 审计可确认，首屏空列表并不是单点 bug，而是多因素叠加：

1. 页面 mount 后立即请求受保护接口  
   `frontend/src/app/(admin)/editor/intake/page.tsx` 与 `frontend/src/components/editor/ManagingWorkspacePanel.tsx` 都在 `useEffect` 中直接请求列表。

2. 鉴权恢复没有统一门控  
   `frontend/src/services/auth.ts` 负责从 Supabase 恢复 session；`frontend/src/components/layout/SiteHeader.tsx` 也在并行调用 `getSession()`。  
   这说明页面请求与 session 恢复并未通过统一 gate 协调。

3. 多层缓存叠加  
   - 组件内 20 秒缓存
   - `frontend/src/services/editor-api/manuscripts.ts` 内的 GET 缓存与 inflight 去重
   - 后端短 TTL 缓存

4. 错误态缺失  
   目前页面在 `catch` 中大多仅 `console.error`，然后关掉 loading。  
   用户最终看到的是“空态”，而不是“请求失败”。

5. mutation 后缓存失效不完整  
   当前若执行 `assignAE`、`submitIntakeRevision` 等动作，只清理了 intake/process/detail 相关缓存，未完整失效 `managingWorkspaceCache`。

## 官方口径校验

通过 Context7 查询官方文档后，本设计采用以下原则：

1. Next.js 16.1.6 App Router 仍优先推荐在 Server Component 做首屏数据获取，再把交互下沉给 Client Component。  
   这说明当前“所有首屏列表都放在 client `useEffect` 中拉取”的做法不是最稳妥模式。

2. Supabase JS 2.58.0 的 `getSession()` / `onAuthStateChange()` 可以提供当前 session 与刷新事件，但这并不等于“页面任意时刻直接抢发 protected fetch”就是稳的。  
   仍需要一个统一的 session-ready 语义，避免多个组件各自并行恢复、并行请求。

本轮不直接把整个页面重构为 Server Component 首屏取数，只是在当前代码结构下引入更稳的门控与错误态；这是风险与收益之间的折中。

## 候选方案

### 方案 A：保留双页面，仅修稳定性

做法：

- 不动信息架构
- 只修错误态、认证门控、缓存失效

优点：

- 改动面小
- 风险低

缺点：

- 产品层重复感仍然存在
- 需要长期维护两个入口与两套文案
- 用户认知负担并未真正下降

### 方案 B：保留两个页面，但把 Managing Workspace 去掉 `intake bucket`

做法：

- `Intake Queue` 保留
- `Managing Workspace` 不再显示 intake 分组
- 两个页面继续并存

优点：

- 比方案 A 更清楚
- 改动中等

缺点：

- 从最终产品形态看，仍然需要用户理解“为什么还有两个页面”
- 入口页面与跟踪页面的分裂仍然存在

### 方案 C：单页收口为唯一主页面（激进版）

做法：

- `Managing Workspace` 成为唯一主页面
- `Intake Queue` 降级为默认 tab / filter / section
- 独立 `/editor/intake` 路由保留过渡期兼容，再跳转或提示跳转
- 同一轮一起修稳定性问题

优点：

- 产品形态最清楚
- 后续只维护一个主工作面
- 用户心智最简单：“ME 进一个页面处理全部在办稿件”

缺点：

- 变更面最大
- 必须同时处理信息架构与稳定性
- 需要更完整的回归测试

## 决策

采用 **方案 C 的受控版本（C'）**。

这里强调“受控”的原因是：

- 不是只靠打 tag 做粗暴回滚
- 而是通过兼容路由、分阶段收口、补全测试来降低风险

换句话说，本轮允许激进的产品收口，但不允许鲁莽的实现方式。

## 设计目标

### 目标 1：让 Managing Workspace 成为 ME 唯一主工作面

用户进入 ME 工作区后，应优先看到一个统一页面，包含：

- `Intake` 默认分组或默认 tab
- `Waiting Author`
- `Technical Follow-up`
- `Academic Pending`
- `Under Review`
- `Revision Follow-up`
- `Decision`
- `Production`

### 目标 2：去除独立 Intake 页面在信息架构中的主入口地位

`/editor/intake` 不再是独立心智中心，而是：

- 过渡期兼容入口，自动跳转到 `Managing Workspace` 对应 filter
- 或提示这是旧入口并引导进入统一页面

### 目标 3：修复首屏稳定性根因

必须同时做到：

- 不再让请求失败伪装成空列表
- 不在 session 未恢复前发 protected fetch
- mutation 后相关 workspace 视图一定刷新

## 目标产品形态

### 一、页面结构

#### 1. Managing Workspace

作为唯一主工作面，职责如下：

- 展示 ME 所有非终态、且需要 ME 跟进的稿件
- 默认视图落在 `Intake`
- 支持搜索、刷新、按分组浏览
- 支持从统一页面进入稿件详情、分配 AE、退回作者、继续跟进后续流程

#### 2. Intake Queue

改为过渡路由，不再承担独立主页面职责：

- 第一阶段：保留路径，页面顶部提示“已迁移至 Managing Workspace”
- 第二阶段：自动跳转到 `/editor/managing-workspace?bucket=intake`

本轮建议先做第一阶段，避免一次性改变用户入口造成困惑。

### 二、分组语义

统一以 `Managing Workspace` 为主读模型，分组语义如下：

- `intake`
  - `status='pre_check'`
  - `pre_check_status in {null, 'intake'}`
- `awaiting_author`
  - `status='revision_before_review'`
- `technical_followup`
  - `status='pre_check'`
  - `pre_check_status='technical'`
- `academic_pending`
  - `status='pre_check'`
  - `pre_check_status='academic'`
- `under_review`
  - `status='under_review'`
- `revision_followup`
  - `status in {'resubmitted', 'minor_revision', 'major_revision'}`
- `decision`
  - `status in {'decision', 'decision_done'}`
- `production`
  - `status in {'approved', 'layout', 'english_editing', 'proofreading'}`

### 三、为什么仍保留 `intake` 作为分组而不是彻底删除

因为单页方案里，`intake` 不再意味着“另一个页面”，而只是统一工作面中的默认工作分组。  
真正要删除的是“第二个独立入口页的主地位”，不是 `intake` 这类业务状态本身。

## 目标实现结构

### 一、后端

#### 1. `get_managing_workspace()` 继续作为主读模型

`backend/app/services/editor_service_precheck_workspace_views.py` 继续承担 ME 主工作面数据读取职责，但需要做两件事：

- 确认 `intake` bucket 是单页模式下的有效默认分组
- 输出足够稳定的 `workspace_bucket`，供前端按统一模型展示

本轮不建议删除后端 `intake` bucket 本身，因为在单页模式下它仍然是默认分组的合法语义。

#### 2. 保留 `get_intake_queue()`，但降级为兼容用途

`backend/app/services/editor_service_precheck_intake.py` 仍保留：

- 用于过渡期旧页面
- 用于兼容现有测试与潜在脚本调用

但它不再是产品主读模型。

### 二、前端

#### 1. `ManagingWorkspacePanel` 升级为真正主页面

需要新增或调整：

- 默认聚焦 `intake` 分组
- 更强的分组导航
- 更清晰的“这是唯一主工作面”文案
- 显式错误态
- session-ready 之前不发请求

#### 2. `Intake Page` 改为过渡容器

`frontend/src/app/(admin)/editor/intake/page.tsx` 改为：

- 解释旧入口已迁移
- 提供按钮进入 `Managing Workspace`
- 或直接复用 `ManagingWorkspacePanel` 并预选 `intake` bucket

推荐本轮采用“复用主页面 + 默认选中 intake bucket”的方式，这样可减少维护两套列表逻辑。

#### 3. 认证门控

需要引入统一 session-ready 模型，而不是让每个组件各自调用 `getSession()` 后立即请求。

可接受的实现方式：

- 在 editor 受保护页面外层加一层 gate hook / wrapper
- gate 完成前显示“正在验证登录态”
- gate 完成后再进入列表请求

### 三、缓存策略

#### 1. 页面级缓存

保留短 TTL 可以接受，但必须满足：

- 失败不写入“空结果”
- 有旧数据时请求失败，继续显示旧数据 + 错误提示
- 无旧数据时请求失败，显示错误态而不是空态

#### 2. API 层缓存

`frontend/src/services/editor-api/manuscripts.ts` 需要统一补齐以下动作对 `managingWorkspaceCache` 的失效：

- `assignAE`
- `submitIntakeRevision`
- `submitTechnicalCheck`
- `revertTechnicalCheck`
- `submitAcademicCheck`

如后续发现还有会改变 ME bucket 的 mutation，也应同步失效。

## UI 设计原则

### 一、先表达“这是主页面”

Managing Workspace 标题区要明确表达：

- 这是 ME 的统一工作台
- intake 只是其中一个默认分组

### 二、错误态和空态必须分离

至少区分三种状态：

- 初始加载中
- 请求失败
- 请求成功但当前筛选下无数据

### 三、兼容入口必须降低误导性

旧 `Intake Queue` 页面必须停止给用户传递“这是另一个主要工作页面”的信号。

## 测试策略

### 一、后端测试

至少覆盖：

- `get_managing_workspace()` 仍能正确输出 `intake` bucket 作为默认分组
- 其他 bucket 不回归
- 旧 intake API 仍只返回 `pre_check/intake`

### 二、前端测试

至少覆盖：

- `ManagingWorkspacePanel` 默认显示 `intake` 分组
- 请求失败时显示错误态而不是空态
- 旧 intake 路由会正确引导到统一工作面

### 三、缓存回归测试

至少覆盖：

- `assignAE` 后 workspace 刷新
- `submitIntakeRevision` 后 workspace 刷新
- 技术检查相关动作后 bucket 变化可见

## 风险与缓解

### 风险 1：单页收口导致用户短期不适应

缓解：

- 保留旧路由兼容
- 页面顶部给出明确迁移提示

### 风险 2：稳定性问题在单页下被放大

缓解：

- 本轮把错误态、session gate、cache invalidation 作为同级目标
- 不允许只做单页 UI 合并

### 风险 3：改动范围较大影响回归

缓解：

- 先后端/读模型确认
- 再前端入口收口
- 最后补缓存与测试
- 每一段单独 commit

## 非目标

本轮不做：

- 彻底移除 `get_intake_queue()` 后端接口
- 全量改造为 Server Component 首屏数据获取
- 重做整个 Editor Dashboard IA
- 同时优化所有 editor 页面认证门控

## 实施建议

推荐按以下顺序落地：

1. 统一页面职责与过渡路由策略
2. 修复 session-ready 与错误态
3. 补齐 cache invalidation
4. 补回归测试
5. 更新文案与文档

## 最终结论

这轮不应继续把 `Intake Queue` 和 `Managing Workspace` 当成两个平级主页面维护。  
更合理的终态是：

- **Managing Workspace = ME 唯一主工作面**
- **Intake = 统一工作面里的默认分组**
- **旧 Intake 页面 = 过渡兼容入口**

同时，本轮必须把首屏稳定性问题一起解决；否则即使产品形态合并了，系统仍然会继续表现出“不稳定、像没数据、必须刷新”的问题。
