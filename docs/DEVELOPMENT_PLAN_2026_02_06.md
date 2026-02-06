# ScholarFlow 阶段性总结与后续开发计划 (2026-02-06)

## 1. 项目现状综述
目前 ScholarFlow 已完成从“通用编辑器管理”向“角色驱动的专业学术工作流”的转型。核心链路（投递 -> 预审 -> 外审 -> 录用/出版）已打通，且严格遵循了鲁总关于“状态机硬化”和“角色隔离”的业务反馈。

---

## 2. 已完成部分 (Completed)

### A. 预审角色工作流 (Feature 038) - **核心交付**
- **ME (Managing Editor) 入口**: 实现了 Intake Queue。只有 ME 能进行初步行政审查并指派给特定的 AE。
- **AE (Assistant Editor) 执行**: 实现了 Technical Check 工作空间。AE 负责技术质检，完成后推送到 EIC 队列。
- **EIC (Editor-in-Chief) 决策**: 实现了 Academic Pre-check。EIC 拥有学术否决权或送审权，且实现了“预审不直接拒稿”的门禁。
- **状态机硬化**: 强制限制 `pre_check` -> `minor_revision` (请求修回) 或 `under_review` (送审) 或 `decision` (进入决策阶段)。

### B. 审稿人端闭环 (Feature 037, 039, 040)
- **免登录审稿 (Magic Link)**: 实现了基于 JWT + httpOnly Cookie 的免登录访问，解决了审稿人注册成本高的问题。
- **沉浸式工作间**: 实现了左侧 PDF 预览 + 右侧双通道意见（对作者/对编辑）+ 附件上传的沉浸式布局。
- **邀请响应机制**: 支持“先看摘要再决定接受/拒绝”，并补齐了邀请生命周期的时间轴记录。

### C. 财务与出版门禁 (Feature 024, 026)
- **自动化账单**: 实现了录用后自动生成 Invoice PDF 并持久化到 Storage。
- **发布门禁**: 实现了 Payment Gate（未支付禁止发布）和 Production Gate（未上传终稿禁止发布，可选）。
- **人工确认**: 支持编辑手动 `Mark Paid` 以处理线下汇款。

### D. 系统基础支撑 (Feature 027, 028, 032)
- **审计日志**: `status_transition_logs` 记录了每一次状态变更的 actor、时间戳和 comment。
- **Sentry 监控**: 全栈接入错误监控，遵循“零崩溃启动”和“隐私保护”原则。
- **Process List 增强**: 实现了支持多条件过滤和 URL 驱动的流程列表，具备 Quick Pre-check 快操作。

---

## 3. 鲁总核心反馈落实清单 (Feedback Fulfillment)
| 反馈要点 | 落实状态 | 实现细节 |
| :--- | :--- | :--- |
| **状态机收紧** | ✅ 已完成 | `pre_check/under_review` 无法直接跳 `rejected`，必须过 `decision` 阶段。 |
| **Quick Pre-check 简化** | ✅ 已完成 | 去掉 `reject` 选项，仅保留 `approve` / `revision`；`revision` 必填意见。 |
| **Analytics 登录态** | ✅ 已修复 | 统一复用 Browser Client，修复了导出 CSV/Excel 时的交互 Bug。 |
| **详情页布局对齐** | ✅ 已完成 | 重构为双栏布局，左侧信息流，右侧流程操作与审计时间线。 |
| **分角色队列** | ✅ 已完成 | ME/AE/EIC 拥有各自独立的待办视图，互不干扰。 |

---

## 4. 接下来应完善的部分 (To-be Implemented)

### 第一阶段：决策工作间强化 (Decision Phase Hardening) - **高优先级**
- **目标**: 解决 EIC 在外审结束后如何高效做出最终裁决。
- **功能点**:
    - **汇总报告视图**: 在 `/editor/manuscript/[id]` 中，需要一个专门的“审稿汇总卡片”，并排对比所有审稿人的打分和意见。
    - **决策草稿箱**: EIC 在做出 Accept/Reject/Revision 决定时，系统应自动根据审稿意见生成一份“致作者信”草稿，允许 EIC 修改。
    - **强制意见补齐**: 录用或拒稿时，必须要求 EIC 关联至少一条内部审核备注。

### 第二阶段：出版流水线细化 (Production Pipeline)
- **目标**: 将“录用后”到“上线前”的行政协作流程从 UI 上补全。
- **功能点**:
    - **Layout/Editing/Proofreading 子状态**: 目前这三个状态在后端已定义，但前端缺乏对应的“角色指派”和“文件流转”（如：发送给排版师 -> 排版师上传排版稿 -> 发送给作者校对）。
    - **最终版本确认**: 实现作者对 Proofreading 版本的线上确认（One-click Confirm）。

### 第三阶段：内部协作与通知增强 (Collaboration & Notification)
- **目标**: 提高编辑部内部效率。
- **功能点**:
    - **内部 @ 提醒**: 在稿件详情页的 Notebook（Internal Comments）中支持 @ 其他编辑，并触发邮件/站内通知。
    - **逾期预警**: 对外审超过 14 天、预审超过 3 天未动的稿件在 Process 列表中标红。

### 第四阶段：门户精修 (Portal Refinement)
- **目标**: 提升学术形象。
- **功能点**:
    - **分类检索**: 实现按学科分类（Subject Areas）浏览已发表文章。
    - **学术引用格式**: 在文章详情页提供 BibTeX / RIS 导出按钮。

---

## 5. 开发建议 (Action Plan)
建议接下来的迭代顺序为：
1.  **US1: 最终决策工作间 (Final Decision UI)** - 完善外审后的关口。
2.  **US2: 出版协作流 (Production Collaboration)** - 解决排版和校对的线下沟通线上化。
3.  **US3: 效能看板 (Efficiency Dashboard)** - 满足鲁总对管理效率的监控需求。
