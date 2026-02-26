from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi.responses import Response

from app.services.storage_service import create_signed_url

from fastapi import HTTPException
from app.models.revision import VersionHistoryResponse
from app.services.revision_service import RevisionService


def _safe_iso(raw: object | None) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def _try_parse_dt(raw: object | None) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:
        return None


def _timestamp_or_now(raw: object | None) -> datetime:
    parsed = _try_parse_dt(raw)
    return parsed or datetime.now(timezone.utc)


def _sign_storage_url(*, bucket: str, path: str, expires_in_sec: int = 60 * 5) -> str | None:
    path = str(path or "").strip()
    if not path:
        return None
    try:
        return create_signed_url(bucket=bucket, path=path, expires_in=expires_in_sec).url
    except Exception:
        return None


def _normalize_html_preview(html: str, *, max_chars: int = 400) -> str:
    text = str(html or "").strip()
    if not text:
        return ""
    # 中文注释: response_letter 可能包含 base64 图片，作者侧时间线先展示摘要，避免页面卡顿。
    # 详情可在前端点击“展开”后再渲染完整内容。
    text = text.replace("\n", " ")
    return (text[:max_chars] + "…") if len(text) > max_chars else text


AUTHOR_VISIBLE_TRANSITION_ACTIONS: set[str] = {
    # ME intake / AE technical return
    "precheck_intake_revision",
    "precheck_technical_revision",
    # revision request from decision/review
    "request_revision",
    "decision_revision",
    # final decisions
    "decision_final_accept",
    "decision_final_reject",
    "decision_final_minor_revision",
    "decision_final_major_revision",
    # production steps (some are author visible)
    "production_proof_request",
    "production_proof_submitted",
}


def _normalize_status_for_author(raw: object | None) -> str:
    from app.api.v1.manuscripts import _normalize_private_progress_status

    return _normalize_private_progress_status(raw)


def _humanize_status(status: str) -> str:
    mapping = {
        "submitted": "投稿",
        "pre_check": "预审",
        "under_review": "外审中",
        "revision_requested": "需要修回",
        "resubmitted": "作者已修回",
        "decision": "待决策",
        "decision_done": "决策完成",
        "approved": "已录用",
        "layout": "排版中",
        "english_editing": "英文编辑",
        "proofreading": "校对中",
        "published": "已发布",
        "rejected": "已拒稿",
    }
    key = str(status or "").strip().lower()
    return mapping.get(key, key.replace("_", " ") or "未知")


def _humanize_decision(decision: str) -> str:
    mapping = {
        "accept": "接收",
        "reject": "拒稿",
        "minor_revision": "小修",
        "major_revision": "大修",
    }
    key = str(decision or "").strip().lower()
    return mapping.get(key, key.replace("_", " ") or "未知")


def _missing_column_from_error(error: Exception, *, column: str) -> bool:
    text = str(error or "").lower()
    col = str(column or "").strip().lower()
    return bool(col and col in text and ("does not exist" in text or "schema cache" in text or "pgrst" in text))


def _load_transition_logs(manuscript_id: str) -> list[dict]:
    select_variants = [
        "from_status,to_status,comment,created_at,changed_by,payload",
        "from_status,to_status,comment,created_at,changed_by",
        "from_status,to_status,comment,created_at",
    ]
    for cols in select_variants:
        try:
            resp = (
                _m()
                .supabase_admin.table("status_transition_logs")
                .select(cols)
                .eq("manuscript_id", manuscript_id)
                .order("created_at", desc=False)
                .limit(500)
                .execute()
            )
            return getattr(resp, "data", None) or []
        except Exception as e:
            lowered = str(e).lower()
            if "status_transition_logs" in lowered and ("does not exist" in lowered or "schema cache" in lowered or "pgrst205" in lowered):
                return []
            # 缺列则尝试下一种 select
            continue
    return []


def _load_revisions(manuscript_id: str) -> list[dict]:
    try:
        resp = (
            _m()
            .supabase_admin.table("revisions")
            .select(
                "id,round_number,decision_type,editor_comment,response_letter,status,created_at,submitted_at,updated_at"
            )
            .eq("manuscript_id", manuscript_id)
            .order("round_number", desc=False)
            .limit(200)
            .execute()
        )
        return getattr(resp, "data", None) or []
    except Exception as e:
        lowered = str(e).lower()
        if "revisions" in lowered and ("does not exist" in lowered or "schema cache" in lowered or "pgrst205" in lowered):
            return []
        return []


def _load_versions(manuscript_id: str) -> list[dict]:
    try:
        resp = (
            _m()
            .supabase_admin.table("manuscript_versions")
            .select("id,version_number,file_path,created_at")
            .eq("manuscript_id", manuscript_id)
            .order("version_number", desc=False)
            .limit(200)
            .execute()
        )
        return getattr(resp, "data", None) or []
    except Exception as e:
        lowered = str(e).lower()
        if "manuscript_versions" in lowered and ("does not exist" in lowered or "schema cache" in lowered or "pgrst205" in lowered):
            return []
        return []


def _load_review_reports(manuscript_id: str) -> list[dict]:
    select_variants = [
        "id,reviewer_id,status,comments_for_author,content,attachment_path,created_at,updated_at",
        "id,reviewer_id,status,comments_for_author,content,attachment_path,created_at",
        "id,reviewer_id,status,content,attachment_path,created_at",
    ]
    for cols in select_variants:
        try:
            resp = (
                _m()
                .supabase_admin.table("review_reports")
                .select(cols)
                .eq("manuscript_id", manuscript_id)
                .order("created_at", desc=False)
                .limit(500)
                .execute()
            )
            return getattr(resp, "data", None) or []
        except Exception:
            continue
    return []


def _load_final_decision_letters(manuscript_id: str) -> list[dict]:
    try:
        resp = (
            _m()
            .supabase_admin.table("decision_letters")
            .select("id,decision,status,content,attachment_paths,created_at,updated_at")
            .eq("manuscript_id", manuscript_id)
            .eq("status", "final")
            .order("updated_at", desc=False)
            .limit(50)
            .execute()
        )
        return getattr(resp, "data", None) or []
    except Exception as e:
        lowered = str(e).lower()
        if "decision_letters" in lowered and ("does not exist" in lowered or "schema cache" in lowered or "pgrst205" in lowered):
            return []
        return []


def _load_cover_letter_files(manuscript_id: str) -> list[dict]:
    try:
        resp = (
            _m()
            .supabase_admin.table("manuscript_files")
            .select("id,file_type,bucket,path,original_filename,content_type,created_at,uploaded_by")
            .eq("manuscript_id", manuscript_id)
            .eq("file_type", "cover_letter")
            .order("created_at", desc=False)
            .limit(10)
            .execute()
        )
        return getattr(resp, "data", None) or []
    except Exception as e:
        lowered = str(e).lower()
        if "manuscript_files" in lowered and ("does not exist" in lowered or "schema cache" in lowered or "pgrst205" in lowered):
            return []
        return []


def _load_latest_author_proofreading_task(manuscript_id: str, author_id: str) -> dict | None:
    """
    Feature 042: 作者侧校对任务入口（awaiting_author / 提交后回看）。

    中文注释:
    - 这里不做签名 URL（作者真正进入 /proofreading/{id} 页面再取 context）。
    - 若云端缺表/未迁移，保守返回 None，避免阻塞作者侧时间线。
    """
    try:
        resp = (
            _m()
            .supabase_admin.table("production_cycles")
            .select("id,manuscript_id,cycle_no,status,proof_due_at,updated_at")
            .eq("manuscript_id", manuscript_id)
            .eq("proofreader_author_id", author_id)
            .in_("status", ["awaiting_author", "author_confirmed", "author_corrections_submitted"])
            .order("cycle_no", desc=True)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            return None
        row = rows[0]
        status = str(row.get("status") or "").strip()
        return {
            "cycle_id": row.get("id"),
            "cycle_no": row.get("cycle_no"),
            "status": status,
            "proof_due_at": row.get("proof_due_at"),
            "action_required": status == "awaiting_author",
            "url": f"/proofreading/{manuscript_id}",
        }
    except Exception as e:
        lowered = str(e).lower()
        if "production_cycles" in lowered and (
            "does not exist" in lowered or "schema cache" in lowered or "pgrst205" in lowered
        ):
            return None
        return None

