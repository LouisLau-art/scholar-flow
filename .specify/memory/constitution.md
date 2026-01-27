<!--
Sync Impact Report
- Version change: 1.6.0 → 1.7.0
- List of modified principles:
  - 细化原则 VIII: 开发环境与包管理规范 (用户权限, paru 操作, 包清理, pip 强制安装)
- Added sections: 身份与凭证安全说明
- Removed sections: N/A
- Templates requiring updates:
  - ✅ updated: .specify/templates/tasks-template.md
- Follow-up TODOs: N/A
-->

# ScholarFlow Constitution

## 一、 核心治理原则 (Core Governance)

### I. 规格驱动开发 (SD - Spec-Driven)
所有功能开发前必须有完整的 `spec.md` 和 `plan.md`。严禁在未经验证的情况下直接编码。

### II. 测试先行与增量交付 (TI - Test-First)
功能必须拆解为可独立测试的 User Stories。测试（若要求）必须在实现前编写并失败。每个 Story 必须是可验证的 MVP 增量。

### III. 阶段门控开发 (PG - Phase-Gated)
严格遵守：研究 (Phase 0) -> 设计 (Phase 1) -> 基础搭建 (Phase 2) -> 功能实现 (Phase 3+) 的顺序。严禁越级。

### IV. 架构简约与显性逻辑 (AS - Simple & Explicit)
最小化复杂度。禁止“黑盒”逻辑或魔法函数。核心业务门禁（权限、财务）必须在代码中清晰可见。

### V. 可观测性与追踪 (OT - Observability)
所有 User Story 必须包含异常处理、结构化日志。任务必须通过 ID 与 User Story 保持端到端追踪。

## 二、 开发哲学与优先级 (Development Philosophy)
- **MVP 优先**: 严禁引入超前设计（如未要求的微服务）。
- **可读性 > 性能**: 代码是写给 AI 和人类看的，逻辑直观是最高准则。
- **效率至上**: 优先使用成熟第三方库，严禁重复造轮子。

## 三、 架构规范与数据流 (Architecture & Data Flow)
- **前后端契约**: 严格遵守 OpenAPI (Swagger) 规范。
- **API 封装**: 前端必须统一封装 API 类，禁止在组件中散写请求。
- **Next.js 规范**: 数据请求优先在 Server Components 完成，仅交互部分使用 `'use client'`。
- **状态管理**: 优先使用 URL 状态或原生 `useState`，减少 Redux 等样板代码。

## 四、 错误处理与容错 (Error Handling & Resilience)
- **全局防御**: 前端统一 Error Boundary，后端统一异常捕获中间件。
- **优雅降级**: 算法响应慢时必须有 Loading 态或占位，严禁页面卡死。
- **财务幂等性**: 涉及确认到账、生成账单等操作，必须在数据库层面做唯一性校验。

## 五、 UI/UX 视觉标准 (Visual Standards)
- **Frontiers 风格**: 全宽布局、卡片容器（4px圆角、轻阴影）、品牌蓝 CTA。
- **原子化**: 严格基于 `Shadcn/UI` 和 `Tailwind CSS`。禁止行内样式。
- **排版与配色**: 大标题衬线体（Serif），正文使用系统无衬线体（Sans）。配色锁定为深蓝色调 (`slate-900`) 及灰、白、蓝。

## 六、 技术栈版本约束 (Version Constraints)
- **Frontend**: Next.js 14.2.x (App Router), React 18.x, Tailwind 3.4.x.
- **Backend**: Python 3.11+, FastAPI 0.115+, Pydantic v2.
- **Infrastructure**: Supabase (PostgreSQL, Auth, Storage).
- **SDK**: Supabase-js v2.x / Supabase-py v2.x.

## 七、 AI 协作准则 (AI Collaboration)
- **文档同步**: 变更代码前必须确认并同步更新设计文档（Data Model, Spec）。
- **任务原子化**: 每次实现仅处理一个小项，单次修改文件严禁超过 5 个。
- **中文注释**: 关键逻辑（算法、Token 验证）必须包含中文注释。

## 八、 开发环境与包管理规范 (Environment & PKG)
- **开发平台**: 本项目开发环境锁定为 **Arch Linux**。
- **包管理优先级**: 
  1. 优先使用系统包管理器 **`pacman`** 或 **`paru`**。
  2. 若系统包与语言包（pip/npm）冲突，应优先保留系统包，并可清理对应的语言包。
- **用户权限**: 
  - `pacman` 操作可使用 root。
  - `paru` 严禁新建用户，必须切换至已有用户 **`louis`** (密码: `18931976`) 执行。
- **Python 强制安装**: 若 `pip` 全局安装被 OS 拒绝，必须使用 **`--break-system-packages`** 参数。
- **Docker 规范**: 必须确保配置了国内镜像源。

## 九、 持续集成与存档 (CI & Savepoints)

- **即时存档**: 每一个原子化任务（如完成一个 Issue）完成后，必须立即执行 `git push` 同步至 GitHub。

- **存档意义**: 此举作为项目的“存档点”，确保在发生意外情况时能及时回滚并减少损失。



## 十、 全栈切片与交付定义 (Full-Stack Slice & DoD)



- **拒绝隐形逻辑**: 后端任务完成的标准**必须**包含 API Router 注册，且在 `/docs` (Swagger) 可见。



- **显性路由原则**: API 路由严禁过度依赖嵌套前缀。必须在方法装饰器上定义清晰、完整的路径（如 `/manuscripts/search`），以防测试歧义。



- **拒绝孤岛页面**: 前端任务完成的标准**必须**包含从主页或导航栏的可达入口。



- **骨架先行**: 项目启动的 Phase 1 **必须**显式包含 Landing Page 和 Navigation 的搭建。







## 十一、 质量保障与交互标准 (QA & UX Standards)



- **自动化测试刚性要求**: 任何新功能的交付（DoD）**必须**包含自动化测试用例（后端 Pytest，前端 Vitest）。



- **原生 SDK 优先**: 在 Supabase 集成中，优先使用原生 `supabase-js` 或 `supabase-py`，严禁使用不稳定的已弃用辅助库。



- **交互反馈统一**: 全站禁止使用浏览器原生 `alert()`。必须统一使用 **Shadcn/Sonner** 的 Toast 组件进行状态反馈。







## Governance



本项目章程是最高准则。



**Version**: 1.9.0 | **Ratified**: 2026-01-27 | **Last Amended**: 2026-01-27




