# 项目差距分析与行动清单（Todo 版）

**更新日期**: 2026-02-09  
**基线分支**: `main`  
**目的**: 这份文档直接作为执行清单，持续勾选推进。

---

## 1. 当前状态快照（已完成）

- [x] 核心主链路已打通：投稿 -> 预审/外审 -> 终审决策 -> 录用/账单 -> 出版门禁。
- [x] Reviewer 闭环已完成（Invite Accept/Decline + Magic Link + Reviewer Workspace）。
- [x] Final Decision Workspace 已完成（草稿/终稿/附件/审计）。
- [x] 录用后生产协作闭环已完成（Feature 042）：
  - [x] 编辑生产工作间 `/editor/production/[id]`
  - [x] 作者校对页面 `/proofreading/[id]`
  - [x] `production_cycles` / `production_proofreading_responses` / `production_correction_items`
  - [x] 发布门禁与“已核准轮次”绑定
- [x] 最新主干 CI 已恢复为绿色（`ScholarFlow CI` / `Sync to Hugging Face Hub`）。

---

## 2. 差距清单（按优先级）

## P0（下一阶段必须做）

- [x] **GAP-P0-01：预审角色工作流落地（Feature 038）**
  - 结果：已按 `specs/044-precheck-role-hardening/` 完成 044 收敛实现，形成可回归的 ME -> AE -> EIC 闭环。
  - 完成标准：
    - [x] 后端状态流转与 RBAC 全量落地
    - [x] Process/详情页可视化角色队列
    - [x] E2E 覆盖 ME 分配、AE 质检、EIC 初审
  - 验收记录：
    - [x] Backend：`18 passed, 3 skipped`（`test_api_paths` + `test_editor_http_methods` + `test_editor_service` + `test_precheck_flow` + `test_precheck_role_service`）
    - [x] Frontend：Vitest `6 passed` + Playwright `precheck_workflow.spec.ts` `1 passed`

- [x] **GAP-P0-02：Feature 042 云端迁移与真实环境回归**
  - 现状：已交付 Feature 043（Cloud Rollout Regression）作为放行门禁层，补齐 run/check 审计、internal API 与一键脚本。
  - 结果：
    - [x] 新增迁移：`20260209160000_release_validation_runs.sql`（`release_validation_runs` + `release_validation_checks`）
    - [x] 新增内部验收接口：`/api/v1/internal/release-validation/*`（create/list/readiness/regression/finalize/report）
    - [x] 新增放行脚本：`scripts/validate-production-rollout.sh`（dry-run/readiness-only/统一退出码）
    - [x] 新增测试：`test_release_validation_service.py`、`test_release_validation_api.py`，并验证 `15 passed`

- [x] **GAP-P0-03：内部协作增强（Feature 036 增量）**
  - 结果：已完成 045（`045-internal-collaboration-enhancement`）落地，形成“@提及 -> 任务化 -> 逾期筛选”闭环。
  - 完成标准：
    - [x] Notebook 支持 @用户并触发站内通知（提及去重、无效提及拦截）
    - [x] 增加内部 task 字段（负责人、截止时间、状态）+ activity log
    - [x] Process 列表显示 overdue 标识与筛选（`overdue_only`）
  - 验收记录：
    - [x] Backend：`15 passed`（contract + unit + integration，见 045 quickstart）
    - [x] Frontend：Vitest `7 passed` + Playwright `1 passed`

## P1（P0 后立即推进）

- [x] **GAP-P1-01：Finance 页面接入真实 `invoices`（替换演示数据）**
  - 结果：已完成 Feature 046（Finance Real Invoices Sync），`/finance` 已切换为真实账单数据源。
  - 完成标准：
    - [x] 列表真实读取 `invoices`
    - [x] 支持筛选（unpaid/paid/waived）与对账导出
    - [x] 与 `/editor/manuscript/[id]` 的 Mark Paid 行为一致
  - 验收记录：
    - [x] Backend：`8 passed`（contract + unit + integration）
    - [x] Frontend：Vitest `5 passed` + Playwright `1 passed` + lint 通过（仅既有 warning）

- [x] **GAP-P1-02：Portal 学术工具箱补齐（Feature 034）**
  - 结果：已完成文章页结构化引用导出与学科聚合浏览能力，补齐 Scholar 抓取关键元数据。
  - 完成标准：
    - [x] 文章页提供 BibTeX/RIS 导出（`GET /api/v1/manuscripts/articles/{id}/citation.bib|ris` + 前端下载按钮）
    - [x] Subject Collections 可按学科聚合浏览（`GET /api/v1/public/topics` 动态聚合）
    - [x] Scholar/SEO 元数据校验通过（文章页 `citation_pdf_url` 指向公开 `/pdf` 入口）
  - 验收记录：
    - [x] Backend：`tests/unit/test_public_and_citation_api.py` + `tests/unit/test_portal_api.py` 共 `5 passed`
    - [x] Contract：`tests/contract/test_api_paths.py` `1 passed`
    - [x] Frontend：`tests/unit/citation.test.ts` `2 passed` + `next lint` 通过（仅既有 warning）

- [x] **GAP-P1-03：Analytics 管理视角增强（Feature 014 增量）**
  - 结果：已完成管理视角下钻，新增 `/api/v1/analytics/management` + 前端管理洞察区块（效率排行/阶段耗时/SLA 预警）。
  - 完成标准：
    - [x] 编辑个人效率排行（处理量/平均耗时）
    - [x] 阶段耗时分解（预审/外审/终审/生产）
    - [x] 异常预警（超 SLA 稿件）
  - 验收记录：
    - [x] Backend：`tests/test_analytics.py` + `tests/test_analytics_aggregation.py` + `tests/test_analytics_export.py` 共 `31 passed`
    - [x] Frontend：`bun run lint` 通过（仅既有 warning）

- [x] **GAP-P1-04：审稿邀请策略强化（Review Policy Hardening）**
  - 结果：已完成邀请策略硬化（冷却期拦截 + 高权限 override 审计 + due 窗口统一 + 模板变量 + 前端命中原因可视化）。
  - 完成标准：
    - [x] 同一期刊 30 天冷却期（近期被邀 reviewer 灰显不可邀，可由高权限显式 override 并审计）
    - [x] 审稿人同意时可选 `due_date`（默认 +10 天，窗口可配置，超窗不可选）
    - [x] 邀请模板支持变量占位（审稿人名/稿件题目/期刊名/截止时间）
    - [x] Process 与详情页显示邀请策略命中原因（cooldown / conflict / overdue risk）
  - 验收记录：
    - [x] Backend：`tests/unit/test_reviewer_service.py` + `tests/integration/test_editor_invite.py` + `tests/integration/test_reviewer_library.py` 共 `15 passed`
    - [x] Frontend：`src/components/ReviewerAssignModal.test.tsx` `4 passed`
    - [x] Lint：`frontend bun run lint` 通过（仅既有 warning）

- [x] **GAP-P1-05：角色矩阵与期刊作用域 RBAC 收敛**
  - 现状：当前主要角色为 author/reviewer/editor/admin，已能运行但粒度偏粗。
  - 缺口：与对方目标角色体系（publisher / manager editor / SIE / assistant editor / academic editor）仍有距离。
  - 当前推进：已完成完整实现：角色矩阵动作门禁 + journal-scope 隔离 + first/final decision 语义 + 高风险审计字段（before/after/reason/source）+ 前端 capability 显隐 + mocked E2E 回归。
  - 完成标准：
    - [x] 定义角色矩阵（页面、按钮、状态流转、可见字段）并固化到 `specs/*` + 测试用例
    - [x] Journal-scope 权限落地（同角色跨期刊默认隔离）
    - [x] APC / Owner / Final Decision 等高风险操作支持“最小权限 + 审计追踪”
    - [x] 关键接口补齐 RBAC 回归测试（401/403/越权读取/越权写入）

## P2（中期规划）

- [x] **GAP-P2-01：DOI/Crossref 真对接**
  - 结果：已完成真实注册链路收敛（`doi_registrations` + `doi_tasks` + `doi_audit_log`），支持任务消费、失败重试、审计追踪。
  - 完成标准：
    - [x] 注册（`POST /api/v1/doi/register`）可落库并入队
    - [x] 重试（`POST /api/v1/doi/{article_id}/retry`）幂等入队
    - [x] 回执状态可追踪（`GET /api/v1/doi/{article_id}` + `GET /api/v1/doi/tasks*` + `doi_audit_log`）
    - [x] 新增内部消费入口 `POST /api/v1/internal/cron/doi-tasks`（`ADMIN_API_KEY`）

- [x] **GAP-P2-02：查重能力重启（可配置）**
  - 结果：已完成查重异步链路重启（状态查询 + 手动重试 + 报告下载 + 高相似度预警留痕）。
  - 完成标准：
    - [x] 开关保留并可配置（`PLAGIARISM_CHECK_ENABLED` + 阈值/轮询参数）
    - [x] 失败降级（不阻断投稿主链路，落库 `failed` + `error_log`）
    - [x] 报告留痕完整（`plagiarism_reports` 全生命周期状态 + 高相似度审计/通知）

---

## 3. 建议执行顺序（接下来 2 个迭代）

### Iteration 1（本周，先把链路“可上线”）

- [x] 完成 GAP-P0-02：云端迁移 + 真实环境回归（优先最高）
- [x] 完成 GAP-P0-01：预审角色工作流落地（含 E2E + 审计可视化）

### Iteration 2（下周，先把“编辑团队提效”）

- [x] 完成 GAP-P0-03（@mentions + 内部任务 + SLA 预警）
- [x] 完成 GAP-P1-01（Finance 真数据接入）

### Iteration 3（当前建议，先把“产品对标能力”补齐）

- [x] 完成 GAP-P1-02（Portal 学术工具箱：BibTeX/RIS + Subject Collections + Scholar/SEO）
- [x] 完成 GAP-P1-03（Analytics 管理视角增强：效率排行 + 阶段耗时 + SLA 预警）
- [x] 完成 GAP-P1-04（审稿邀请策略：冷却期 + due date + 模板）
- [x] 完成 GAP-P1-05（角色矩阵与 Journal-scope RBAC）

---

## 4. 立即下一步（单一建议）

**当前建议：进入 UAT 回归与上线验收**。  
P0/P1/P2 清单已收敛，下一步建议按角色手册执行端到端冒烟并聚焦线上环境差异（迁移、配置、性能）。

---

## 5. 对方需求归纳（基于 reference1~reference5）

- [x] 端到端主流程：投稿 -> 质检 -> 外审 -> 决策 -> 接收 -> 生产 -> 发布（已具备）
- [x] 审稿流程细节：双通道评语（给作者/给编辑）+ 审稿附件（已具备）
- [x] 多轮审稿与 round 机制（已具备）
- [x] 详情页聚合视图：基础信息 + 文件区 + 状态时间线 + 内部 note（已具备）
- [x] APC/Invoice 与发布门禁联动（已具备）
- [x] 同刊 reviewer 冷却期（1 个月）与可视化拦截（已完成，映射 GAP-P1-04）
- [x] reviewer 同意后 `due_date` 选择与窗口限制（已完成，映射 GAP-P1-04）
- [x] 角色层级细化与按期刊权限隔离（已完成，映射 GAP-P1-05）
- [x] `first decision` 与 `final decision` 的产品语义显式化（已完成，映射 GAP-P1-05）
- [x] APC 锁定与高权限 override 审计（已完成，映射 GAP-P1-05）

---

## 6. 开源架构借鉴结论（OJS + Janeway，非代码复用）

- [x] 已验证可本地参考 OJS 仓库结构（`/tmp/ojs`，仅用于能力对标，不复制实现）。
- [x] 已验证可本地参考 Janeway 仓库结构（`/tmp/janeway`，Django 架构，含 workflow/role 文档）。
- [x] 借鉴原则：抄“能力模型与流程颗粒度”，不抄“语言实现细节与源代码”。
- [x] 输出多标杆对标矩阵：`docs/OSS_ARCHITECTURE_GAP_MATRIX.md`（逐项映射到 ScholarFlow 的 API/页面/测试）。
- [x] 已将 OJS + Janeway 对标结果并入相关 spec（`specs/034-portal-refinement/spec.md`、`specs/037-reviewer-invite-response/spec.md`、`specs/048-role-matrix-journal-scope-rbac/spec.md`），确保缺口项可验收。
