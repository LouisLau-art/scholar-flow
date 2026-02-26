from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException


def _parse_iso(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def _decode_attachment_ref(raw: str) -> tuple[str, str]:
    text = str(raw or "").strip()
    if "|" in text:
        attachment_id, path = text.split("|", 1)
        return attachment_id.strip(), path.strip()
    # 兼容旧数据：若只存了 path，则用 path 作为 id 占位
    return text, text


class DecisionServiceLettersMixin:
    def _list_submitted_reports(self, manuscript_id: str) -> list[dict[str, Any]]:
        resp = (
            self.client.table("review_reports")
            .select(
                "id,reviewer_id,status,score,comments_for_author,content,confidential_comments_to_editor,attachment_path,created_at"
            )
            .eq("manuscript_id", manuscript_id)
            .order("created_at", desc=True)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        submitted = [
            row
            for row in rows
            if str(row.get("status") or "").strip().lower()
            in {"submitted", "completed", "done"}
        ]

        reviewer_ids = sorted(
            {str(r.get("reviewer_id") or "") for r in submitted if r.get("reviewer_id")}
        )
        reviewer_map: dict[str, dict[str, Any]] = {}
        if reviewer_ids:
            try:
                p = (
                    self.client.table("user_profiles")
                    .select("id,full_name,email")
                    .in_("id", reviewer_ids)
                    .execute()
                )
                for item in (getattr(p, "data", None) or []):
                    rid = str(item.get("id") or "")
                    if rid:
                        reviewer_map[rid] = item
            except Exception:
                reviewer_map = {}

        normalized: list[dict[str, Any]] = []
        for idx, row in enumerate(submitted, start=1):
            rid = str(row.get("reviewer_id") or "")
            prof = reviewer_map.get(rid) or {}
            comments_for_author = str(
                row.get("comments_for_author") or row.get("content") or ""
            ).strip()
            attachment_path = str(row.get("attachment_path") or "").strip()
            attachment_id, _ = _decode_attachment_ref(attachment_path)
            normalized.append(
                {
                    "id": row.get("id"),
                    "reviewer_id": row.get("reviewer_id"),
                    "reviewer_name": prof.get("full_name") or f"Reviewer {idx}",
                    "reviewer_email": prof.get("email"),
                    "status": row.get("status"),
                    "score": row.get("score"),
                    "comments_for_author": comments_for_author,
                    "confidential_comments_to_editor": row.get(
                        "confidential_comments_to_editor"
                    ),
                    "attachment": (
                        {
                            "id": attachment_id,
                            "path": attachment_path,
                            "signed_url": self._signed_url("review-attachments", attachment_path),
                        }
                        if attachment_path
                        else None
                    ),
                    "created_at": row.get("created_at"),
                }
            )
        return normalized

    def _build_template(self, reports: list[dict[str, Any]]) -> str:
        parts: list[str] = [
            "Dear Author,",
            "",
            "Thank you for submitting your manuscript. Please find the editorial decision below.",
            "",
        ]
        for idx, report in enumerate(reports, start=1):
            comments = str(report.get("comments_for_author") or "").strip()
            parts.append(f"Reviewer {idx}:")
            parts.append(comments or "(No public comment provided)")
            parts.append("")
        parts.extend(
            [
                "Best regards,",
                "Editorial Office",
            ]
        )
        return "\n".join(parts)

    def _has_submitted_author_revision(self, manuscript_id: str) -> bool:
        """
        判断是否存在“作者已提交修回”记录。
        """
        rev_rows: list[dict[str, Any]] = []
        select_candidates = [
            ("id,status,submitted_at,updated_at,created_at", "updated_at"),
            ("id,status,submitted_at,created_at", "created_at"),
            ("id,status,submitted_at", None),
        ]
        for select_clause, order_key in select_candidates:
            try:
                q = (
                    self.client.table("revisions")
                    .select(select_clause)
                    .eq("manuscript_id", manuscript_id)
                )
                if order_key:
                    q = q.order(order_key, desc=True)
                rev = q.execute()
                rev_rows = getattr(rev, "data", None) or []
                break
            except Exception:
                continue
        if not rev_rows:
            return False

        for row in rev_rows:
            if str(row.get("status") or "").strip().lower() == "submitted":
                return True
            if row.get("submitted_at"):
                return True
        return False

    def _get_latest_letter(
        self, *, manuscript_id: str, editor_id: str, status: str | None = None
    ) -> dict[str, Any] | None:
        try:
            query = (
                self.client.table("decision_letters")
                .select(
                    "id,manuscript_id,manuscript_version,editor_id,content,decision,status,attachment_paths,created_at,updated_at"
                )
                .eq("manuscript_id", manuscript_id)
                .eq("editor_id", editor_id)
            )
            if status:
                query = query.eq("status", status)
            resp = query.order("updated_at", desc=True).limit(1).execute()
            rows = getattr(resp, "data", None) or []
            return rows[0] if rows else None
        except Exception as e:
            if "decision_letters" in str(e).lower() and "does not exist" in str(e).lower():
                raise HTTPException(
                    status_code=500, detail="DB not migrated: decision_letters table missing"
                ) from e
            raise

    def _save_letter(
        self,
        *,
        existing: dict[str, Any] | None,
        manuscript_id: str,
        manuscript_version: int,
        editor_id: str,
        content: str,
        decision: str,
        status: str,
        attachment_paths: list[str],
        last_updated_at: datetime | None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()

        def _is_conflict(existing_row: dict[str, Any]) -> bool:
            if last_updated_at is None:
                return False
            db_updated = _parse_iso(existing_row.get("updated_at"))
            if db_updated is None:
                return False
            return int(db_updated.timestamp() * 1000) != int(last_updated_at.timestamp() * 1000)

        if existing:
            if _is_conflict(existing):
                raise HTTPException(
                    status_code=409,
                    detail="Draft conflict: letter has been modified by another session",
                )
            payload = {
                "content": content,
                "decision": decision,
                "status": status,
                "manuscript_version": manuscript_version,
                "attachment_paths": attachment_paths,
                "updated_at": now,
            }
            resp = (
                self.client.table("decision_letters")
                .update(payload)
                .eq("id", existing["id"])
                .execute()
            )
            rows = getattr(resp, "data", None) or []
            if not rows:
                raise HTTPException(status_code=500, detail="Failed to update decision letter")
            return rows[0]

        payload = {
            "manuscript_id": manuscript_id,
            "manuscript_version": manuscript_version,
            "editor_id": editor_id,
            "content": content,
            "decision": decision,
            "status": status,
            "attachment_paths": attachment_paths,
            "created_at": now,
            "updated_at": now,
        }
        resp = self.client.table("decision_letters").insert(payload).execute()
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=500, detail="Failed to create decision letter")
        return rows[0]
