from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.lib.api_client import supabase_admin
from app.services.notification_service import NotificationService


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_single_no_rows_error(error_text: str) -> bool:
    lowered = (error_text or "").lower()
    return (
        "pgrst116" in lowered
        or "cannot coerce the result to a single json object" in lowered
        or "0 rows" in lowered
    )


def _is_missing_table_error(error_text: str) -> bool:
    lowered = (error_text or "").lower()
    return (
        "pgrst205" in lowered
        or "schema cache" in lowered
        or "does not exist" in lowered
        or "relation" in lowered
    )


class PlagiarismService:
    """
    查重报告服务（GAP-P2-02）。

    中文注释:
    - 统一负责 plagiarism_reports 的落库与读取。
    - 将“高相似度预警”写入审计日志，并通知内部角色。
    """

    def __init__(self, *, client: Any | None = None):
        self.client = client or supabase_admin
        self.notification_service = NotificationService()

    def get_report_by_manuscript(self, manuscript_id: str) -> Optional[dict[str, Any]]:
        try:
            resp = (
                self.client.table("plagiarism_reports")
                .select("*")
                .eq("manuscript_id", manuscript_id)
                .single()
                .execute()
            )
            return getattr(resp, "data", None) or None
        except Exception as e:
            if _is_single_no_rows_error(str(e)):
                return None
            if _is_missing_table_error(str(e)):
                raise RuntimeError("DB not migrated: plagiarism_reports table missing") from e
            raise

    def get_report_by_id(self, report_id: str) -> Optional[dict[str, Any]]:
        try:
            resp = (
                self.client.table("plagiarism_reports")
                .select("*")
                .eq("id", report_id)
                .single()
                .execute()
            )
            return getattr(resp, "data", None) or None
        except Exception as e:
            if _is_single_no_rows_error(str(e)):
                return None
            if _is_missing_table_error(str(e)):
                raise RuntimeError("DB not migrated: plagiarism_reports table missing") from e
            raise

    def ensure_report(self, manuscript_id: str, *, reset_status: bool = False) -> dict[str, Any]:
        now = _now_iso()
        existing = self.get_report_by_manuscript(manuscript_id)

        if existing and not reset_status:
            return existing

        payload: dict[str, Any] = {
            "manuscript_id": manuscript_id,
            "updated_at": now,
        }

        if existing is None:
            payload.update(
                {
                    "status": "pending",
                    "retry_count": 0,
                    "error_log": None,
                    "external_id": None,
                }
            )
        elif reset_status:
            payload.update(
                {
                    "id": existing.get("id"),
                    "status": "pending",
                    "error_log": None,
                    "external_id": None,
                }
            )

        resp = (
            self.client.table("plagiarism_reports")
            .upsert(payload, on_conflict="manuscript_id")
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if rows:
            return rows[0]

        latest = self.get_report_by_manuscript(manuscript_id)
        if latest:
            return latest

        raise RuntimeError("Failed to initialize plagiarism report")

    def mark_running(self, manuscript_id: str, *, external_id: str) -> dict[str, Any]:
        self.ensure_report(manuscript_id)
        resp = (
            self.client.table("plagiarism_reports")
            .update(
                {
                    "status": "running",
                    "external_id": external_id,
                    "error_log": None,
                    "updated_at": _now_iso(),
                }
            )
            .eq("manuscript_id", manuscript_id)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        return rows[0] if rows else self.get_report_by_manuscript(manuscript_id) or {}

    def mark_completed(
        self,
        manuscript_id: str,
        *,
        similarity_score: float,
        report_url: str,
        external_id: str,
    ) -> dict[str, Any]:
        self.ensure_report(manuscript_id)
        resp = (
            self.client.table("plagiarism_reports")
            .update(
                {
                    "status": "completed",
                    "similarity_score": similarity_score,
                    "report_url": report_url,
                    "external_id": external_id,
                    "error_log": None,
                    "updated_at": _now_iso(),
                }
            )
            .eq("manuscript_id", manuscript_id)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        return rows[0] if rows else self.get_report_by_manuscript(manuscript_id) or {}

    def mark_failed(
        self,
        manuscript_id: str,
        *,
        error_message: str,
        increment_retry: bool = True,
    ) -> dict[str, Any]:
        existing = self.ensure_report(manuscript_id)
        retry_count = int(existing.get("retry_count") or 0)
        if increment_retry:
            retry_count += 1

        resp = (
            self.client.table("plagiarism_reports")
            .update(
                {
                    "status": "failed",
                    "error_log": str(error_message or "")[:2000],
                    "retry_count": retry_count,
                    "updated_at": _now_iso(),
                }
            )
            .eq("manuscript_id", manuscript_id)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        return rows[0] if rows else self.get_report_by_manuscript(manuscript_id) or {}

    def get_download_url(self, report: dict[str, Any], *, expires_in: int = 600) -> str:
        report_url = str(report.get("report_url") or "").strip()
        if not report_url:
            raise RuntimeError("Report URL not available")

        if report_url.startswith("http://") or report_url.startswith("https://"):
            return report_url

        signed = self.client.storage.from_("plagiarism-reports").create_signed_url(
            report_url,
            expires_in,
        )
        url = (signed or {}).get("signedUrl") or (signed or {}).get("signedURL")
        if not url:
            raise RuntimeError("Failed to create signed URL")
        return str(url)

    def _load_manuscript_context(self, manuscript_id: str) -> dict[str, Any]:
        try:
            resp = (
                self.client.table("manuscripts")
                .select("id,title,status,author_id,owner_id,editor_id")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            return getattr(resp, "data", None) or {}
        except Exception:
            return {}

    def record_high_similarity_alert(
        self,
        *,
        manuscript_id: str,
        similarity_score: float,
        threshold: float,
    ) -> None:
        manuscript = self._load_manuscript_context(manuscript_id)
        from_status = str(manuscript.get("status") or "")

        # 中文注释: 不中断主流程，尽力写审计。
        try:
            self.client.table("status_transition_logs").insert(
                {
                    "manuscript_id": manuscript_id,
                    "from_status": from_status,
                    "to_status": from_status,
                    "comment": "plagiarism high similarity alert",
                    "changed_by": None,
                    "created_at": _now_iso(),
                    "payload": {
                        "action": "plagiarism_high_similarity_alert",
                        "similarity_score": similarity_score,
                        "threshold": threshold,
                        "risk_level": "high",
                    },
                }
            ).execute()
        except Exception:
            pass

        target_users: list[str] = []
        for key in ("owner_id", "editor_id"):
            uid = str(manuscript.get(key) or "").strip()
            if uid and uid not in target_users:
                target_users.append(uid)

        title = str(manuscript.get("title") or "Untitled").strip() or "Untitled"
        for user_id in target_users:
            self.notification_service.create_notification(
                user_id=user_id,
                manuscript_id=manuscript_id,
                type="system",
                title="High Similarity Alert",
                content=(
                    f"稿件《{title}》查重结果为 {similarity_score:.1%}，"
                    f"超过阈值 {threshold:.1%}，请尽快复核。"
                ),
            )
