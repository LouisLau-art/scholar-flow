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

- [ ] **GAP-P0-01：预审角色工作流落地（Feature 038）**
  - 现状：`specs/038-precheck-role-workflow/` 已有规格，但落地实现不足。
  - 缺口：ME -> AE -> EIC 的队列、责任切换、时间戳审计、前端入口还不完整。
  - 完成标准：
    - [ ] 后端状态流转与 RBAC 全量落地
    - [ ] Process/详情页可视化角色队列
    - [ ] E2E 覆盖 ME 分配、AE 质检、EIC 初审

- [x] **GAP-P0-02：Feature 042 云端迁移与真实环境回归**
  - 现状：已交付 Feature 043（Cloud Rollout Regression）作为放行门禁层，补齐 run/check 审计、internal API 与一键脚本。
  - 结果：
    - [x] 新增迁移：`20260209160000_release_validation_runs.sql`（`release_validation_runs` + `release_validation_checks`）
    - [x] 新增内部验收接口：`/api/v1/internal/release-validation/*`（create/list/readiness/regression/finalize/report）
    - [x] 新增放行脚本：`scripts/validate-production-rollout.sh`（dry-run/readiness-only/统一退出码）
    - [x] 新增测试：`test_release_validation_service.py`、`test_release_validation_api.py`，并验证 `15 passed`

- [ ] **GAP-P0-03：内部协作增强（Feature 036 增量）**
  - 现状：已有 Internal Notebook + Audit Timeline。
  - 缺口：缺少 @mentions、可分配内部任务、SLA 逾期预警。
  - 完成标准：
    - [ ] Notebook 支持 @用户并触发站内通知
    - [ ] 增加内部 task 字段（负责人、截止时间、状态）
    - [ ] Process 列表显示 overdue 标识与筛选

## P1（P0 后立即推进）

- [ ] **GAP-P1-01：Finance 页面接入真实 `invoices`（替换演示数据）**
  - 现状：`/finance` 为 demo，不与云端同步。
  - 完成标准：
    - [ ] 列表真实读取 `invoices`
    - [ ] 支持筛选（unpaid/paid/waived）与对账导出
    - [ ] 与 `/editor/manuscript/[id]` 的 Mark Paid 行为一致

- [ ] **GAP-P1-02：Portal 学术工具箱补齐（Feature 034）**
  - 现状：文章页有基础引用按钮，但无 BibTeX/RIS 下载与专题索引闭环。
  - 完成标准：
    - [ ] 文章页提供 BibTeX/RIS 导出
    - [ ] Subject Collections 可按学科聚合浏览
    - [ ] Scholar/SEO 元数据校验通过

- [ ] **GAP-P1-03：Analytics 管理视角增强（Feature 014 增量）**
  - 现状：仪表盘已可用（KPI/趋势/导出）。
  - 缺口：缺少“按编辑/按阶段”的下钻分析与 SLA 视图。
  - 完成标准：
    - [ ] 编辑个人效率排行（处理量/平均耗时）
    - [ ] 阶段耗时分解（预审/外审/终审/生产）
    - [ ] 异常预警（超 SLA 稿件）

## P2（中期规划）

- [ ] **GAP-P2-01：DOI/Crossref 真对接**
  - 现状：仍以 mock/占位为主。
  - 完成标准：注册、重试、回执状态可追踪。

- [ ] **GAP-P2-02：查重能力重启（可配置）**
  - 现状：默认关闭 `PLAGIARISM_CHECK_ENABLED=0`。
  - 完成标准：开关、失败降级、报告留痕完整。

---

## 3. 建议执行顺序（接下来 2 个迭代）

### Iteration 1（本周，先把链路“可上线”）

- [x] 完成 GAP-P0-02：云端迁移 + 真实环境回归（优先最高）
- [ ] 启动并交付 GAP-P0-01 第一版（Feature 038 后端 + 基础 UI）

### Iteration 2（下周，先把“编辑团队提效”）

- [ ] 完成 GAP-P0-01 剩余项（E2E + 审计完善）
- [ ] 完成 GAP-P0-03（@mentions + 内部任务 + SLA 预警）
- [ ] 启动 GAP-P1-01（Finance 真数据接入）

---

## 4. 立即下一步（单一建议）

**建议立刻开工：`GAP-P0-01`（预审角色工作流落地）**。  
原因：GAP-P0-02 已完成并补齐发布门禁，当前主路径瓶颈转移到 ME→AE→EIC 预审协作效率与审计完整性。
