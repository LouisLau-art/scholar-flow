---
description: "ScholarFlow 自动查重功能任务列表 (v1.6.0 合宪修订版)"
---

# Tasks: Manuscript Plagiarism Check

**Input**: Design documents from `/specs/002-plagiarism-check/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 [P] 优先使用 `pacman` 安装 `python-httpx`，AUR 项切换至用户 `louis` 使用 `paru`
- [x] T002 在 Supabase Storage 中创建私有 Bucket `plagiarism-reports` 并配置 RLS 策略
- [x] **CP01** [存档点] 执行 `git push` 同步 Phase 1 环境配置

---

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T003 创建 `PlagiarismReports` 数据库表 (包含 `manuscript_id` 唯一索引)
- [x] T004 [P] 定义查重报告 Pydantic v2 模型 (**含中文注释**)
- [x] T005 [P] 定义前端查重状态 TypeScript 接口
- [x] T006 [P] 封装后端 Crossref API 异步客户端 (**含中文注释**)
- [x] **CP02** [存档点] 执行 `git push` 同步 Phase 2 基础定义

---

## Phase 3: User Story 1 - 自动触发查重流程 (Priority: P1) 🎯 MVP

- [ ] T007 [US1] 实现查重任务的异步调度逻辑 (BackgroundTasks) (**含中文注释**)
- [ ] T008 [US1] 在稿件提交 API 中集成查重任务触发逻辑
- [ ] T009 [US1] 实现查重状态轮询与数据库更新逻辑
- [ ] T009a [US1] 在异步 Worker 中实现基础限流逻辑 (Rate Limiting) (**含中文注释**)
- [ ] T010 [US1] 封装前端查重状态查询 API 调用
- [ ] **CP03** [存档点] 完成 US1 Issue 后立即 `git push` 存档

---

## Phase 4: User Story 2 - 高重复率自动预警 (Priority: P2)

- [ ] T011 [US2] 实现相似度门控判断逻辑（>0.3 自动更新状态）
- [ ] T012 [US2] 实现高重复率预警邮件通知触发逻辑
- [ ] T013 [US2] 在编辑管理后台实现“高重复率风险”的视觉展示
- [ ] **CP04** [存档点] 完成 US2 Issue 后立即 `git push` 存档

---

## Phase 5: User Story 3 - 查重报告查看与管理 (Priority: P3)

- [ ] T014 [US3] 实现后端下载 API 获取签名链接 (**含中文注释**)
- [ ] T015 [US3] 开发查重报告下载组件
- [ ] T016 [US3] 实现后端手动重试 API (幂等性校验)
- [ ] T017 [US3] 开发“手动重试查重”按钮及其交互逻辑
- [ ] **CP05** [存档点] 完成 US3 Issue 后立即 `git push` 存档

---

## Phase N: Polish & Cross-Cutting Concerns

- [ ] T018 增加后端查重逻辑的结构化日志记录 (OT 原则)
- [ ] T019 全链路 Quickstart 验证
- [ ] T019a 创建查重准确率验证脚本以验证 SC-001 (**含中文注释**)
- [ ] T020 代码清理与文档同步
- [ ] **CP06** [最终存档] 执行 `git push` 同步全功能变更

---

## Notes



- **即时存档**: 每一个原子化任务或 Phase 结束后，必须执行 `git push`。

- **Arch 准则**: 安装优先用 `pacman`；AUR 必须切换至用户 `louis` 使用 `paru`；`pip` 被拒时使用 `--break-system-packages`。

- **注释规范**: 实现代码必须包含核心逻辑的中文注释。
