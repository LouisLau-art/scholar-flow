# Research: Local AI Matchmaker

**Feature Branch**: `012-local-ai-matchmaker`
**Date**: 2026-01-30
**Input**: Feature spec.md and user clarifications

## 1. Vector Storage & Search (Supabase)

- **Decision**: Use `pgvector` extension in Supabase PostgreSQL.
- **Rationale**: 
  - Native integration with our existing database.
  - Allows efficient cosine similarity searches (`<=>` operator) via SQL.
  - Persistent storage avoids re-indexing on service restarts (unlike in-memory solutions).
- **Implementation**:
  - Run `create extension vector;` migration.
  - Create a dedicated `public.reviewer_embeddings` table with `embedding vector(384)` (384 dims for MiniLM-L6).
  - Optionally add an `ivfflat/hnsw` index once rows > 2000；MVP 先保证正确性与可迁移性。

## 2. Embedding Model (Local NLP)

- **Decision**: `sentence-transformers/all-MiniLM-L6-v2`
- **Rationale**: 
  - Extremely lightweight (~80MB), fast inference on CPU.
  - High semantic quality for general English text (Manuscript titles/abstracts).
  - Standard library `sentence_transformers` is robust and easy to use in Python.
- **Alternatives Considered**:
  - `TF-IDF`: Rejected due to lack of semantic understanding (e.g., "AI" vs "Machine Learning").
  - `OpenAI/Cohere`: Rejected due to strict "No External API" privacy constraint.
  - `BERT-Base`: Rejected as too heavy/slow for a basic CPU backend without GPU.

## 3. Asynchronous Processing

- **Decision**: FastAPI `BackgroundTasks`
- **Rationale**: 
  - "Glue Coding" principle: simplest tool for the job.
  - Avoids setting up a heavy Celery/Redis worker cluster for MVP.
  - Tasks (indexing user profiles, analyzing manuscripts) are short-lived (< 10s usually).
- **Pattern（最终落地）**:
  - **Indexing（Reviewer Profile 更新）**：使用 `BackgroundTasks` fire-and-forget，避免保存资料时卡顿。
  - **Analysis（Editor 触发）**：API 同步返回推荐列表（便于 UI 直接 Loading -> Render），但向量化计算必须放到线程池执行，避免阻塞 FastAPI 事件循环（满足“异步计算/不阻塞 UI”这一验收语义）。

## 4. Data Source for Reviewers

- **Decision**: Reviewer Interests + Past Manuscript Titles.
- **Rationale**: 
  - Titles are high-signal, low-noise.
  - Abstracts might be missing or too long, diluting the reviewer's "core" expertise vector.
  - Concatenate "Interest 1, Interest 2. Title 1. Title 2." as the input text for embedding.

## 5. Configuration

- **Decision**: Environment Variables / `backend/app/core/config.py`
- **Parameters**:
  - `MATCHMAKING_THRESHOLD`: 0.70
  - `MATCHMAKING_TOP_K`: 5
