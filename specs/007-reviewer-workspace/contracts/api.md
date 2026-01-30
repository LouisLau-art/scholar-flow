# API Contracts: Reviewer Workspace

## 1. 任务分配 (Editor API)
- **Endpoint**: `POST /api/v1/reviews/assign`
- **Body**: `{ manuscript_id: uuid, reviewer_id: uuid }`
- **Logic**: 包含“作者不得自审”校验。

## 2. 任务列表 (Reviewer API)
- **Endpoint**: `GET /api/v1/reviews/my-tasks`
- **Query**: `user_id=uuid`
- **Response**: 返回包含稿件标题和摘要的待办列表。

## 3. 提交评审 (Reviewer API)
- **Endpoint**: `POST /api/v1/reviews/submit`
- **Body**: 
```json
{
  "assignment_id": "uuid",
  "scores": {
    "novelty": 1-5,
    "rigor": 1-5,
    "language": 1-5
  },
  "comments": "string"
}
```
