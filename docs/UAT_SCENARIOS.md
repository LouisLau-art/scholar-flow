# ScholarFlow UAT 手册（2026-02-09）

本文档用于 UAT 阶段的人工验收，覆盖 Public / Author / Reviewer / Editor / Admin 的关键业务闭环。

## 1. 测试目标

- 验证核心投稿流程在 UAT 环境可用。
- 验证权限边界正确（未发表稿件、角色访问、审稿免登录）。
- 验证发布门禁正确（Payment Gate / Production 流程）。
- 验证关键页面无阻断级错误（500、白屏、死链）。

## 2. 测试环境

- 前端（UAT）：`https://scholar-flow-q1yw.vercel.app/`
- 后端（UAT API）：`https://louisshawn-scholarflow-api.hf.space`
- 日期基线：`2026-02-09`

执行前请确认：

1. UAT 环境可正常登录。
2. Supabase 云端 migration 已同步（至少包含 workflow 与 process list 相关字段）。
3. 浏览器禁用“强拦截”插件后再复测一次（`ERR_BLOCKED_BY_CLIENT` 常由插件引起，不一定是系统问题）。

### 2.1 5 分钟前置检查（每轮回归前先做）

1. 环境变量检查（本地）  
   `./scripts/sync-platform-env.sh --env-file deploy/platform.env --dry-run`
2. 发布门禁检查（UAT API）  
   `scripts/validate-production-rollout.sh --api-base https://louisshawn-scholarflow-api.hf.space --readiness-only`
3. 关键迁移已落库（至少以下几项）：
   - `supabase/migrations/20260206150000_add_precheck_fields.sql`
   - `supabase/migrations/20260209190000_internal_collaboration_mentions_tasks.sql`
   - `supabase/migrations/20260210193000_doi_registration_manuscript_fk.sql`
4. 如出现 PGRST 列/表缺失，执行迁移后补一条：  
   `select pg_notify('pgrst', 'reload schema');`

## 3. 账号与数据准备

建议至少准备以下账号：

1. `admin` 账号（含 `admin` 角色）
2. `editor` 账号（含 `editor` 或细分编辑角色）
3. `author` 账号（普通作者）
4. `reviewer` 账号（用于 Magic Link 流程）

建议准备 3 篇稿件：

1. `M1`：未发表（例如 `under_review` / `revision_requested`）
2. `M2`：已录用未付费（`approved` + invoice `unpaid`）
3. `M3`：已发布（`published`）

## 4. 10~15 分钟冒烟清单（先跑）

### UAT-SMOKE-01 登录与 Dashboard

步骤：

1. 用 `author` 登录，打开 `/dashboard`。
2. 用 `editor` 登录，打开 `/dashboard?tab=editor`。

预期：

1. 页面加载成功，无白屏。
2. 角色 tab 与账号角色一致。

### UAT-SMOKE-02 Editor Process 列表

步骤：

1. 打开 `/editor/process` 或 Dashboard 内 Editor Command Center。
2. 点击 `Search`（可带空条件）。

预期：

1. 接口 `/api/v1/editor/manuscripts/process` 返回 200。
2. 列表展示正常，无 `Failed to fetch manuscripts process`。

### UAT-SMOKE-03 Author 未发表稿件详情权限

步骤：

1. `author` 打开自己的未发表稿件详情：`/articles/{M1}`。

预期：

1. 能打开页面（不应出现 “Article not found”）。
2. 仅展示有限信息：当前状态、最近动态时间等。
3. 不暴露内部审稿细节与内部人员信息。

### UAT-SMOKE-04 Payment Gate

步骤：

1. 对 `M2` 尝试发布（invoice 仍 `unpaid`）。

预期：

1. 发布被拦截并有明确提示。
2. `Mark Paid` 后可继续发布。

### UAT-SMOKE-05 Published 公开可见

步骤：

1. 退出登录或用匿名访问 `M3` 对应公开页。

预期：

1. 已发布文章可公开访问。
2. PDF 预览走后端签名 URL 接口，能正常打开。

## 5. 全量验收（按角色）

## 5.1 Public（匿名）

用例：

1. 首页可访问，导航可达 `Journals` / `Topics` / `About`。
2. 公开文章列表只显示 `published`。
3. 死链检查：不存在明显 404（例如历史 `/contact` 链接）。

验收标准：

1. 无阻断级 404/500。
2. 公私数据边界正确。

## 5.2 Author

用例：

1. 新投稿（含 PDF）可成功提交。
2. Dashboard 中可见自己的稿件状态变化。
3. 未发表稿件详情页可打开，并且仅展示受限信息。
4. 收到修回后可进入 `/submit-revision/{id}` 提交修订。
5. 稿件 `approved` 后可下载 invoice。

验收标准：

1. 作者看得到自己的流程状态，但看不到内部敏感字段。
2. 修回流程闭环无阻断。

## 5.3 Reviewer（Magic Link）

用例：

1. 打开 `/review/invite?token=...`。
2. Middleware 交换 token 后跳转 assignment 页。
3. 进入 reviewer workspace，填写意见并上传附件。
4. 提交后页面变为只读，不能重复编辑关键字段。

验收标准：

1. 全流程无需常规登录。
2. scope 校验严格，不能访问其他 assignment。

## 5.4 Editor / Managing Editor / Assistant Editor / EIC

用例：

1. Process 列表过滤：`q`、`status`、`journal`、`overdue_only`。
2. Quick Pre-check：只允许 `approve` / `revision`（不应直接 `reject`）。
3. 外审阶段若要拒稿，应先进入 decision 阶段再执行。
4. 决策面板可提交 `accept/reject/revision`（遵守状态机约束）。
5. Reviewer 指派、冷却覆盖（有理由）可用。

验收标准：

1. 状态机约束与产品规则一致。
2. 操作后列表与详情状态同步更新。

## 5.5 Admin

用例：

1. `/admin/users` 仅 admin 可进入。
2. 用户角色修改与审计日志可用。
3. `Mark Paid` 与发布门禁链路可执行。
4. `/admin/sentry-test` 可触发监控自测（仅测试环境使用）。

验收标准：

1. 权限边界正确。
2. 财务门禁与发布链路可追踪。

## 6. 重点回归点（近期高风险）

每轮 UAT 建议必测：

1. `GET /api/v1/editor/manuscripts/process` 不因 schema 漂移报 500。
2. Author 访问未发表稿件详情不再误报 `Article not found`。
3. Footer/导航不再出现 `/contact` 404。
4. Reviewer Magic Link 全流程可走通。
5. Payment Gate：未支付不可发布，支付后可发布。

## 6.1 常见问题速查（按错误关键字）

1. `column manuscripts.pre_check_status does not exist`  
   处理：
   - 执行 `supabase/migrations/20260206150000_add_precheck_fields.sql`
   - 执行 `select pg_notify('pgrst', 'reload schema');`
   - 复测 `GET /api/v1/editor/manuscripts/process`
2. `Could not find table public.internal_comments in schema cache`  
   处理：
   - 执行 `supabase/migrations/20260209190000_internal_collaboration_mentions_tasks.sql`
   - 执行 `select pg_notify('pgrst', 'reload schema');`
   - 复测 `GET /api/v1/editor/manuscripts/{id}/comments`
3. 作者投稿卡在 AI 解析（前端一直转圈）  
   处理：
   - 浏览器 Network 确认卡住的是哪个接口（通常是上传后的解析请求）
   - 查看 HF 运行日志中该请求是否进入后端
   - 用小 PDF（<10MB）重试，排除超大文件/异常 PDF
   - 若请求进入后端但长时间无响应，优先记录请求时间、manuscript_id、Sentry issue id 交由后端排查（避免前端无限等待）
4. 只看到 HF 日志首行 `{"message":"ScholarFlow API is running","docs":"/docs"}`  
   说明：
   - 这是启动探活日志，不代表后续无请求。
   - 需要在 Space Runtime Logs 中按时间刷新查看请求日志；若依然没有请求日志，先检查 `NEXT_PUBLIC_API_URL` 是否正确指向 HF Space。

## 7. 缺陷记录模板

提交缺陷时至少包含：

1. 标题：`[模块] 简述`
2. 环境：UAT URL、浏览器、时间（含时区）
3. 账号角色：author/reviewer/editor/admin
4. 重现步骤：1..N
5. 实际结果
6. 预期结果
7. 证据：截图、Network 请求、控制台报错、Sentry Issue 链接
8. 严重级别：`P0/P1/P2/P3`

严重级别建议：

1. `P0`：阻断主流程（无法投稿/无法决策/无法发布）
2. `P1`：主流程可绕过但风险高
3. `P2`：功能可用但体验或边界异常
4. `P3`：文案/UI 细节问题

## 8. UAT 通过标准（建议）

1. 冒烟用例全部通过。
2. `P0 = 0`。
3. `P1` 有明确修复计划与日期。
4. 核心闭环可演示：投稿 -> 审稿 -> 决策 -> 账单 -> 发布 -> 公开访问。
