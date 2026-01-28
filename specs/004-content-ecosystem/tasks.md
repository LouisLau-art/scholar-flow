---
description: "ScholarFlow 内容生态构建任务列表"
---

# Tasks: Content Ecosystem

**Input**: `specs/004-content-ecosystem/`
**Prerequisites**: plan.md, spec.md

## Phase 1: Foundational (Schema & API)

- [x] T001 创建 `journals` 数据库表并关联 `manuscripts` (SETUP_DATABASE.sql 更新)
- [x] T002 开发后端 `GET /api/v1/journals` 接口
- [x] T003 开发后端 `GET /api/v1/articles/{id}` 接口
- [x] T004 实现基于 PostgreSQL 的全文检索接口 `GET /api/v1/search`
- [x] **CP01** [存档点] 完成后端数据层并推送

## Phase 2: Article Reading Experience (The Public View)

- [x] T005 开发文章详情页 `/articles/[id]` (学术元数据展示)
- [x] T006 集成 PDF 在线预览组件 (基于 Iframe/Object)
- [x] T007 设计并实现文章页侧边栏 (Related Articles, Metrics)

## Phase 3: Journal Portfolio & Discovery

- [x] T008 开发期刊详情页 `/journals/[id]` (列表展示 published 文章)
- [x] T009 对接首页搜索框与 `/search` 结果页的真实后端数据
- [x] T010 更新首页轮播图链接，使其指向真实的期刊详情页
- [x] **CP02** [存档点] 完成前端公共展示层并推送

## Phase 4: Integration & Polish

- [x] T011 增加“下载文章”记录统计逻辑 (Mock)
- [x] T012 [P] 适配学术门户的 SEO 元数据 (Open Graph)
- [x] T013 [DoD] 验证从 首页 -> 搜索 -> 文章页 的全路径通畅
- [ ] **CP03** [最终存档] 执行 `git push` 同步变更
