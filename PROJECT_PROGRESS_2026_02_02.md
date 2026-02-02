# ScholarFlow 项目全景进展报告

**日期**: 2026-02-02
**基准**: 基于 Specs 001-021 及当前代码库状态
**版本**: Constitution v1.0.0

---

## 1. 执行摘要 (Executive Summary)

ScholarFlow 目前已从基础的原型阶段过渡到**成熟的学术出版管理系统**。我们已经完成了核心投稿、审稿、编辑决策闭环的开发，并建立了完善的自动化测试、环境隔离和超级管理员治理体系。

当前处于 **Phase 4: 深度优化与集成验证阶段**，重点在于稿件修订（Revision）流程的端到端验证以及系统的稳健性加固。

---

## 2. 详细功能模块进展 (Module Breakdown)

### A. 核心工作流与角色系统 (Core Workflow & Roles)
*涵盖 Specs: 001, 005, 007, 008, 018, 020*

我们已经构建了完整的学术出版全链路：
1.  **投稿 (Author)**: 支持 PDF 上传、元数据填写、自动查重预检。
2.  **编辑指挥中心 (Editor Command Center)** (Spec 008):
    *   实现了编辑仪表盘，支持按状态筛选稿件。
    *   支持“初审拒稿”、“指派审稿人”、“最终录用”等决策操作。
3.  **审稿人工作台 (Reviewer Workspace)** (Spec 007):
    *   审稿邀请的接受/拒绝。
    *   在线评分表单与审稿意见提交。
4.  **修订循环 (Revision Cycle)** (Spec 020 - **最近完成**):
    *   实现了 `Major Revision` / `Minor Revision` 的状态流转。
    *   作者提交修改稿（v2, v3...）及“给审稿人的回复”。
    *   **最新突破**: 完成了修订流程的集成测试 (Spec 021)。
5.  **用户与安全 (User Profile)** (Spec 018):
    *   基于 Supabase Auth 的鉴权。
    *   完整的个人资料页（学术机构、研究方向 `text[]`）。
    *   安全中心（密码更新、会话管理）。

### B. 系统治理与运维 (Governance & Operations)
*涵盖 Specs: 011, 017, 019, 006, 009*

1.  **超级管理员后台 (Super Admin)** (Spec 017):
    *   基于 Shadcn UI 的独立管理界面。
    *   用户管理（封禁、角色提升）、系统配置查看。
2.  **通知中心 (Notification System)** (Spec 011):
    *   双通道通知：站内信（实时红点）+ 邮件通知（SMTP/Jinja2 模板）。
    *   支持由数据库触发器或后端事件驱动的消息推送。
3.  **环境治理 (Environment)** (Spec 019):
    *   实现了 **UAT/Staging 环境隔离**。
    *   前端具备环境感知能力（Staging Banner），数据库配置独立。
4.  **质量保证 (QA Suite)** (Spec 006, 009):
    *   建立了 Backend (>80%) 和 Frontend (>70%) 的覆盖率硬性指标。
    *   自动化测试脚本 (`run-all-tests.sh`) 集成了 Unit, Integration, E2E 测试。

### C. 智能化与增强功能 (Intelligence & Advanced Features)
*涵盖 Specs: 002, 012, 014, 015, 013*

1.  **本地 AI 匹配 (Local AI Matchmaker)** (Spec 012):
    *   后端集成了 `scikit-learn`。
    *   实现了基于 TF-IDF 的**审稿人推荐算法**（根据稿件摘要匹配审稿人研究兴趣）。
2.  **内容与查重 (Content & Plagiarism)** (Spec 002, 004):
    *   PDF 解析与文本提取基础。
    *   查重机制的预留接口与基础实现。
3.  **数据分析与索引 (Analytics & Indexing)** (Spec 014, 015):
    *   初步的数据埋点与统计仪表盘结构。

### D. UI/UX 标准化 (UI Standardization)
*涵盖 Specs: 010, 003*

*   **技术栈统一**: 全面采用 Next.js App Router + Tailwind CSS。
*   **组件库**: 深度集成 `Shadcn UI`，确保了从按钮到对话框的视觉一致性。
*   **TypeScript 严格模式**: 刚刚确立并强制开启，消除了类型隐患。

---

## 3. 技术架构现状 (Technical Architecture)

| 层级 | 技术选型 | 当前状态 |
| :--- | :--- | :--- |
| **前端** | Next.js 14, TypeScript (Strict), React 18, Tailwind, Shadcn UI | **成熟**。组件复用率高，严格遵循类型安全。 |
| **后端** | Python 3.14, FastAPI, Pydantic v2 | **成熟**。API 契约稳定，迁移至 Pydantic v2 完成。 |
| **数据库** | Supabase (PostgreSQL 15+) | **稳定**。Schema 版本化管理，含 RLS 安全策略。 |
| **测试** | Playwright (E2E), Pytest (Backend), Vitest (Frontend) | **完善**。已覆盖核心路径，正在补全边界测试。 |
| **部署** | Docker, GitHub Actions (CI/CD) | **就绪**。支持自动化构建与测试运行。 |

---

## 4. 下一步计划 (Roadmap Forward)

根据 Spec 序列的完成情况，我们接下来的短期目标是：

1.  **加固 Spec 021**: 确保修订流程（Revision Flow）在各种边缘情况（如作者中途撤稿、审稿人超时）下都能通过自动化测试。
2.  **文档债清理**: 随着功能快速迭代，需要同步更新 `/docs` 目录下的 API 文档，确保与代码一致。
3.  **性能优化**: 针对 Spec 012 的 AI 匹配算法，随着数据量增加，可能需要引入缓存或更高效的向量检索（Vector Search）。

---

*报告生成时间：2026-02-02*
*生成工具：Gemini CLI Agent*
