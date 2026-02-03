<!--
Sync Impact Report:
- Version Change: Template -> 1.0.0
- Modified Principles: Replaced all placeholders with ScholarFlow specific principles.
- Added Sections: Core Principles (Glue Coding, Test-First, Security, Sync & Commit, Env & Tooling), Tech Stack, Workflow, Governance.
- Templates requiring updates: None (Generic references in templates are valid).
- Follow-up TODOs: None.
-->
# ScholarFlow Constitution

## Core Principles

### I. 胶水编程 (Glue Coding)
核心理念是复用成熟开源组件。凡是能不写的就不写，优先复制使用经过社区检验的代码 (Copy & Paste)。尽量不修改原仓库代码，将其作为黑盒使用。自定义代码只负责组合、调用、封装和适配。

### II. 测试与效率 (Test-First, Risk-Based & Coverage)
我们坚持“可回归、可验证”的工程质量，但在日常开发中采用**分层/风险驱动**策略提升效率，避免每次改动都跑全量测试。

- **覆盖率底线不变**：后端 >80%，前端 >70%，关键业务逻辑 100%。
- **测试金字塔不变**：E2E -> Integration -> Unit。
- **新功能必须有测试**：可以同 PR 提交（不强制每次先写完所有全量测试才开始实现），但合并前必须可回归。

#### 推荐分层（提速默认方案）
- **Tier 1（开发中，秒级/分钟级）**：只跑“相关/改动附近”的单测或单文件集成测试；必要时用 `-o addopts=` 跳过全局覆盖率门槛做快速回归。
- **Tier 2（提 PR 前）**：跑后端 unit + 相关 integration + 前端 unit（Vitest），确保该 PR 的核心路径稳定。
- **Tier 3（合并前/CI）**：跑全量（含覆盖率门槛与必要 E2E），例如 `./scripts/run-all-tests.sh`；主干永远保持绿。

### III. 安全优先 (Security First)
所有敏感操作必须鉴权。绝不允许未认证访问用户数据。使用 Supabase JWT 验证。设计阶段即考虑安全（Design Security）。

### IV. 持续同步与提交 (Continuous Sync & Commit)
必须及时提交代码至 GitHub，避免大量未提交的更改。必须时刻保持 `GEMINI.md`, `CLAUDE.md`, `AGENTS.md` 三个上下文文档的同步和统一，确保不同 Agent 获取的环境和规则信息一致。

### V. 环境与工具规范 (Environment & Tooling)
遵循 Arch Linux 包管理优先级 (`pacman` > `paru` > `pip`/`npm`)。文档查询优先使用 `context7` 工具。始终使用中文交流。

## Technology Stack & Constraints

- **Frontend**: TypeScript (Strict Mode), Next.js (App Router), Tailwind CSS, Shadcn UI.
- **Backend**: Python, FastAPI, Pydantic.
- **Database/Auth**: Supabase (PostgreSQL).
- **Environment Assumptions**: Cloud Supabase as default.
- **AI 解析（重要事实）**：
  - **PDF 文本提取是本地库**（`pdfplumber`，仅前几页 + 字符截断）。
  - **元数据抽取是本地解析**：`backend/app/core/ai_engine.py` 优先使用 PDF 版面信息（字号/位置）+ 轻量规则/正则提取 title/abstract/authors（无 HTTP、无远程大模型依赖；可用 `PDF_LAYOUT_MAX_PAGES` / `PDF_LAYOUT_MAX_LINES` 调整版面扫描范围）。
  - **成本/耗时约束**：严禁在上传链路引入远程大模型网络调用；必须截断页数与字符数，保证上传响应可预测。
- **日志（可观测性）**：`./start.sh` 必须同时满足“终端实时可见 + 文件持久化”，默认输出到 `logs/backend.log` 与 `logs/frontend.log`（最新别名）。
- **AI 推荐模型缓存（性能）**：Matchmaking（审稿人推荐）使用 `sentence-transformers` 本地 CPU 推理；首次启动可能需要下载模型，必须启用本地缓存（`HF_HOME` / `SENTENCE_TRANSFORMERS_HOME`）。项目默认通过 `./start.sh` 设置 `HF_ENDPOINT=https://hf-mirror.com`（可覆盖）。
- **MVP 状态机与财务门禁（强约束）**：
  - Reject 必须进入终态 `status='rejected'`（禁止使用历史遗留的 `revision_required`）。
  - Revision 必须进入 `status='revision_requested'`（等待作者修回）；作者提交修订后进入 `resubmitted`。
  - Accept 必须进入 `approved` 并写入 `invoices`；Publish 必须做 Payment Gate：`amount>0` 且 `status!=paid` 则禁止发布。
  - MVP 允许人工确认到账：`POST /api/v1/editor/invoices/confirm` 将 invoice 标记为 `paid`。
  - 云端若存在旧数据 `status='revision_required'`，需执行 `supabase/migrations/20260203120000_status_cleanup.sql` 完成数据纠正。

## Development Workflow

- **单人开发提速（默认模式）**：本项目当前为“单人 + 单机 + 单目录”开发，默认不走 PR / review / auto-merge 流程；直接在工作分支小步提交并 `git push` 同步到 GitHub 作为备份与回滚点。
- **PR（可选）**：仅在需要多人协作、外部审查、或重大高风险改动时才使用 PR；否则视为不必要开销。
- **Doc Sync**：任何“环境假设/核心规则/提速策略”的变更，必须同步更新 `GEMINI.md`、`CLAUDE.md`、`AGENTS.md` 三个上下文文件。

## Governance

Constitution supersedes all other practices. Amendments require documentation and version bump. 若使用 PR 流程，则 PR 必须验证符合本宪法原则。

**Version**: 1.1.0 | **Ratified**: 2026-02-02 | **Last Amended**: 2026-02-02
