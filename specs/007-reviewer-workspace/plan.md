# Implementation Plan: Reviewer Workspace

## Technical Decisions

### 1. Architecture & Routing
- **显性路由**: 
  - `POST /api/v1/reviews/assign`: 编辑分配任务。
  - `GET /api/v1/reviews/my-tasks`: 审稿人获取个人任务。
  - `POST /api/v1/reviews/submit`: 提交多维度评分。
- **全栈切片**: 交付编辑端的 `AssignmentModal` 和审稿人端的 `ReviewDashboard`。

### 2. Dependencies & SDKs
- **原生优先**: 直接使用 `supabase-py` 操作 `review_assignments` 表。
- **UI 组件**: 使用 `sonner` 进行分配成功的反馈。

## Quality Assurance (QA Suite)
- **后端测试**: 编写 `test_review_flow.py`。
  - 测试 1: 编辑分配权限校验。
  - 测试 2: 审稿人无法评审自己的稿件 (Conflict Check)。
  - 测试 3: 多维度评分汇总计算逻辑。

## 数据模型变更
- `review_assignments`:
  - `id` (UUID, PK)
  - `manuscript_id` (FK -> manuscripts)
  - `reviewer_id` (FK -> auth.users)
  - `status` (pending, completed)
  - `scores` (JSONB: {novelty: int, rigor: int, language: int})
  - `comments` (Text)
