# Feature Specification: Academic Portal Redesign

**Feature Branch**: `003-portal-redesign`
**Created**: 2026-01-27
**Status**: Draft
**References**: Frontiers, MDPI, PiscoMed landing pages.

## Context & Goals
目前的首页仅为简单的功能入口，缺乏学术出版机构的专业感与信任感。本特性旨在重构首页，将其打造为集**内容发现、投稿引导、品牌展示**于一体的综合性学术门户。

## User Scenarios

### US1: 全局导航与品牌认知 (Navigation & Branding)
- **As a** 访问者, **I want** 清晰的导航结构, **So that** 我能快速找到期刊列表、投稿入口或机构介绍。
- **Requirements**:
  - **Sticky Header**: 包含 Logo、一级导航 (Journals, Publish, About)、搜索入口、登录/个人中心。
  - **Mega Menu**: 鼠标悬停 "Journals" 时，展开分类或 A-Z 索引面板。
  - **Visual Style**: 严格遵循 Frontiers 风格（深蓝/白色底，无衬线字体导航，衬线字体标题）。

### US2: 核心检索与 Hero 区域 (Search & Discovery)
- **As a** 研究人员, **I want** 在首屏直接搜索文章, **So that** 我能快速验证平台的学术资源。
- **Requirements**:
  - **Hero Section**: 背景需体现学术严谨感（抽象几何或科研图片）。
  - **Search Box**: 支持通过 Title, DOI, Author 进行检索（前端模拟）。
  - **Call to Action (CTA)**: 醒目的 "Submit your manuscript" 按钮。

### US3: 动态内容展示 (Dynamic Content)
- **As a** 读者, **I want** 看到最新的发表动态, **So that** 我能了解平台的活跃度。
- **Requirements**:
  - **Featured Carousel**: 轮播展示“主编推荐”或“最新上线”的文章卡片。
  - **Stats Bar**: 展示 "Impact Factor", "Citations", "Articles Published" 等统计数字（Mock 数据）。

### US4: 期刊/学科分类 (Subject Areas)
- **As a** 作者, **I want** 浏览特定领域的期刊, **So that** 我能找到适合投稿的去处。
- **Requirements**:
  - **Subject Grid**: 网格化展示学科图标（Medicine, Engineering, Social Sciences...）。

## Success Criteria
- [ ] 首页视觉风格与 Frontiers/MDPI 达到 80% 以上相似度。
- [ ] 导航栏在移动端自动折叠为 Hamburger Menu（响应式）。
- [ ] 搜索框能够响应输入并跳转至搜索结果页（/search）。

## Design Assets (Reference)
- **Color Palette**: 
  - Primary: `slate-900` (Frontiers Black/Blue)
  - Accent: `blue-600` (Hyperlinks/Buttons)
  - Background: `white` / `slate-50`
- **Typography**:
  - Headings: Serif (Merriweather or Noto Serif)
  - Body: Sans (Inter or Roboto)
