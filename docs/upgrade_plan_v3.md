---
title: "ScholarFlow 期刊投稿与审稿系统升级方案（v3.0）"
---

**日期**: 2026-02-10  
**依据**: `docs/original_version` + 当前 UAT 反馈  
**重点修订**: 将前序流程统一为“ME 先技术审查，通过后再分配 AE”，并明确三段决策口径（Pre-check 可选、First Decision 可选、Final Decision 必须）

## 1. 文档目的

本版用于明确 ScholarFlow 的标准稿件处理链路，确保角色分工、状态机和系统实现一致，重点解决以下问题：

1. 前序节点顺序不一致（已统一为 ME 先审后分配 AE）。
2. 大修/小修分流规则在执行层口径不一致。
3. 学术决策分层（Pre-check / First / Final）口径需要统一。

---

## 2. 标准处理流程（新版）

1. **作者投稿**：作者提交稿件与基础元数据。
2. **ME 技术审查**：检查格式完整性、基础合规、文件有效性；不通过则退回作者。
3. **ME 分配 AE**：仅在技术审查通过后执行。
4. **AE 执行入口（技术通过后）**：默认发起外审；也可选送 `Academic Pre-check`（可选，不阻塞主链路）。
5. **审稿人回执**：接受/拒绝/超时；不足则继续邀请。
6. **审稿报告达标**：AE 汇总意见，必要时提交 `First Decision`（可选，主要用于分歧/难判断场景）。
7. **修回流转**：可直接进入小修/大修；小修由 AE 核查后可再决策，大修必须二审。
8. **Final Decision（必须）**：作者提交修回稿后，EIC/Board 做最终接收/拒稿/继续修回判断。
9. **接收后并行**：Production 与 Finance 同时启动。
10. **发布门禁**：需同时满足 `Paid` 与 `Proof Ready`。
11. **正式发布**：公开检索、引用与下载链路生效。

---

## 3. 稿件全生命周期（宏观流程图）

![稿件全生命周期流程（v3）](flow_lifecycle_v3.svg)

---

## 4. 状态机（系统流转约束）

![稿件状态机（v3）](state_manuscript_v3.svg)

> 约束强调：`under_review` 不允许直接拒稿；`Final Decision` 仅允许在作者修回提交后执行（`resubmitted/decision/decision_done`）。
>
> 状态码映射：投稿`submitted`，ME技术审查`me_precheck`，外审中`under_review`，待决策`decision`，小修`revision_minor`，大修`revision_major`，小修重提`resubmitted_minor`，大修重提`resubmitted_major`，接收`approved`，拒稿`rejected`，校对完成`proof_ready`，已支付`paid`，已发布`published`。

---

## 5. 审稿邀请机制（Magic Link）

![审稿人邀请机制](seq_invite_v3.svg)

---

## 6. 角色边界（执行口径）

| 角色 | 主要职责 | 不负责事项 |
| :--- | :--- | :--- |
| Author | 投稿、修回、校对确认 | 学术决策、审稿人管理 |
| ME (Managing Editor) | 投稿入口技术审查、AE 分配、流程监管 | 学术终审 |
| AE (Assistant Editor) | 组织外审、催审、汇总审稿意见、修回跟进 | 最终学术拍板 |
| EIC/Board | 学术 Pre-check、Final Decision（拒稿/修回/接收） | 日常流程操作 |
| Reviewer | 提交同行评审意见（Magic Link） | 系统后台管理 |
| Production | 排版、校对流转、发布前制作准备 | 财务到账确认 |
| Finance | 开票、到账确认、账单状态管理 | 学术意见判断 |

---

## 7. 与原版相比的关键变化

1. **前序顺序修正**：明确“ME 技术审查 -> ME 分配 AE”，杜绝先分配后审查。
2. **Pre-check 定位为可选**：AE 可“直接发起外审”或“送 Academic Pre-check”。
3. **First Decision 定位为可选**：仅在报告冲突/难判断时启用，不强制阻断主流程。
4. **Final Decision 强制化**：必须在作者修回提交后执行，作为审稿流程终结门。
5. **门禁表达清晰**：发布由财务与制作双条件共同放行。
6. **图形标准统一**：本版图示全部采用 `SVG` 矢量图，适配放大打印。

---

## 8. 实施建议（对接当前系统）

1. 将 `/editor/intake` 固化为 ME 入口页面，仅处理技术审查与 AE 分配。
2. 将 `/editor/workspace` 聚焦 AE 的外审执行与修回推进，并提供“发起外审 / 送 Academic / 技术退回”三选一。
3. 将 `/editor/academic` 聚焦 EIC/Board 的学术判断，First Decision 可选记录、Final Decision 强制落在修回后。
4. 发布按钮继续受 Payment Gate + Proof Gate 双重约束。
