# ScholarFlow 期刊投稿与审稿系统升级方案 (v2.0)

**日期**: 2026-02-05
**受众**: 鲁总 / 业务负责人
**状态**: 规划中

## 1. 项目背景与目标

根据最新的业务需求分析，我们需要将现有的 ScholarFlow 系统从一个基础的投稿系统升级为一个**全流程、商业化、高度自动化**的出版管理平台（类似 MDPI/Frontiers 模式）。

**核心差异点（本次升级重点）：**
1.  **销售/归属权管理（Owner Binding）**：引入“特刊编辑/归属人（Owner）”概念，用于追踪业务员/编辑的业绩（拉稿绩效）。
2.  **学术与行政分离**：明确**内部行政编辑（AE/ME）**负责流程跑腿，**外部学术编辑（主编/编委）**掌握生杀大权（初审与终审）。
3.  **前台与后台分离的审稿流**：审稿人不需要注册繁琐账号，通过“Magic Link（魔术链接）”直接操作，降低门槛。
4.  **出版与财务并行**：录用后立即进入排版，但上线前必须经过**财务门禁**（款项结清）。

---

## 2. 核心业务流程图 (Flowcharts)

### 2.1 稿件全生命周期流程 (宏观视角)

这张图展示了稿件从投稿到上线的完整路径。
*   **双重 Pre-check**：先由 **ME** 完成投稿前期技术/行政审查，随后由 **AE** 跟进执行，最后交由 **学术主编/编委** 进行学术初审。
*   **决策权分离**：AE 负责邀请审稿人、催收报告，但最终的 **录用/拒稿/修回** 决定由 **学术主编** 做出。(特别修正：Under Review 状态下不可直接拒稿，必须先提交至 **Decision** 阶段，再由主编发出拒稿决定。)
*   **出版阶段**：录用后，**财务流程**与**制作流程**并行，最终在“上线”节点汇合。

![稿件全生命周期流程](doc_artifacts/flow_lifecycle.png)

---

## 3. 角色与权限体系 (Role Definition)

系统严格区分“公司内部员工”与“外部合作学者”。

| 角色类别 | 角色名称 | 英文缩写 | 职责描述 |
| :--- | :--- | :--- | :--- |
| **公司高管** | **Publisher** | **Admin** | **出版人/系统总管**。负责整个出版社系统，管理所有期刊与人员权限。 |
| **公司员工** | **Managing Editor** | **ME** | **期刊负责人**。负责新稿件入口审查（技术/行政）与 AE 分配，并监督整体进度。 |
| **公司员工** | **Assistant Editor** | **AE** | **助理编辑/操作主力**。负责已通过入口审查稿件的具体跟进（送审、催审、修回跟进）。 |
| **公司员工/合作** | **Special Issue Editor** | **Owner** | **业务编辑/归属人**。负责“拉人头”（组稿/邀稿），通过此角色追踪**销售业绩**。 |
| **外部学者** | **Editor-in-Chief / Board** | **EIC** | **主编/编委 (教授)**。挂靠的学术专家，不负责具体操作，但拥有**Pre-check (学术把关)** 和 **Final Decision (终审)** 的最高决定权。 |
| **外部学者** | **Reviewer** | - | **审稿专家**。通过 Magic Link 进行同行评审，无需登录后台。 |
| **公司员工** | **Production** | - | **制作编辑**。负责排版、润色、处理校对。 |

---

## 4. 关键功能模块设计 (UML Diagrams)

### 4.1 审稿人邀请机制 (Sequence Diagram)

**痛点解决**：以前需要审稿人注册账号才能审稿，转化率低。现在改为“先入库，后邀请，链接直达”。

![审稿人邀请机制](doc_artifacts/seq_invite.png)

### 4.2 稿件状态机 (State Machine)

这是系统流转的核心逻辑，清晰展示了 Revision 的分支逻辑以及 Production 阶段的并行状态。(修正注：严禁从 Under Review 直接跳转至 Rejected。所有拒稿流程必须经过 Decision 节点。)

![稿件状态机](doc_artifacts/state_manuscript.png)

---

## 5. 下一步实施计划 (Implementation Roadmap)

基于目前的项目进度（已完成基础框架和部分编辑端重构），建议接下来的开发分为三个 Sprint：

### 阶段一：质检与归属体系 (Sprint 1 - High Priority)
*   **目标**：完善稿件进入系统后的第一步管理，建立“行政分配 -> 学术初审”的流转机制。
*   **功能点**：
    1.  **Pre-check 页面开发**：
        *   ME 视图：新稿件入口审查（技术/行政）+ 分配 AE。
        *   AE 视图：跟进执行（修回跟踪/外审推进）。
        *   **EIC 视图**：学术初审（Pass/Reject）。
    2.  **Owner 绑定与详情页增强**：
        *   **元数据**：绑定 `Owner` (Special Issue Editor) 与 `AE`。
        *   **文件中心 (File Hub)**：统一管理 Cover Letter, 查重报告, 审稿附件等（提供下载，无需预览）。
        *   **内部协作 (Notebook)**：内部员工专用的评论区（带时间戳与人员信息），用于 AE 与 ME/EIC 沟通。
        *   **审计日志 (Audit Log)**：记录所有状态变更与操作历史。
    3.  **APC 设置**：确认版面费金额。

        > **界面示意图**：Editor Dashboard (Frontier Style)
        > ![Editor Dashboard Mockup](doc_artifacts/mock_dashboard.png)

        > **界面示意图**：Internal Manuscript Detail (File Hub, Notebook, Audit Log)
        > ![Manuscript Detail Mockup](doc_artifacts/mock_detail.png)

### 阶段二：审稿人库与 Magic Link (Sprint 2 - Core Value)
*   **目标**：降低审稿门槛，建立私有专家库。
*   **功能点**：
    1.  **Reviewer Library**：独立的审稿人管理页面（增删改查）。
    2.  **邀请弹窗重构**：从库中搜索 -> 发送邮件。
    3.  **Token 机制与工作台开发**：
        *   **PDF 预览**：审稿人无需下载即可在线阅读。
        *   **双向评论 (Dual Comments)**：区分“致作者 (Visible to Author)”和“致编辑 (Confidential to Editor)”的评论框。
        *   **隔离机制**：审稿人互不可见，只能看到自己的对话。

        > **界面示意图**：Reviewer Workspace (PDF Preview + Dual Comments)
        > ![Reviewer Landing Mockup](doc_artifacts/mock_reviewer.png)

    4.  **文件预览**：审稿人落地页需集成 PDF 预览功能。

### 阶段三：财务门禁与出版流 (Sprint 3 - Revenue Safety)
*   **目标**：确保“先付钱，后上线”，同时不阻塞制作进度。
*   **功能点**：
    1.  **Invoice 生成器**：基于录用稿件信息，自动生成 PDF 账单。
    2.  **并行工作流**：录用后状态自动变更为 `Approved / In Production`，同时触发财务通知。
    3.  **作者校对 (Proofreading)**：开发在线或邮件触发的校对确认环节。
    4.  **出版门禁逻辑**：在“Publish”按钮增加**双重校验**（Invoice Paid + Author Confirmed），缺一不可。

---

**附：技术术语解释**
*   **APC (Article Processing Charge)**: 文章处理费，开源期刊的主要收入来源。
*   **Magic Link**: 一种免密码登录技术，用户点击邮件链接即可获得临时权限。
*   **QC (Quality Check)**: 稿件初筛/质检。
*   **Production Gate**: 生产门禁，指系统强制要求满足特定条件（如付款）才能进入下一阶段。
