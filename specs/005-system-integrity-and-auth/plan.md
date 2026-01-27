# Implementation Plan: System Integrity & Auth

**Feature**: `005-system-integrity-and-auth`
**Spec**: [specs/005-system-integrity-and-auth/spec.md]

## Technical Decisions

### 1. Auth 选型
- **Decision**: 纯净的 **Supabase Auth (Native SDK)**。
- **Rationale**: 既然我们已经在用 Supabase 数据库，Auth 集成是最自然的选择。前端直接使用原生 `@supabase/supabase-js`，摒弃不稳定的 Helper 库。后端中间件校验 JWT。

### 2. 空白页填充策略
- 使用 **Shadcn/UI** 的 `Card`, `Skeleton`, `EmptyState` 模式。
- `/topics`: 动态读取数据库中的学科分类。
- `/about`: 静态内容结合动画。

### 3. API 架构扩容
- 创建 `app/api/v1/users.py` 和 `app/api/v1/stats.py`。
- 将逻辑从大的 `manuscripts.py` 中拆分，实现模块化。

## Implementation Phased

### Phase 1: Auth & Login (The Foundation)
- 实现 `/login` 和 `/signup` 页面。
- 配置 Supabase Auth 前端 Provider。
- 开发后端 Auth Middleware。

### Phase 2: User Dashboards (The Muscle)
- 实现 Author / Editor / Reviewer 三合一 Dashboard。
- 开发配套的统计 API。

### Phase 3: Completing Public Pages (The Skin)
- 开发 `/about` 和 `/topics` 页面。
- 将首页占位链接真正挂载。

## Constitution Check
- **Full-Stack Slice**: 每一项任务必须包含真实 API 支持。
- **Visual Standards**: 维持 Frontiers 的极简专业风格。
