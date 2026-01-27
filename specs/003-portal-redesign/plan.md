# Implementation Plan: Academic Portal Redesign

**Feature**: `003-portal-redesign`
**Spec**: [specs/003-portal-redesign/spec.md]

## Technical Architecture

### 1. Frontend Components
需要新建/重构以下组件：
- **`src/components/layout/SiteHeader.tsx`**: 全局吸顶导航，替代现有的简陋 Header。
- **`src/components/layout/MegaMenu.tsx`**: 下拉式大菜单。
- **`src/components/home/HeroSection.tsx`**: 包含搜索框和背景图的核心区域。
- **`src/components/home/JournalCarousel.tsx`**: 基于 `embla-carousel` 的轮播组件。
- **`src/components/home/StatsBanner.tsx`**: 统计数据展示条。
- **`src/components/home/SubjectGrid.tsx`**: 学科分类网格。

### 2. Dependencies
- **`embla-carousel-react`**: 用于实现高性能轮播图。
- **`framer-motion`** (可选): 如果需要平滑的下拉菜单动画。目前先用 CSS Transition 保持轻量。

### 3. Data Flow
- **Mock Data**: 首页的“最新文章”、“期刊列表”暂时使用硬编码的 JSON 数据，后续对接后端 `GET /public/journals` 接口。
- **Search**: `SearchBox` 组件接收输入后，跳转 `router.push('/search?q=...')`。

## Visual Strategy (Frontiers Style)
- **Header**: 高度 `h-16` -> `h-20`，背景 `bg-slate-900`，文字 `text-white`。
- **Typography**: 
  - 标题使用 `font-serif` (Tailwind 自带或 `next/font` 配置)。
  - 正文使用 `font-sans`。
- **Spacing**: 使用大间距 (`py-20`, `gap-8`) 营造呼吸感。

## Implementation Steps (Phased)

### Phase 1: Infrastructure & Assets
- 安装 `embla-carousel-react`。
- 准备学科图标 (SVG) 和 Hero 背景图 (Unsplash/CSS Pattern)。

### Phase 2: Structural Components
- 开发 `SiteHeader` (含响应式 Hamburger)。
- 开发 `HeroSection` (含 SearchBox)。

### Phase 3: Content Blocks
- 开发 `JournalCarousel`。
- 开发 `SubjectGrid` 和 `StatsBanner`。

### Phase 4: Integration
- 替换 `src/app/page.tsx`。
- 适配 Mobile 端样式。

## Constitution Check
- **Visual Standards**: 严格遵循 V. UI/UX Visual Standards (Frontiers 风格)。
- **Full-Stack Slice**: 虽然是纯前端改版，但需预留搜索接口对接点。
