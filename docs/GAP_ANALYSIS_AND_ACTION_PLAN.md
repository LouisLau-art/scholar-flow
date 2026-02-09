# 项目差距分析与下一步行动计划书 (Gap Analysis & Action Plan)

**日期**: 2026-02-06  
**基于**: 鲁总（业务方）反馈、当前开发进度 (Feature 041 Finished)、系统架构现状

---

## 1. 总体进度概览 (Status Overview)

经过最近一轮冲刺（Feature 038 角色工作流、041 最终决策工作间、037/039/040 审稿人闭环），ScholarFlow 已经从一个“通用型 CMS”成功转型为**“符合学术出版规范的专业投审稿系统”**。

- **核心闭环**: 投递 -> 预审(ME/AE/EIC) -> 外审(Invite/Review) -> 终审(Decision) -> 录用/账单 -> 出版门禁。这一主干链路已全部打通。
- **关键合规**: 状态机已硬化（拒绝越级拒稿），审计日志已全覆盖，角色权限已隔离。

---

## 2. 差距分析 (Gap Analysis)

这里对照鲁总（甲方）的业务要求与学术出版标准，列出目前系统的缺失项：

| 维度 | 甲方/业务要求 | 当前现状 | 差距 (Gap) | 优先级 |
| :--- | :--- | :--- | :--- | :--- |
| **出版生产** | **“录用后要有排版、校对的协作流”**<br>不仅是状态变更，要有文件流转。 | 仅有 `layout`, `proofreading` 等状态枚举，缺乏专门的协作 UI。 | **缺失出版协作工作间**：排版师上传清样、作者在线校对确认的入口缺失。 | **High** |
| **内部协作** | **“编辑部内部要能高效沟通”**<br>不要发微信/邮件，系统内要有留痕。 | 详情页有 Note，但缺乏通知机制；无法 @ 其他编辑。 | **缺失内部通知与指派**：Note 仅是“备忘录”，不是“沟通工具”。缺乏任务逾期预警。 | **Medium** |
| **数据决策** | **“我要看编辑处理得快不快”**<br>宏观管理视角。 | 只有简单的“稿件列表”，没有“时效统计图表”。 | **缺失效能看板**：无法直观看到“平均初审用时”、“外审周转率”等关键 KPI。 | **Medium** |
| **学术门户** | **“这得像个正经的期刊网站”**<br>展示要专业，方便引用。 | 基础的文章展示，缺乏学术分类和引用工具。 | **门户功能单薄**：缺少 Subject Area 分类索引，缺少 BibTeX/RIS 导出。 | **Low** |
| **支付/财务** | **“财务要能对账”**<br>不仅是下载 PDF，要有流水记录。 | 已有 Invoice PDF 和 Payment Gate。 | **财务模块较轻**：目前混在编辑详情页中，缺乏独立的财务对账列表（Finance Dashboard）。 | **Low** |

---

## 3. 下一步行动计划 (Action Plan)

根据上述差距，建议接下来的开发按照 **"生产闭环 -> 内部提效 -> 数据管理"** 的顺序进行。

### 🚀 第一阶段：生产协作闭环 (Production Pipeline)
**目标**: 解决稿件“录用后”如何变成“最终 PDF”的问题，填补出版环节的 UI 空白。

*   **Task 1 (Feature 031 - Production Workflow)**:
    *   **排版端 (Layout Desk)**: 为“排版编辑”角色提供专用视图，上传 Galley Proof (清样 PDF)。
    *   **校对端 (Author Proofreading)**: 作者收到校对通知，在线查看清样，提交 Correction List（或确认无误）。
    *   **版本管理**: 区分 `Author Version` (原稿) 和 `Production Version` (排版稿)，最终发布时强制使用 Production Version。

### 🛠 第二阶段：内部协作增强 (Internal Collaboration)
**目标**: 让系统成为编辑部日常工作的核心平台，减少对外部沟通工具的依赖。

*   **Task 2 (Feature 036 - Enhanced Collaboration)**:
    *   **提及功能 (@Mentions)**: 在 Internal Comments 中支持 @同事，触发系统/邮件通知。
    *   **任务指派 (Task Assignment)**: 除了指派稿件 Owner，支持指派细分任务（如“请核对图片版权”）。
    *   **逾期红点**: 对超过 SLA（如预审 > 3天）的稿件在列表中高亮预警。

### 📊 第三阶段：效能看板 (Efficiency Dashboard)
**目标**: 满足管理层（鲁总）对团队效率的监控需求。

*   **Task 3 (Feature 014 - Analytics Dashboard)**:
    *   **时效统计**: 计算并展示 TTR (Time to Review), TTD (Time to Decision), TTP (Time to Publication)。
    *   **工作量统计**: 统计每位编辑处理的稿件数量、拒稿率。
    *   **漏斗分析**: 展示稿件在各阶段的流失情况。

### 🎨 第四阶段：门户与体验精修 (Portal Polish)
**目标**: 提升对外品牌形象。

*   **Task 4 (Feature 034 - Portal Refinement)**:
    *   **学术工具箱**: 增加 "Cite this article" (BibTeX/EndNote/RIS)。
    *   **分类浏览**: 完善 Subject Collections 页面。
    *   **SEO 优化**: 针对 Google Scholar 的 Meta Tags 优化。

---

## 4. 立即执行建议 (Immediate Next Step)

鉴于 **Feature 041 (终审决策)** 刚刚完成，稿件已经可以顺利流转到 `approved` (录用) 状态。**目前的断点在于录用后如何生成最终出版物**。

**强烈建议立即启动：Feature 031 (Production Pipeline / 出版流水线)**。
这将彻底打通从“录用”到“上线”的最后一公里，实现全流程的 100% 闭环。
