---
description: "ScholarFlow 系统完整性与 Auth 任务清单"
---

# Tasks: System Integrity & Auth

**Input**: `specs/005-system-integrity-and-auth/`
**Prerequisites**: plan.md, spec.md, data-model.md

## Phase 1: Auth Infrastructure

- [x] T001 开发 `/login` 登录页面（支持 Email/Password）
- [x] T002 开发 `/signup` 注册页面
- [x] T003 配置前端 Supabase Auth 状态同步 (useAuth Hook)
- [x] T004 开发后端 Auth 中间件，验证 JWT Token
- [x] **CP01** [存档点] 完成 Auth 基础功能并推送

## Phase 2: API Expansion & Stats

- [x] T005 开发 `app/api/v1/users.py`：资料获取与通知
- [x] T006 开发 `app/api/v1/stats.py`：三个角色的统计接口
- [x] T007 开发 `app/api/v1/public.py`：学科与公告接口
- [x] T008 实现稿件流转历史记录逻辑 (T001 之后补齐)
- [x] **CP02** [存档点] 后端接口翻倍并推送

## Phase 3: Dashboard & Blank Pages

- [x] T009 开发统一 Dashboard 骨架页
- [x] T010 开发 Author 视角统计卡片与列表
- [x] T011 开发 `/about` 平台介绍页 (Frontiers 风格)
- [x] T012 开发 `/topics` 学科网格动态页
- [x] **CP03** [存档点] 消除所有空白页并推送

## Phase 4: Integration & Polish

- [ ] T013 链接修复：首页导航、页脚、各处跳转闭环
- [ ] T014 权限修复：非登录用户禁止进入 Dashboard
- [ ] T015 [DoD] 验证全流程：注册 -> 登录 -> 我的投稿展示
- [ ] **CP04** [最终存档] 系统完整性大版本推送