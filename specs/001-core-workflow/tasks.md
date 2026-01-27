---
description: "ScholarFlow 核心工作流任务列表 (v1.6.0 合宪修订版)"
---

# Tasks: ScholarFlow Core Workflow

**Input**: Design documents from `/specs/001-core-workflow/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

---

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 优先使用 `pacman` 安装环境依赖，AUR 包切换至用户 `louis` 执行 `paru`，初始化 Next.js 14.2 项目 (`frontend/`)
- [x] T002 优先使用 `pacman` 安装 Python 3.11，缺失项使用 `paru` (用户 `louis`) 或 `pip --break-system-packages` 安装，初始化 FastAPI 项目 (`backend/`)
- [x] T003 [P] 配置 Linting (ESLint, Ruff) 与 Formatting 工具
- [x] **CP01** [存档点] 执行 `git push` 同步 Phase 1 变更至 GitHub

---

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T004 Setup Supabase project, database schema per `data-model.md`
- [x] T005 实现财务操作幂等性约束（唯一性校验与状态锁）
- [x] T006 Configure Supabase Storage bucket `manuscripts` (及国内 Docker 镜像校验)
- [x] T007 [P] 初始化审稿人库基础数据
- [x] T008 [P] Define core Pydantic v2 models (**含中文注释**)
- [x] T009 [P] Define core TypeScript interfaces
- [x] T010 开发前端统一 API 封装类与 Supabase Client 实例
- [x] T011 实现后端基础异常捕获中间件与结构化日志模块
- [x] **CP02** [存档点] 执行 `git push` 同步 Phase 2 变更至 GitHub

---

## Phase 3: User Story 1 - 作者投稿与 AI 辅助解析 (Priority: P1)

- [x] T012 [P] [US1] Implement PDF extraction (**含中文注释**)
- [x] T013 [P] [US1] Implement AI parsing (**含中文注释**)
- [x] T014 [US1] Create manuscript upload API endpoint
- [x] T015 [P] [US1] 开发投稿页面（Server Components 优先，`slate-900` 配色）
- [x] T016 [US1] Implement frontend submission form with AI fallback logic
- [x] **CP03** [存档点] 完成 US1 Issue 后立即 `git push` 存档

---

## Phase 4: User Story 2 - 编辑质检与 KPI 归属 (Priority: P2)

- [x] T017 [P] [US2] Create editor dashboard management page
- [x] T018 [US2] Implement quality check API and "Return for Revision" logic
- [x] T019 [US2] 开发质检对话框与 KPI 归属选择组件
- [x] T020 [US2] 开发编辑 KPI 统计看板
- [x] **CP04** [存档点] 完成 US2 Issue 后立即 `git push` 存档

---

## Phase 5: User Story 3 - 审稿人免登录预览与评价 (Priority: P3)

- [x] T021 [P] [US3] 实现安全 Token 生成与验证逻辑 (**含中文注释**)
- [x] T022 [US3] Create reviewer landing page (衬线体标题，`slate-900` 风格)
- [x] T023 [US3] Implement PDF preview component with signed URL
- [x] T024 [US3] Create submit review API
- [x] **CP05** [存档点] 完成 US3 Issue 后立即 `git push` 存档

---

## Phase 6: User Story 4 - 财务开票与上线控制 (Priority: P4)

- [x] T025 [P] [US4] 实现 PDF 账单生成模块 (**含中文注释**)
- [x] T026 [US4] Create finance dashboard and confirm payment API
- [x] T027 [US4] 实现主编终审管理界面与 API 触发
- [x] T028 [US4] 实现最终发布逻辑
- [x] **CP06** [存档点] 完成 US4 Issue 后立即 `git push` 存档

---

## Phase 7: User Story 5 - AI 自动推荐审稿人 (Priority: P5)

- [x] T029 [P] [US5] Implement TF-IDF matching algorithm (**含中文注释**)
- [x] T030 [US5] Create recommend API and "Invite" logic
- [x] **CP07** [存档点] 完成 US5 Issue 后立即 `git push` 存档

---

## Phase N: Polish & Cross-Cutting Concerns

- [x] T031 实现前端全局 Error Boundary
- [x] T032 全链路 Quickstart 验证
- [x] T033 代码清理与文档同步
- [x] T034 [Hotfix] 补全缺失的业务 API 路由 (Quality Check, Publish, Finance)
- [x] T035 [Hotfix] 开发门户首页 (Landing Page) 与全局导航
- [x] **CP08** [最终存档] 执行 `git push` 同步全功能变更

---

## Notes

- **即时存档**: 每一个原子化任务或 Phase 结束后，必须执行 `git push`。
- **Arch 准则**: 安装优先用 `pacman`；AUR 必须切换至用户 `louis` 使用 `paru`；`pip` 被拒时使用 `--break-system-packages`。
- **注释规范**: 实现代码必须包含核心逻辑的中文注释。