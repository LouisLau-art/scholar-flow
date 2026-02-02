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

### II. 测试驱动开发 (Test-First & Coverage)
严格的测试覆盖率要求（后端 >80%，前端 >70%，核心逻辑 100%）。遵循测试金字塔（E2E -> Integration -> Unit）。新功能必须包含测试。

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

## Development Workflow

- **Contribution**: Use `gh` CLI for issues/PRs. Update blog/profile upon completion.
- **Doc Sync**: Any change to environment assumptions or core rules must be reflected in all three context files (`GEMINI.md`, `CLAUDE.md`, `AGENTS.md`).

## Governance

Constitution supersedes all other practices. Amendments require documentation and version bump. All PRs and reviews must verify compliance with these principles.

**Version**: 1.0.0 | **Ratified**: 2026-02-02 | **Last Amended**: 2026-02-02