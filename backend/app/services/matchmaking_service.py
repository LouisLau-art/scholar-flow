from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException

from app.core.config import MatchmakingConfig
from app.core.ml import embed_text, hash_source_text
from app.lib.api_client import supabase_admin


def _to_pgvector_literal(vector: List[float]) -> str:
    """
    将 Python list[float] 转成 pgvector 可解析的字面量字符串。

    中文注释:
    - Supabase RPC 入参对 vector 类型的兼容性在不同 SDK/版本下存在差异；
      使用显式字面量（"[0.1,0.2,...]"）能最大化兼容性。
    """

    return "[" + ",".join(f"{x:.6f}" for x in vector) + "]"


class MatchmakingService:
    """
    本地审稿人匹配服务（Feature 012）
    """

    def __init__(
        self,
        config: Optional[MatchmakingConfig] = None,
        *,
        db_client=None,
        embedder=None,
    ) -> None:
        self._config = config or MatchmakingConfig.from_env()
        self._db = db_client or supabase_admin
        self._embedder = embedder or (lambda text: embed_text(text, self._config.model_name))

    def analyze(
        self,
        *,
        manuscript_id: Optional[str],
        title: Optional[str],
        abstract: Optional[str],
    ) -> Dict[str, Any]:
        """
        为稿件生成 embedding，并返回 TopK 推荐审稿人。
        """

        config = self._config

        # 冷启动门槛：reviewer_embeddings 少于 min_reviewers 时，返回友好提示
        try:
            corpus_preview = (
                self._db.table("reviewer_embeddings")
                .select("user_id")
                .limit(config.min_reviewers)
                .execute()
            )
            corpus_rows = getattr(corpus_preview, "data", None) or []
        except Exception as e:
            print(f"[matchmaking] failed to read reviewer_embeddings: {e}")
            raise HTTPException(status_code=503, detail="Matchmaking unavailable (database not configured)")

        if len(corpus_rows) < config.min_reviewers:
            return {
                "recommendations": [],
                "insufficient_data": True,
                "message": "Insufficient reviewer data. Add more reviewers or wait for indexing to complete.",
            }

        ms_title, ms_abstract = self._resolve_manuscript_text(manuscript_id=manuscript_id, title=title, abstract=abstract)

        query_text = self._build_manuscript_source_text(title=ms_title, abstract=ms_abstract)
        vector = self._embedder(query_text)
        if not isinstance(vector, list) or len(vector) != 384:
            raise HTTPException(status_code=500, detail="Embedding generation failed (unexpected dimension)")

        query_embedding = _to_pgvector_literal(vector)

        try:
            match_resp = self._db.rpc(
                "match_reviewers",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": float(config.threshold),
                    "match_count": int(config.top_k),
                },
            ).execute()
        except Exception as e:
            print(f"[matchmaking] rpc match_reviewers failed: {e}")
            raise HTTPException(status_code=503, detail="Matchmaking unavailable (rpc missing)")

        matches = getattr(match_resp, "data", None) or []
        user_ids = [m.get("user_id") for m in matches if m.get("user_id")]
        profiles = self._fetch_profiles_map(user_ids)

        recommendations = []
        for m in matches:
            user_id = m.get("user_id")
            score = float(m.get("score") or 0.0)
            profile = profiles.get(str(user_id), {})
            email = profile.get("email") or "reviewer@example.com"
            name = profile.get("full_name") or email.split("@")[0].replace(".", " ").title()
            recommendations.append(
                {
                    "reviewer_id": str(user_id),
                    "name": name,
                    "email": email,
                    "match_score": max(0.0, min(1.0, score)),
                }
            )

        return {
            "recommendations": recommendations,
            "insufficient_data": False,
            "message": None,
        }

    def index_reviewer(self, user_id: str) -> None:
        """
        计算并写入 reviewer embedding（BackgroundTasks 调用）。

        中文注释:
        - 只允许服务端（service role）写入 reviewer_embeddings。
        - 通过 source_text_hash 做幂等，避免重复向量化。
        """

        config = self._config
        try:
            profile = (
                self._db.table("user_profiles")
                .select("id, email, full_name, affiliation, research_interests, roles")
                .eq("id", user_id)
                .single()
                .execute()
            )
            profile_data = getattr(profile, "data", None) or {}
        except Exception:
            profile_data = {}

        # 优先使用数组格式的 research_interests
        interests_data = profile_data.get("research_interests")
        if isinstance(interests_data, list):
            interests = ", ".join(interests_data)
        else:
            interests = str(interests_data or "").strip()

        history_titles: List[str] = []
        try:
            rr = (
                self._db.table("review_reports")
                .select("manuscript_id")
                .eq("reviewer_id", user_id)
                .limit(20)
                .execute()
            )
            rr_rows = getattr(rr, "data", None) or []
            ms_ids = [r.get("manuscript_id") for r in rr_rows if r.get("manuscript_id")]
            if ms_ids:
                ms = (
                    self._db.table("manuscripts")
                    .select("id, title")
                    .in_("id", ms_ids)
                    .execute()
                )
                ms_rows = getattr(ms, "data", None) or []
                history_titles = [m.get("title") for m in ms_rows if m.get("title")]
        except Exception:
            history_titles = []

        source_text = self._build_reviewer_source_text(interests=interests, history_titles=history_titles)
        source_hash = hash_source_text(source_text)

        # 若 hash 不变，跳过写入
        try:
            existing = (
                self._db.table("reviewer_embeddings")
                .select("source_text_hash")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            existing_hash = (getattr(existing, "data", None) or {}).get("source_text_hash")
            if existing_hash and existing_hash == source_hash:
                return
        except Exception:
            pass

        try:
            vector = self._embedder(source_text)
            if not isinstance(vector, list) or len(vector) != 384:
                print("[matchmaking] reviewer embedding generation failed: unexpected dimension")
                return
        except Exception as e:
            print(f"[matchmaking] failed to generate embedding for reviewer {user_id}: {e}")
            return

        payload = {
            "user_id": user_id,
            "embedding": _to_pgvector_literal(vector),
            "source_text_hash": source_hash,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            self._db.table("reviewer_embeddings").upsert(payload).execute()
        except Exception as e:
            print(f"[matchmaking] failed to upsert reviewer_embeddings: {e}")

    def _resolve_manuscript_text(
        self,
        *,
        manuscript_id: Optional[str],
        title: Optional[str],
        abstract: Optional[str],
    ) -> tuple[str, str]:
        resolved_title = (title or "").strip()
        resolved_abstract = (abstract or "").strip()

        if manuscript_id and (not resolved_title or not resolved_abstract):
            try:
                ms = (
                    self._db.table("manuscripts")
                    .select("title, abstract")
                    .eq("id", str(UUID(manuscript_id)))
                    .single()
                    .execute()
                )
                ms_data = getattr(ms, "data", None) or {}
                resolved_title = resolved_title or (ms_data.get("title") or "").strip()
                resolved_abstract = resolved_abstract or (ms_data.get("abstract") or "").strip()
            except Exception:
                # 留给后续校验兜底
                pass

        if not resolved_title and not resolved_abstract:
            raise HTTPException(status_code=422, detail="Either manuscript_id or (title/abstract) must be provided")

        return resolved_title, resolved_abstract

    @staticmethod
    def _build_manuscript_source_text(*, title: str, abstract: str) -> str:
        title_part = (title or "").strip()
        abstract_part = (abstract or "").strip()
        if abstract_part:
            return f"Title: {title_part}\n\nAbstract: {abstract_part}".strip()
        return f"Title: {title_part}".strip()

    @staticmethod
    def _build_reviewer_source_text(*, interests: str, history_titles: List[str]) -> str:
        parts = []
        if interests:
            parts.append(f"Research interests: {interests}")
        if history_titles:
            parts.append("Past reviewed manuscripts: " + ". ".join(history_titles))
        return "\n".join(parts).strip() or "General academic reviewer"

    def _fetch_profiles_map(self, user_ids: List[Any]) -> Dict[str, Dict[str, Any]]:
        if not user_ids:
            return {}

        ids = [str(uid) for uid in user_ids]

        # 尽量读取新增字段；若测试/环境未迁移，则自动降级。
        try:
            resp = (
                self._db.table("user_profiles")
                .select("id, email, full_name")
                .in_("id", ids)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
        except Exception:
            resp = (
                self._db.table("user_profiles")
                .select("id, email, roles")
                .in_("id", ids)
                .execute()
            )
            rows = getattr(resp, "data", None) or []

        return {str(r.get("id")): r for r in rows if r.get("id")}

