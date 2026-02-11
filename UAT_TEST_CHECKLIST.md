# ScholarFlow UAT 测试清单（可执行版）

更新时间：2026-02-10  
适用环境：UAT（Vercel + Hugging Face + Supabase Cloud）

---

## 1. 结论先说

- 现在是做“UAT驱动的代码质量审查”的合适时机。  
- 建议顺序：先按本清单完成 UAT 主链路，再做系统级 code review（这样可以避免审查与环境问题互相干扰）。

---

## 2. 测试前准备（必须）

### 2.1 环境与地址

- 前端：`https://scholar-flow-q1yw.vercel.app`
- 后端：`https://louisshawn-scholarflow-api.hf.space`

### 2.2 账号准备

- `admin`（兼具 editor 权限）
- `editor`（非 admin）
- `reviewer`
- `author`

### 2.3 迁移前置检查（关键）

至少确认以下迁移已在云端执行：

- `supabase/migrations/20260206150000_add_precheck_fields.sql`
- `supabase/migrations/20260209190000_internal_collaboration_mentions_tasks.sql`
- `supabase/migrations/20260209160000_release_validation_runs.sql`
- `supabase/migrations/20260210193000_doi_registration_manuscript_fk.sql`

若不确定是否已执行：优先在 Supabase CLI 跑 `supabase db push --linked`，不要靠猜。

### 2.4 发布门禁（readiness）检查

```bash
ADMIN_API_KEY=<your_admin_key> ./scripts/validate-production-rollout.sh \
  --base-url https://louisshawn-scholarflow-api.hf.space \
  --readiness-only \
  --manuscript-id <任意UAT稿件UUID>
```

通过标准：输出 `readiness-only result: GO`。  
注意：脚本参数是 `--base-url`，不是 `--api-base`。

---

## 3. 冒烟测试（15-20 分钟）

### SMOKE-01 登录与导航

- [ ] 分别用 author / reviewer / editor / admin 登录成功
- [ ] 顶部导航、Dashboard、角色切换可用
- [ ] 无明显白屏、无限 loading、403/500 弹错

### SMOKE-02 Editor Process 列表

- [ ] 打开 `/editor/process` 成功显示表格
- [ ] 按 `q`、`journal`、`assign editor`、`status`、`overdue` 筛选可用
- [ ] 点击稿件可进入详情页
- [ ] 排序规则符合预期：最近 `Updated` 的稿件应排在最上方

### SMOKE-02B 角色可见范围（Process/Intake）

- [ ] 使用 `assistant_editor` 登录：`/editor/process` 仅显示“分配给我”的稿件
- [ ] 使用 `managing_editor` 登录：`/editor/intake` 与 `/editor/process` 仅显示其分管 Journal 范围
- [ ] 使用 `admin` 登录：可查看全局稿件（不受 journal scope 限制）

### SMOKE-03 Author 详情访问控制

- [ ] author 可查看自己未发表稿件详情（仅允许范围内信息）
- [ ] author 不能查看他人未发表稿件（应 403/Not found）
- [ ] 已发表稿件公开页可匿名访问

### SMOKE-04 投稿上传与解析

- [ ] `/submit` 上传 PDF 成功
- [ ] 不出现“长期转圈卡死”
- [ ] AI 解析失败时有可回退手填，不阻断提交

### SMOKE-05 支付与发布门禁

- [ ] 未 paid 的稿件不能 publish（Payment Gate 生效）
- [ ] `Mark Paid` 后可继续发布流程

---

## 4. 全量 UAT（按角色）

## 4.1 Author 路径

### A-01 新投稿

- [ ] 填写标题/摘要/作者信息并上传稿件
- [ ] 提交后状态进入 `pre_check`
- [ ] Dashboard 能看到最新状态和更新时间

### A-02 修回提交

- [ ] 当稿件进入 `revision_requested` 时，作者可进入修回页
- [ ] 上传修回稿 + Response Letter 成功
- [ ] 状态变更为 `resubmitted`

### A-03 账单与已发表文章

- [ ] 录用后可下载 invoice PDF（若已生成）
- [ ] 已发表文章详情页可查看公开信息与 PDF

---

## 4.2 Reviewer 路径

### R-01 邀请响应

- [ ] 访问 `/review/invite?token=...` 能正确落到 assignment 页面
- [ ] Accept/Decline 状态更新正确，重复点击幂等

### R-02 Reviewer Workspace

- [ ] `/reviewer/workspace/[id]` 正常加载（左 PDF + 右 Action Panel）
- [ ] 可填写双通道意见、上传附件、提交
- [ ] 提交后进入只读态

---

## 4.3 Editor 路径

### E-01 Pre-check 三阶段

- [ ] `/editor/intake`：ME 分配 AE
- [ ] `/editor/workspace`：AE 提交 technical check
- [ ] `/editor/academic`：EIC 提交 academic check
- [ ] 违规流转（例如 pre_check 直接 reject）被阻止

### E-02 Process & Detail

- [ ] `/editor/process` 列表加载、筛选、跳转详情正常
- [ ] `/editor/manuscript/[id]`：文件区、内部评论、任务面板正常
- [ ] 任务逾期聚合与 overdue_only 一致

### E-03 Reviewer 指派策略

- [ ] 可从 Reviewer Library 选择审稿人
- [ ] 冷却期命中时有提示；高权限可 override 并记录 reason

### E-04 Decision Workspace

- [ ] `/editor/decision/[id]` 可查看上下文、编辑决策信、上传附件
- [ ] 提交 decision 成功并有审计记录

### E-05 Production & Publish

- [ ] `/editor/production/[id]` 可创建 cycle、上传 galley、审批
- [ ] Payment Gate 按预期阻断/放行发布

---

## 4.4 Admin 路径

### AD-01 用户与角色

- [ ] User Management 页面可加载列表
- [ ] 编辑角色保存成功（若多角色已实现，验证多选）

### AD-02 Analytics 管理视角

- [ ] `/editor/analytics` 管理洞察区块可显示
- [ ] 编辑效率、阶段耗时、SLA 预警接口返回正常

### AD-03 Release Validation

- [ ] 能创建 run、执行 readiness/regression/finalize
- [ ] 报告可读，结果能区分 `go` / `no-go`

### AD-04 Journal Management 与 Scope 绑定

- [ ] 打开 `/admin/journals`，可查看期刊列表
- [ ] 创建新期刊成功（title + slug 唯一）
- [ ] 可编辑期刊信息并保存成功
- [ ] 可停用/重新启用期刊（is_active 生效）
- [ ] `supabase db push --linked` 后，确认 `journals.is_active` / `journals.updated_at` 字段存在
- [ ] （可选）在 `journal_role_scopes` 配置 ME/EIC 的 journal 范围后，Process/Intake 列表可见范围立即变化

---

## 5. 性能与体验专项（本轮重点）

### P-01 页面切换与首屏体验

- [ ] Dashboard → Process → Manuscript Detail → Decision 的切换可接受
- [ ] 不出现每次都长时间转圈（记录慢页面的 URL 与耗时）

### P-02 表格加载

- [ ] `/editor/process` 在常见筛选下首屏加载稳定
- [ ] 快速切换筛选不出现明显卡顿、抖动或重复请求风暴

### P-03 上传链路

- [ ] 大小不同的 PDF 上传都不会“无响应”
- [ ] 失败能给出可理解错误提示，不出现静默失败

---

## 6. 缺陷记录模板（每条必填）

- 标题：
- 环境：UAT（浏览器 + OS）
- 账号角色：
- 页面 URL：
- 复现步骤（1/2/3）：
- 实际结果：
- 期望结果：
- 证据：截图 / 控制台 / Network / Sentry Issue ID
- 严重级别：`S0/S1/S2/S3`

---

## 7. UAT 放行标准（建议）

- [ ] 冒烟 5 项全部通过
- [ ] 四角色主链路（Author/Reviewer/Editor/Admin）全部打通
- [ ] Payment Gate / 状态机门禁无绕过
- [ ] 无 `S0/S1` 未修复缺陷
- [ ] release validation 最终结果为 `GO`

---

## 8. 测试执行顺序（推荐）

1. 先跑第 2 节（准备 + readiness）  
2. 再跑第 3 节（冒烟）  
3. 通过后按第 4 节角色顺序跑全量  
4. 最后集中跑第 5 节性能专项并出缺陷清单

---

## 9. 关联文档

- 详细场景版：`docs/UAT_SCENARIOS.md`
- 上线验收脚本：`scripts/validate-production-rollout.sh`
- GAP 总计划：`docs/GAP_ANALYSIS_AND_ACTION_PLAN.md`
