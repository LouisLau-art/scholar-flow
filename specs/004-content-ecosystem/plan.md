# Implementation Plan: Content Ecosystem

**Feature**: `004-content-ecosystem`
**Spec**: [specs/004-content-ecosystem/spec.md]

## Technical Decisions

### 1. PDF 预览方案
- **Decision**: 使用 `react-pdf-viewer` 或 `iframe` 直接嵌入 Supabase Storage 的 PDF 链接。
- **Rationale**: `iframe` 是最快、最兼容的方案，且支持浏览器自带的打印/缩放功能。

### 2. 数据库扩展
- 需要在 `manuscripts` 表中增加以下字段（虽然目前已有基础字段，但需确保完整性）：
  - `doi`: 文章数字唯一标识。
  - `journal_id`: 关联的期刊 ID。
  - `published_at`: 正式发布时间。

### 3. 前端路由结构
- `/journals/[id]`: 期刊主页。
- `/articles/[id]`: 文章详情页。
- `/search`: 检索结果页（完善我们在 003 中留下的骨架）。

## Implementation Phased

### Phase 1: Data & API
- 修改数据库 Schema 增加 `journals` 表。
- 编写 `GET /articles/{id}` 和 `GET /journals/{id}` 后端接口。
- 实现 `GET /search` 后端检索逻辑。

### Phase 2: Journal & Article Pages
- 开发期刊门户 UI。
- 开发文章详情 UI（含 PDF 嵌入）。

### Phase 3: Search & Discovery Integration
- 将首页搜索框与后端接口真正打通。
- 将首页轮播图点击链接指向真实的期刊页。

## Constitution Check
- **Visual Standards**: 延续 Frontiers 的干净排版风格。
- **Full-Stack Slice**: 必须包含真实的数据检索，拒绝 Mock 搜索结果。
