# Feature Specification: The Content Ecosystem

**Feature Branch**: `004-content-ecosystem`
**Created**: 2026-01-27
**Status**: Draft

## Context
本特性旨在实现稿件发布后的“终点站”。让平台拥有公开的期刊主页和美观的文章详情页，支持 PDF 在线预览和学术元数据展示。

## User Scenarios

### US1: 期刊主页门户 (Journal Landing Page)
- **As a** 访客, **I want** 进入特定期刊（如 AI Ethics）的主页, **So that** 我能看到该期刊的简介、主编信息和最新发表的文章。
- **Requirements**:
  - 展示期刊封面图、ISSN、Impact Factor。
  - 列表展示该期刊下状态为 `published` 的稿件。

### US2: 文章详情与在线阅读 (Article View)
- **As a** 读者, **I want** 点击文章标题进入详情页, **So that** 我能阅读摘要、查看作者并在网页直接预览 PDF。
- **Requirements**:
  - **Metadata Display**: 标题、作者（带机构）、摘要、关键字、DOI。
  - **PDF Viewer**: 集成在线 PDF 渲染器。
  - **Metrics**: 展示文章的阅读量、下载量（Mock）。

### US3: 全局内容检索 (Search Implementation)
- **As a** 用户, **I want** 在首页搜索框输入关键词, **So that** 系统能从已发表的文章中返回匹配结果。
- **Requirements**:
  - 通过后端接口 `GET /api/v1/manuscripts/search?q=...&mode=articles|journals` 提供检索结果。
  - `mode=articles`: 仅返回状态为 `published` 的文章（公开检索）。
  - `mode=journals`: 从 `journals` 表按标题模糊检索期刊。

## Success Criteria
- [ ] 每个发表的稿件都有一个唯一的公开 URL（如 `/articles/{id}`）。
- [ ] PDF 预览组件加载速度 < 2秒。
- [ ] 搜索结果页能展示标题/摘要片段；无结果时给出明确提示（避免“空白页”误判为故障）。
