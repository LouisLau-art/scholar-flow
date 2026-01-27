# Tasks: Reviewer Workspace

## Phase 1: Design & Schema
- [x] T001 编写 spec.md 和 plan.md
- [x] T002 更新 SETUP_DATABASE.sql 包含 review_assignments 表
- [x] T003 [P] 预置审稿种子数据

## Phase 2: Backend Development (v1.9.0 Compliant)
- [x] T004 实现显性路由接口 `POST /reviews/assign` (含冲突校验)
- [x] T005 实现接口 `GET /reviews/my-tasks`
- [x] T006 实现接口 `POST /reviews/submit`
- [x] T007 [DoD] 编写并跑通 `test_review_flow.py` (UUID 兼容版)

## Phase 3: Frontend Workspace
- [x] T008 开发 `ReviewerDashboard` 任务列表组件
- [x] T009 集成结构化评分 Dialog 弹窗 (Novelty/Rigor 滑动条)
- [x] T010 [Story] 实现评审提交的 Sonner Toast 反馈与列表刷新
- [x] T011 在全局 Dashboard 增加视角切换 Tabs

## Phase 4: Polish & Handover
- [ ] T012 实现“阅读全文”按钮打开 PDF 预览逻辑
- [ ] T013 适配移动端评分操作
- [x] **CP01** [存档点] 修复测试 UUID 序列化并推送
