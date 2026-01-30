# Feature Specification: System Integrity & Auth

**Feature Branch**: `005-system-integrity-and-auth`
**Created**: 2026-01-27
**Status**: Draft

## Goals
1. **消灭空白页**: 实现 `/about`, `/topics`, `/login` 页面。
2. **接入 Auth**: 使用 Supabase Auth 实现真实的登录/注册流。
3. **角色分权**: 根据用户角色（Author, Editor, Reviewer）展示不同的 Dashboard 统计数据。
4. **API 扩容**: 后端接口数量翻倍，涵盖用户资料、统计、系统公告等。

## Implementation Notes (Current Repo)
- **角色来源**: 使用 `public.user_profiles.roles`（`text[]`）作为“应用层角色表”。首次调用 `GET /api/v1/user/profile` 时自动创建记录，默认 `['author']`。
- **管理员便捷配置**: 支持 `ADMIN_EMAILS`（逗号分隔邮箱）把指定账号自动提升为 `['admin','editor','reviewer','author']`，便于本地/演示测试。
- **前后端一致性**:
  - 前端 Dashboard 仅在拥有对应角色时展示 Reviewer/Editor Tabs。
  - 后端对 `/api/v1/editor/*`、`/api/v1/reviews/*` 等敏感接口做 role gate（403）。

## User Scenarios

### US1: 统一身份认证 (Secure Identity)
- **As a** 用户, **I want** 使用邮箱登录系统, **So that** 我能看到属于我自己的投稿或任务。
- **Requirements**:
  - 实现标准 Login/Sign-up 页面。
  - 前后端接入 Supabase Auth Token 校验。

### US2: 角色化工作台 (Personalized Dashboards)
- **As a** 作者, **I want** 一个专门的仪表盘展示我所有投稿的状态, **So that** 我不需要手动查表。
- **Requirements**:
  - **Author Dashboard**: 投稿总数、待修改文章、已发表文章。
  - **Reviewer Dashboard**: 待评审、已审结文章。

### US3: 内容目录与发现 (Topics & About)
- **As a** 访客, **I want** 浏览所有学科分类（Topics）, **So that** 我能快速定位感兴趣的领域。
- **Requirements**:
  - `/topics` 页面展示网格化的学科入口。
  - `/about` 页面展示平台愿景、团队和联系方式。

## Success Criteria
- [ ] 首页所有链接点击后不再是 404 或空白。
- [ ] 能够成功完成一次真实的“注册 -> 登录 -> 投稿”流程。
- [ ] 后端新增至少 10 个业务接口。
