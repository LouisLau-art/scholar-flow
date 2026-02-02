# Implementation Plan: Editor Command Center

## Architecture & Routing
- **显性路由**: 
  - `GET /api/v1/editor/pipeline`: 获取全量稿件流转状态。
  - `GET /api/v1/editor/reviewers`: 获取可用专家池。
  - `POST /api/v1/editor/decision`: 提交最终录用/退回决策。

## Quality Assurance (QA Suite)
- **后端测试**: `test_editor_actions.py`。
  - 验证：非编辑角色请求 pipeline 接口应返回 403 (待 Auth 完善角色段后)。
  - 验证：录用操作能够正确更新 `published_at` 并生成 DOI。

## UI/UX Standard
- **Frontiers 风格**: 保持 `slate-900` 调性，使用网格布局清晰展示不同状态的稿件。
