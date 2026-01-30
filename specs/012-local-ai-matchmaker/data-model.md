# Data Model: Local AI Matchmaker

**Feature Branch**: `012-local-ai-matchmaker`
**Date**: 2026-01-30

## Entities

### 1. Reviewer Embeddings (Extension)
**Table**: `public.reviewer_embeddings` (New Table or Extension)
*Actually, strictly separating embeddings is cleaner than altering `auth.users`.*

| Field | Type | Constraint | Description |
|-------|------|------------|-------------|
| user_id | uuid | PK, FK -> auth.users | 1:1 Link to User |
| embedding | vector(384) | | 384-dim vector from MiniLM-L6 |
| updated_at | timestamptz | Default: now() | Last indexing time |
| source_text_hash | text | | Hash of input text to skip re-indexing if unchanged |

**RLS Policies**:
- `SELECT`: Service Role only（后端分析 API 使用 `SUPABASE_SERVICE_ROLE_KEY` 查询，避免前端/匿名直接读取向量）。
- `INSERT/UPDATE`: Service Role only（后台索引任务写入/更新）。

### 0. Reviewer Profile Fields（Source of Interests）
**Table**: `public.user_profiles`（existing）

MVP 需要新增/补齐字段以承载可编辑的“研究兴趣”，用于生成 embedding（避免依赖 `auth.users.raw_user_meta_data` 这种不稳定结构）：
- `name` (text, optional)
- `institution` (text, optional)
- `research_interests` (text, optional) —— 允许使用英文逗号/分号分隔多个兴趣点

### 2. Manuscript Embeddings (Cache - Optional)
*For MVP, we might calculate Manuscript embedding on the fly during analysis to save storage, or store it. Given SC-001 performance goal, on-the-fly for analysis is fine (100ms), but storing it allows "Related Manuscripts" later. Let's compute on-the-fly for "Analyze" request to keep data model simple, unless explicitly required. Spec FR-001 implies generation, not necessarily storage. But FR-003 says "use Supabase pgvector to store embeddings". Okay, we should store Reviewer embeddings. Manuscript embeddings are transient for the search query usually, unless we implement "Find Reviewers for stored Manuscript".*

**Decision**: 
- **Reviewer Embeddings**: Stored in DB (`reviewer_embeddings`).
- **Manuscript Embeddings**: Calculated in-memory during `POST /analyze` request to query the DB. (No DB table needed for Manuscript vectors in MVP).

## Validation Rules
- `embedding` dimensions must match model (384).
- `user_id` must allow only users with `reviewer` role.

## State Transitions
- **Profile Update**: User saves profile -> Backend Task -> Computes Vector -> Upsert `reviewer_embeddings`.
- **Analysis**: Editor clicks "Analyze" -> Backend computes Manuscript Vector -> SQL Query (`<=>` operator) -> Returns List.
