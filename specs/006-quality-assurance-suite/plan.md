# Implementation Plan: Quality Assurance Suite

**Feature**: `006-quality-assurance-suite`
**Spec**: [specs/006-quality-assurance-suite/spec.md]

## Technical Decisions

### 1. 后端测试 (Backend)
- **Framework**: `pytest`
- **Plugin**: `pytest-asyncio` (用于异步 FastAPI 接口测试)。
- **Client**: `httpx.AsyncClient`。
- **Mocking**: 使用 `unittest.mock` 模拟外部 API (OpenAI, Crossref)。

### 2. 前端测试 (Frontend)
- **Framework**: `Vitest` (兼容 Vite 且极速)。
- **Library**: `@testing-library/react` + `@testing-library/jest-dom`。
- **Browser Environment**: `jsdom`。

## Implementation Phased

### Phase 1: Infrastructure Setup
- 安装后端测试依赖 (pytest, pytest-asyncio)。
- 安装前端测试依赖 (vitest, jsdom)。
- 创建测试目录结构 `tests/`。

### Phase 2: Backend API Tests
- 实现 `test_manuscripts.py`: 覆盖上传、列表、搜索。
- 实现 `test_auth.py`: 验证 JWT 解析失败时的 401 返回。
- 实现 `test_plagiarism.py`: 验证 0.3 门控逻辑。

### Phase 3: Frontend Component Tests
- 实现 `SubmissionForm.test.tsx`: 模拟文件上传与元数据回显。
- 实现 `PlagiarismActions.test.tsx`: 验证不同状态下的按钮展示。

## Constitution Check
- **OT 原则**: 测试报告必须清晰、结构化。
- **Simple & Explicit**: 测试代码本身必须易读，作为 API 的“执行文档”。
