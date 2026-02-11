from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Iterable
from uuid import UUID

from fastapi import HTTPException

from app.lib.api_client import supabase_admin
from app.services.notification_service import NotificationService


INTERNAL_COLLAB_ROLES = {
    "admin",
    "assistant_editor",
    "managing_editor",
    "editor_in_chief",
}


@dataclass
class MentionValidationError(Exception):
    invalid_user_ids: list[str]


@dataclass
class InternalCollaborationSchemaMissingError(Exception):
    table: str


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_rows(resp: Any) -> list[dict[str, Any]]:
    return getattr(resp, "data", None) or []


def _extract_single(resp: Any) -> dict[str, Any] | None:
    rows = _extract_rows(resp)
    return rows[0] if rows else None


def _error_text_blob(error: Exception | str | None) -> str:
    """
    统一拼接异常文本，兼容部分 SDK 异常 str(e) 为空、但 repr/args 有内容的场景。
    """
    if error is None:
        return ""
    if isinstance(error, str):
        return error
    parts: list[str] = []
    try:
        s = str(error)
        if s:
            parts.append(s)
    except Exception:
        pass
    try:
        r = repr(error)
        if r:
            parts.append(r)
    except Exception:
        pass
    try:
        args = getattr(error, "args", None) or []
        for item in args:
            v = str(item)
            if v:
                parts.append(v)
    except Exception:
        pass
    return " | ".join(parts)


def _missing_table_from_error(error: Exception | str | None) -> str | None:
    text = _error_text_blob(error)
    lowered = text.lower()
    missing_markers = (
        "does not exist",
        "schema cache",
        "could not find the table",
        "pgrst205",
    )
    for table in ("internal_comments", "internal_comment_mentions", "internal_tasks", "internal_task_activity_logs"):
        # 兼容 Postgres/PGRST 两类缺表错误文案
        if table in lowered and any(marker in lowered for marker in missing_markers):
            return table
        if f"public.{table}" in lowered and any(marker in lowered for marker in missing_markers):
            return table

    # 兼容消息中出现 table/relation + public.<table>，支持单引号/双引号/无引号
    match = re.search(r"(?:table|relation)\s+['\"]?public\.([a-z_]+)['\"]?", lowered)
    if match:
        table_name = str(match.group(1) or "").strip()
        if table_name in {"internal_comments", "internal_comment_mentions", "internal_tasks", "internal_task_activity_logs"}:
            if any(marker in lowered for marker in missing_markers):
                return table_name
    return None


def _extract_missing_mentioned_user_id_from_fk_error(error: Exception | str | None) -> str | None:
    """
    解析 FK 报错中的 mentioned_user_id，便于返回可读的 422。
    典型文案:
    Key (mentioned_user_id)=(<uuid>) is not present in table "users".
    """
    text = _error_text_blob(error)
    match = re.search(r"mentioned_user_id\)=\(([0-9a-fA-F-]{36})\)", text)
    if not match:
        return None
    value = str(match.group(1) or "").strip()
    try:
        return str(UUID(value))
    except Exception:
        return None


class InternalCollaborationService:
    """
    Feature 045: Internal notebook mentions + mention notifications.

    中文注释:
    - 评论主记录沿用 `internal_comments`。
    - 提及关系落在 `internal_comment_mentions`，避免解析正文的歧义。
    - 通知按去重后的 mention user ids 投递一次，避免通知轰炸。
    """

    def __init__(self, *, client: Any = None, notification_service: NotificationService | None = None) -> None:
        self.client = client or supabase_admin
        self.notifications = notification_service or NotificationService()

    def _normalize_mention_ids(self, user_ids: Iterable[str] | None) -> list[str]:
        if not user_ids:
            return []
        dedup: list[str] = []
        seen: set[str] = set()
        invalid: list[str] = []
        for raw in user_ids:
            value = str(raw or "").strip()
            if not value:
                continue
            try:
                normalized = str(UUID(value))
            except Exception:
                invalid.append(value)
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            dedup.append(normalized)
        if invalid:
            raise MentionValidationError(invalid_user_ids=invalid)
        return dedup

    def _is_internal_profile(self, profile: dict[str, Any]) -> bool:
        roles = profile.get("roles") or []
        if isinstance(roles, str):
            roles = [roles]
        role_set = {str(role).strip().lower() for role in roles if str(role).strip()}
        return bool(role_set.intersection(INTERNAL_COLLAB_ROLES))

    def _load_profiles_map(self, user_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not user_ids:
            return {}
        try:
            resp = (
                self.client.table("user_profiles")
                .select("id,full_name,email,roles")
                .in_("id", user_ids)
                .execute()
            )
            rows = _extract_rows(resp)
            return {str(row.get("id")): row for row in rows if row.get("id")}
        except Exception:
            return {}

    def _validate_mention_targets(self, mention_user_ids: list[str]) -> list[str]:
        if not mention_user_ids:
            return []
        profiles_map = self._load_profiles_map(mention_user_ids)
        invalid = [uid for uid in mention_user_ids if uid not in profiles_map or not self._is_internal_profile(profiles_map[uid])]
        if invalid:
            raise MentionValidationError(invalid_user_ids=invalid)
        return mention_user_ids

    def list_comments(self, manuscript_id: str) -> list[dict[str, Any]]:
        try:
            resp = (
                self.client.table("internal_comments")
                .select("id,manuscript_id,content,created_at,user_id")
                .eq("manuscript_id", manuscript_id)
                .order("created_at", desc=False)
                .execute()
            )
        except Exception as e:
            table = _missing_table_from_error(e)
            if table == "internal_comments":
                return []
            # 兼容部分 SDK 抛错文本不带明确表名，但已明确是 schema cache 缺表
            lowered = _error_text_blob(e).lower()
            if "could not find the table" in lowered and "schema cache" in lowered:
                return []
            if table:
                raise InternalCollaborationSchemaMissingError(table=table) from e
            raise

        comments = _extract_rows(resp)
        if not comments:
            return []

        comment_ids = [str(row.get("id")) for row in comments if row.get("id")]
        mention_map: dict[str, list[str]] = {cid: [] for cid in comment_ids}

        if comment_ids:
            try:
                mention_resp = (
                    self.client.table("internal_comment_mentions")
                    .select("comment_id,mentioned_user_id")
                    .in_("comment_id", comment_ids)
                    .execute()
                )
                for row in _extract_rows(mention_resp):
                    cid = str(row.get("comment_id") or "")
                    uid = str(row.get("mentioned_user_id") or "")
                    if not cid or not uid:
                        continue
                    mention_map.setdefault(cid, [])
                    if uid not in mention_map[cid]:
                        mention_map[cid].append(uid)
            except Exception as e:
                if _missing_table_from_error(e) != "internal_comment_mentions":
                    raise

        user_ids = sorted({str(row.get("user_id")) for row in comments if row.get("user_id")})
        profiles_map = self._load_profiles_map(user_ids)

        for row in comments:
            cid = str(row.get("id") or "")
            uid = str(row.get("user_id") or "")
            row["mention_user_ids"] = mention_map.get(cid, [])
            row["user"] = profiles_map.get(uid) or {"full_name": "Unknown", "email": ""}

        return comments

    def create_comment(
        self,
        *,
        manuscript_id: str,
        author_user_id: str,
        content: str,
        mention_user_ids: Iterable[str] | None,
    ) -> dict[str, Any]:
        body = (content or "").strip()
        if not body:
            raise HTTPException(status_code=400, detail="Content cannot be empty")

        normalized_mentions = self._normalize_mention_ids(mention_user_ids)
        validated_mentions = [
            uid for uid in self._validate_mention_targets(normalized_mentions) if uid != author_user_id
        ]

        now = _iso_now()
        payload = {
            "manuscript_id": manuscript_id,
            "user_id": author_user_id,
            "content": body,
            "created_at": now,
            "updated_at": now,
        }

        try:
            ins = self.client.table("internal_comments").insert(payload).execute()
        except Exception as e:
            table = _missing_table_from_error(e)
            if table:
                raise InternalCollaborationSchemaMissingError(table=table) from e
            raise

        comment = _extract_single(ins) or {**payload, "id": None}
        comment_id = str(comment.get("id") or "")

        if validated_mentions:
            mention_rows = [
                {
                    "comment_id": comment_id,
                    "manuscript_id": manuscript_id,
                    "mentioned_user_id": user_id,
                    "mentioned_by_user_id": author_user_id,
                    "created_at": now,
                }
                for user_id in validated_mentions
                if user_id
            ]
            if mention_rows:
                try:
                    self.client.table("internal_comment_mentions").insert(mention_rows).execute()
                except Exception as e:
                    text = _error_text_blob(e).lower()
                    if (
                        "23503" in text
                        and "internal_comment_mentions_mentioned_user_id_fkey" in text
                    ) or ("foreign key" in text and "mentioned_user_id" in text):
                        missing_uid = _extract_missing_mentioned_user_id_from_fk_error(e)
                        if missing_uid:
                            raise MentionValidationError(invalid_user_ids=[missing_uid]) from e
                        raise MentionValidationError(invalid_user_ids=validated_mentions) from e
                    table = _missing_table_from_error(e)
                    if table:
                        raise InternalCollaborationSchemaMissingError(table=table) from e
                    raise

                snippet = body if len(body) <= 160 else f"{body[:157]}..."
                for user_id in {str(row["mentioned_user_id"]) for row in mention_rows}:
                    self.notifications.create_notification(
                        user_id=user_id,
                        manuscript_id=manuscript_id,
                        action_url=f"/editor/manuscript/{manuscript_id}",
                        type="system",
                        title="You were mentioned in Internal Notebook",
                        content=snippet,
                    )

        profiles_map = self._load_profiles_map([author_user_id])
        comment["mention_user_ids"] = validated_mentions
        comment["user"] = profiles_map.get(author_user_id) or {"full_name": "Unknown", "email": ""}
        return comment
