# Quickstart: Local AI Matchmaker

## Prerequisites

1. **Python Dependencies**:
   ```bash
   pip install sentence-transformers pgvector
   ```
   (Note: `pgvector` python client might be needed if using SQLAlchemy/ORM, or just raw SQL via `supabase-py` / `asyncpg`.)

2. **Database Setup**:
   - Enable extension: `create extension vector;` (Must run in Supabase SQL Editor).
   - Run migrations for `reviewer_embeddings` table.

3. **Model Download**:
   - The first run of the app will download `all-MiniLM-L6-v2` (~80MB). Ensure internet access or pre-download cache.

## Verification Steps

### 1. Indexing (Reviewer Side)
1. Login as a **Reviewer**.
2. Go to Profile, update "Research Interests" (e.g., add "Machine Learning").
3. Save.
4. Check DB `reviewer_embeddings`: Ensure a new row exists for this user.

### 2. Analysis (Editor Side)
1. Login as an **Editor**.
2. Go to a Manuscript (or create dummy one with Title="Deep Learning in Medicine").
3. Click "AI Analysis" in the sidebar.
4. Verify the Reviewer from Step 1 appears in the list with a high score (> 0.7).

### 3. Cold Start
1. Truncate `reviewer_embeddings` table.
2. Request Analysis.
3. Verify UI shows "Insufficient Data" or similar message.
