---
description: "ScholarFlow 学术门户重构任务列表"
---

# Tasks: Academic Portal Redesign

**Input**: `specs/003-portal-redesign/`
**Prerequisites**: plan.md, spec.md

## Phase 1: Setup & Assets

- [x] T001 [P] 安装 `embla-carousel-react` 及相关插件
- [x] T002 [P] 在 `globals.css` 中配置 Serif 字体 (Merriweather/Times 备选)
- [x] T003 [P] 准备 Hero Section 的背景图资源 (CSS Pattern)

## Phase 2: Navigation & Header (The "Frontiers" Look)

- [x] T004 开发 `SiteHeader` 组件 (Desktop 版: Logo, Nav Links, Auth Buttons)
- [x] T005 实现 `MegaMenu` 交互逻辑 (Hover 展开期刊分类)
- [x] T006 开发 `MobileNav` 组件 (Hamburger Menu)
- [x] **CP01** [存档点] 完成导航栏开发并推送

## Phase 3: Hero & Search (The "Discovery" Core)

- [x] T007 开发 `HeroSection` 组件 (布局、文案、背景)
- [x] T008 实现 `SearchBox` 组件 (Tab 切换: Articles / Journals)
- [x] T009 创建 `/search` 结果页骨架 (防止搜索跳转 404)

## Phase 4: Dynamic Content Blocks

- [x] T010 开发 `JournalCarousel` 组件 (集成 Embla Carousel)
- [x] T011 开发 `StatsBanner` 组件 (展示 Impact Factor 等数字)
- [x] T012 开发 `SubjectGrid` 组件 (网格化展示学科)
- [x] **CP02** [存档点] 完成所有板块组件并推送

## Phase 5: Integration & Polish

- [x] T013 重写 `src/app/page.tsx`，组装所有新组件
- [x] T014 [P] 适配 Mobile/Tablet 响应式布局
- [x] T015 [DoD] 验证所有链接 (Submit, Login, Search) 点击有效
- [x] **CP03** [最终存档] 执行 `git push` 同步变更

## Notes
- **DoD**: 首页必须看起来像 Frontiers/MDPI，不能有“半成品”感。
- **Performance**: 轮播图必须支持懒加载。
