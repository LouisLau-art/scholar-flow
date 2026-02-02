---
description: "Tasks for Local AI Matchmaker implementation"
---

# Tasks: Local AI Matchmaker

**Input**: Design documents from `/specs/012-local-ai-matchmaker`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 [P] 在 `backend/requirements.txt` 添加 `sentence-transformers`（本地向量化模型依赖）
- [x] T002 [P] 在 `backend/app/core/config.py` 增加匹配参数配置（`MATCHMAKING_MODEL_NAME / MATCHMAKING_THRESHOLD / MATCHMAKING_TOP_K / MATCHMAKING_MIN_REVIEWERS`），全部从环境变量读取
- [x] T003 [P] 补齐/修正 012 文档一致性：`spec.md` / `research.md` / `data-model.md` / `contracts/api.yaml` / `tasks.md`

## Phase 2: Database (pgvector + Embeddings)

- [x] T004 [P] 新增 Supabase migration：启用 `vector` 扩展（`create extension if not exists vector;`）
- [x] T005 [P] 新增 `public.reviewer_embeddings` 表（`user_id` PK + `embedding vector(384)` + `source_text_hash` + `updated_at`）
- [x] T006 [P] 为 `public.user_profiles` 增加字段：`name` / `institution` / `research_interests`（用于 Reviewer 兴趣输入）
- [x] T007 [P] 新增 SQL function `match_reviewers(...)`（使用 `<=>` 做 cosine distance 并返回 `score`）
- [x] T008 [P] 为 `reviewer_embeddings` 配置 RLS：仅允许 `service_role` 读写（禁止前端直接读取向量）

## Phase 3: Backend (US1 - Analysis)

- [x] T009 [P] 新增 `backend/app/core/ml.py`：模型加载 + 向量化（384 维）+ 输入哈希（用于跳过重复索引）
- [x] T010 [P] 新增 `backend/app/services/matchmaking_service.py`：分析与索引的核心逻辑（含中文注释说明相似度换算）
- [x] T011 [P] 新增 `backend/app/api/v1/matchmaking.py`：`POST /api/v1/matchmaking/analyze`（Editor/Admin RBAC + 输入校验 + 冷启动提示）
- [x] T012 [P] 在 `backend/main.py` 注册 matchmaking router，并更新 `backend/tests/contract/test_api_paths.py`
- [x] T013 [P] 后端测试：`analyze` 端点覆盖（成功/缺少认证/无效 token/非 editor 403/冷启动 insufficient_data/输入缺失 422）

## Phase 4: Backend (US2 - Indexing)

- [x] T014 [P] 实现 `PUT /api/v1/user/profile` 持久化更新 `user_profiles`（不再返回 mock），并在当前用户具备 `reviewer` 角色时触发 BackgroundTask 进行索引
- [x] T015 [P] 索引逻辑：拼接 `research_interests + 过往审稿稿件标题` 作为 embedding 输入，并 upsert 到 `reviewer_embeddings`
- [x] T016 [P] 后端测试：profile update 触发索引（mock ML/DB），并验证不会暴露 embedding

## Phase 5: Frontend (US1/US3 - UI + Invite)

- [x] T017 [P] 新增 `frontend/src/services/matchmaking.ts`：封装 `POST /api/v1/matchmaking/analyze`
- [x] T018 [P] 在 `frontend/src/components/ReviewerAssignModal.tsx` 集成 “AI Analysis” 区块：Loading 状态 + 推荐列表 + Invite 按钮
- [x] T019 [P] 前端测试：推荐区块的 loading/render/invite 交互（Vitest + RTL）

## Phase 6: QA & Compliance

- [x] T020 [P] 安全审计测试：在单测中禁用 `socket` 外联，确保 matchmaking 代码路径不会发起外部 HTTP（SC-002）
- [x] T021 [P] 跑全量测试：`./scripts/run-all-tests.sh`
- [x] T022 [P] 更新 `specs/012-local-ai-matchmaker/spec.md` Status -> Implemented，并补齐 quickstart 的 env/迁移说明
- [x] T023 [P] `git push` 分支 `012-local-ai-matchmaker`

## Dependencies

- Phase 2 blocks Phase 3 and 4.
- Phase 3 (Analysis) and Phase 4 (Indexing) are technically independent but rely on the same ML service.
- Phase 5 depends on Phase 3 UI.

## Parallel Execution

**User Story 1**:
- Backend Endpoint (T008) and Frontend Panel (T011) can be built in parallel once contracts are defined.

**User Story 2**:
- Indexing Logic (T015) and Background Trigger (T013) can be developed in parallel.
