---
description: "ScholarFlow 自动化测试套件任务清单"
---

# Tasks: Quality Assurance Suite

**Input**: `specs/006-quality-assurance-suite/`
**Prerequisites**: plan.md, spec.md

## Phase 1: Test Infrastructure

- [x] T001 [P] 优先使用 `pacman` 安装 `python-pytest` 及相关异步插件
- [x] T002 初始化前端 Vitest 环境，配置 `vitest.config.ts`
- [x] T003 创建后端测试入口 `backend/tests/conftest.py` 配置全局 Fixture
- [x] **CP01** [存档点] 完成测试环境搭建并推送

## Phase 2: Core Backend Tests (TDD Style)

- [x] T004 编写稿件业务测试 `tests/test_manuscripts.py` (覆盖 CRUD)
- [x] T005 编写认证逻辑测试 `tests/test_auth.py`
- [x] T006 编写查重逻辑集成测试 `tests/test_plagiarism.py`
- [x] **CP02** [存档点] 后端核心覆盖完成并推送

## Phase 3: UI & Integration Tests

- [x] T007 编写投稿表单交互测试 `SubmissionForm.test.tsx`
- [x] T008 编写导航栏响应式测试 `SiteHeader.test.tsx`
- [x] T009 开发根目录 `run_tests.sh` 一键测试脚本
- [x] **CP03** [最终存档] 质量护城河建成并推送

## Notes
- **DoD**: 所有测试必须能在开发环境一键跑通。
- **Mocking**: 严禁在测试中真实调用 OpenAI 或 Crossref API。