% ScholarFlow UAT 测试手册（交付版）
% ScholarFlow
% 生成日期：2026-02-13

> 适用环境：UAT（Vercel + Hugging Face + Supabase Cloud）
>
> 本手册面向 UAT 测试方，覆盖 Public / Author / Reviewer / Editor / Admin 的关键业务闭环。

\newpage

# 1. 测试目标

- 验证核心业务闭环可用：投稿 -> 审稿 -> 决策 -> 账单 -> 发布 -> 公开访问。
- 验证权限边界正确：未发表稿件、角色可见范围、Reviewer 免登录 scope。
- 验证关键门禁正确：Payment Gate（未付款禁止发布），以及必要的状态机约束。
- 验证关键页面无阻断级错误：白屏、死链、500、无法操作。

# 2. 测试环境

- 前端（UAT）：`https://scholar-flow-q1yw.vercel.app/`
- 后端（UAT API）：`https://louisshawn-scholarflow-api.hf.space`

注意：如遇 `ERR_BLOCKED_BY_CLIENT` 等问题，请先关闭浏览器“强拦截”插件再复测一次。

# 3. 账号与数据准备

## 3.1 账号准备（建议）

本轮 UAT 验收以“把流程讲清楚并可演示”为目标。以下为可用账号（统一密码：`12345678`），可直接提供给鲁总用于验收。

| 角色 | 邮箱 | 显示名（参考） |
| --- | --- | --- |
| author | louis@ccnu.edu.cn | authorLouis |
| managing_editor | LouisShawn@proton.me | CSME |
| reviewer | reviewer@qq.com | 邓梓豪 |
| assistant_editor | new_editor@university.edu | EditorJohn Doe |
| production_editor | LouisShawn@163.com | Louis Shawn |
| editor_in_chief | test_editor@qq.com | ME&EIC |
| admin | louis.shawn@qq.com | admin Louis |

备注：

- 上述账号用于 UAT 环境（Vercel + HF Space + Supabase Cloud）。
- 若出现“登录成功但看不到数据”，优先确认该角色的 journal scope / 分配关系是否已配置。

## 3.2 测试数据准备（建议 3 篇稿件）

- `M1`：未发表（例如 `under_review` / `revision_requested`）
- `M2`：已录用未付费（`approved` + invoice `unpaid`）
- `M3`：已发布（`published`）

# 4. 推荐执行顺序

1. 先跑第 5 章（冒烟 15-20 分钟）。
2. 冒烟通过后，按第 6 章分角色跑全量。
3. 每轮回归，至少跑第 7 章“重点回归点”。
4. 最后集中跑第 8 章“性能与体验专项”。

# 5. 冒烟测试（15-20 分钟）

## SMOKE-01 登录与导航

- [ ] 分别用 author / reviewer / editor / admin 登录成功
- [ ] 顶部导航、Dashboard、角色切换可用
- [ ] 无明显白屏、无限 loading、403/500 弹错

## SMOKE-02 Editor Process 列表

步骤：

1. 使用 editor 登录。
2. 打开 `/editor/process`。
3. 在列表中执行一次筛选（可以空条件）。

预期：

- [ ] 页面可加载并显示表格
- [ ] 按 `q`、`journal`、`status`、`overdue_only` 等筛选可用
- [ ] 点击稿件可进入详情页
- [ ] 排序符合预期：最近 `Updated` 的稿件应排在更上方

## SMOKE-02B 角色可见范围（如 UAT 覆盖到对应角色）

- [ ] `assistant_editor`：`/editor/process` 仅显示“分配给我”的稿件
- [ ] `managing_editor`：`/editor/intake` 与 `/editor/process` 仅显示其分管 Journal 范围
- [ ] `admin`：可查看全局稿件（不受 journal scope 限制）

## SMOKE-03 Author 详情访问控制

- [ ] author 可查看自己未发表稿件详情（仅展示允许范围内信息）
- [ ] author 不能查看他人未发表稿件（应 403/Not found）
- [ ] 已发表稿件公开页可匿名访问

## SMOKE-04 投稿上传与解析

- [ ] `/submit` 上传 PDF 成功
- [ ] 不出现“长期转圈卡死”
- [ ] AI 解析失败时可回退手填，不阻断提交

## SMOKE-05 支付与发布门禁（Payment Gate）

- [ ] 未 paid 的稿件不能 publish（门禁生效且提示清晰）
- [ ] `Mark Paid` 后可继续发布流程

# 6. 全量 UAT（按角色）

# 6.1 Public（匿名）

- [ ] 首页可访问，导航可达 `Journals` / `Topics` / `About`
- [ ] 公开文章列表只显示 `published`
- [ ] 死链检查：不存在明显 404（含页脚/导航历史链接）

# 6.2 Author 路径

## A-01 新投稿

- [ ] 填写标题/摘要/作者信息并上传稿件
- [ ] 提交后状态进入 `pre_check`
- [ ] Dashboard 能看到最新状态和更新时间

## A-02 修回提交

- [ ] 当稿件进入 `revision_requested` 时，作者可进入修回页 `/submit-revision/{id}`
- [ ] 上传修回稿 + Response Letter 成功
- [ ] 状态变更为 `resubmitted`

## A-03 账单与已发表文章

- [ ] 录用后可下载 invoice PDF（若已生成）
- [ ] 已发表文章详情页可查看公开信息与 PDF

# 6.3 Reviewer（Magic Link）

## R-01 邀请响应

- [ ] 访问 `/review/invite?token=...` 能正确落到 assignment 页面
- [ ] Accept/Decline 状态更新正确，重复点击幂等

## R-02 Reviewer Workspace

- [ ] `/reviewer/workspace/[id]` 正常加载（左 PDF + 右 Action Panel）
- [ ] 可填写意见、上传附件、提交
- [ ] 提交后进入只读态（不能重复编辑关键字段）

# 6.4 Editor / Managing Editor / Assistant Editor / EIC

## E-01 Pre-check 三阶段（如 UAT 覆盖到对应角色）

- [ ] `/editor/intake`：ME 分配 AE
- [ ] `/editor/workspace`：AE 提交 technical check
- [ ] `/editor/academic`：EIC 提交 academic check
- [ ] 违规流转被阻止（例如 `pre_check` 直接 `reject`）

## E-02 Process & Detail

- [ ] `/editor/process` 列表加载、筛选、跳转详情正常
- [ ] `/editor/manuscript/[id]` 文件区、内部评论、任务面板正常
- [ ] 任务逾期聚合与 `overdue_only` 一致

## E-03 Reviewer 指派策略

- [ ] 可从 Reviewer Library 选择审稿人
- [ ] 冷却期命中时有提示；高权限可 override 并记录 reason

## E-04 Decision Workspace

- [ ] `/editor/decision/[id]` 可查看上下文、编辑决策信、上传附件
- [ ] 提交 decision 成功并可追踪审计记录（如页面/日志可见）

## E-05 Production & Publish

- [ ] `/editor/production/[id]` 可创建 cycle、上传 galley、审批
- [ ] Payment Gate 按预期阻断/放行发布

# 6.5 Admin

## AD-01 用户与角色

- [ ] `/admin/users` 仅 admin 可进入
- [ ] 用户角色修改保存成功（如实现多角色，验证多选）

## AD-02 Analytics 管理视角

- [ ] `/editor/analytics` 管理洞察区块可显示
- [ ] 编辑效率、阶段耗时、SLA 预警相关数据/接口返回正常

## AD-03 Release Validation（可选，通常由平台方执行）

- [ ] 能创建 run、执行 readiness/regression/finalize
- [ ] 报告可读，结果能区分 `go` / `no-go`

## AD-04 Journal Management 与 Scope（如 UAT 覆盖到该功能）

- [ ] `/admin/journals` 可查看期刊列表
- [ ] 创建新期刊成功（title + slug 唯一）
- [ ] 编辑期刊信息并保存成功
- [ ] 停用/重新启用期刊（`is_active` 生效）
- [ ] （可选）配置 scope 后，Process/Intake 列表可见范围立即变化

# 7. 重点回归点（每轮必测建议）

- [ ] Editor Process 列表稳定：`/editor/process` 打开与筛选无阻断
- [ ] Author 访问未发表稿件详情不误报 “Article not found”
- [ ] Reviewer Magic Link 全流程可走通（invite -> workspace -> submit）
- [ ] Payment Gate：未支付不可发布，支付后可发布
- [ ] 公开页只展示已发布文章（匿名可访问）

# 8. 性能与体验专项（本轮重点）

## P-01 页面切换与首屏

- [ ] Dashboard → Process → Manuscript Detail → Decision 的切换耗时可接受
- [ ] 不出现每次都长时间转圈（记录慢页面 URL 与大致耗时）

## P-02 表格加载

- [ ] `/editor/process` 常见筛选下首屏加载稳定
- [ ] 快速切换筛选不出现明显卡顿、抖动或重复请求风暴

## P-03 上传链路

- [ ] 不同大小 PDF 上传都不会“无响应”
- [ ] 失败能给出可理解错误提示，不出现静默失败

# 9. 缺陷记录模板（每条必填）

- 标题：[模块] 简述
- 环境：UAT（浏览器 + OS）
- 账号角色：author/reviewer/editor/admin
- 页面 URL：
- 复现步骤（1/2/3）：
- 实际结果：
- 期望结果：
- 证据：截图 / 控制台 / Network /（如有）Sentry Issue ID
- 严重级别：`S0/S1/S2/S3`

严重级别建议：

- `S0`：阻断主流程（无法投稿/无法审稿提交/无法决策/无法发布）
- `S1`：主流程可绕过但风险高（可能导致数据错误/权限泄露/财务门禁绕过）
- `S2`：功能可用但体验或边界异常
- `S3`：文案/UI 细节问题

# 10. UAT 放行标准（建议）

- [ ] 冒烟 5 项全部通过
- [ ] 四角色主链路（Author/Reviewer/Editor/Admin）全部打通
- [ ] Payment Gate / 状态机门禁无绕过
- [ ] 无 `S0/S1` 未修复缺陷

# 附录 A：常见问题速查（按错误关键字）

## A.1 Schema 漂移 / 列缺失

现象示例：

- `column manuscripts.pre_check_status does not exist`
- `Could not find table public.internal_comments in schema cache`

建议处理（平台方执行）：

1. 确认云端 migration 已同步并刷新 schema cache。
2. 执行后复测对应页面/接口。

## A.2 投稿卡在解析/一直转圈

- 先在浏览器 Network 确认卡住的是哪个请求（上传/解析/提交）。
- 核对请求是否进入后端日志；若进入但长时间无响应，记录请求时间、稿件 ID、错误信息用于定位。
- 用小 PDF（例如 <10MB）重试，排除超大文件或异常 PDF 的偶发问题。

# 附录 B：关联文档

- 详细场景版：`docs/UAT_SCENARIOS.md`
- 可执行清单版：`UAT_TEST_CHECKLIST.md`
