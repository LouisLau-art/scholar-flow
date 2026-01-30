# Quickstart: Local AI Matchmaker

## Prerequisites

1. **Python Dependencies**:
   ```bash
   pip install sentence-transformers pgvector
   ```
   (Note: `pgvector` python client might be needed if using SQLAlchemy/ORM, or just raw SQL via `supabase-py` / `asyncpg`.)

2. **Database Setup**:
   - 应用迁移：`supabase/migrations/20260130180000_add_matchmaking_embeddings.sql`
   - 该迁移会：
     - 启用扩展：`create extension if not exists vector;`
     - 创建 `public.reviewer_embeddings` 与 `public.match_reviewers(...)`
     - 为 `public.user_profiles` 增加 `name/institution/research_interests`

3. **Model Download**:
   - 首次运行会下载 `sentence-transformers/all-MiniLM-L6-v2`（约 80MB）。
   - 生产建议：预热模型缓存，或在部署环境设置 HuggingFace 离线缓存（避免运行时拉取）。

## Required Environment Variables

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`（或 `SUPABASE_KEY`）
- `SUPABASE_SERVICE_ROLE_KEY`（必需：写入 `reviewer_embeddings` / 调用 `match_reviewers`）
- `SUPABASE_JWT_SECRET`（用于本地 HS256 JWT 校验）

### Optional Matchmaking Tunables

- `MATCHMAKING_MODEL_NAME`（默认：`sentence-transformers/all-MiniLM-L6-v2`）
- `MATCHMAKING_THRESHOLD`（默认：`0.70`）
- `MATCHMAKING_TOP_K`（默认：`5`）
- `MATCHMAKING_MIN_REVIEWERS`（默认：`5`）

## Verification Steps

### 1. Indexing (Reviewer Side)
1. Login as a **Reviewer**.
2. Go to Profile, update "Research Interests" (e.g., add "Machine Learning").
3. Save.
4. Check DB `reviewer_embeddings`: Ensure a new row exists for this user.

### 2. Analysis (Editor Side)
1. Login as an **Editor**.
2. Go to a Manuscript (or create dummy one with Title="Deep Learning in Medicine").
3. Click "AI Analysis" in the Assign Reviewer modal.
4. Verify the Reviewer from Step 1 appears in the list with a high score (> 0.7).

### 3. Cold Start
1. Truncate `reviewer_embeddings` table.
2. Request Analysis.
3. Verify UI shows "Insufficient Data" or similar message.
