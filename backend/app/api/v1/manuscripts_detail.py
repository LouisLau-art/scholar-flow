from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi.responses import Response

from app.services.storage_service import create_signed_url

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth_utils import get_current_user
from app.core.roles import get_current_profile
from app.models.revision import VersionHistoryResponse
from app.services.revision_service import RevisionService

router = APIRouter(tags=["Manuscripts"])


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


@router.get("/manuscripts/{manuscript_id}/author-context")
async def get_manuscript_author_context(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    作者视角：稿件时间线（匿名审稿）+ 文件下载上下文。

    中文注释:
    - 这是作者侧“对账单据”的核心入口：所有对作者可见的 comment 都应在这里可追溯。
    - Reviewer 严格匿名：不返回 reviewer_id/full_name/email，不泄露附件 object key。
    """
    user_id = str(current_user.get("id") or "").strip()
    roles = set((profile or {}).get("roles") or [])

    try:
        ms_resp = (
            _m()
            .supabase_admin.table("manuscripts")
            .select("id,title,status,created_at,updated_at,author_id,file_path,journal_id")
            .eq("id", str(manuscript_id))
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}
    except Exception as e:
        if _m()._is_postgrest_single_no_rows_error(str(e)):
            raise HTTPException(status_code=404, detail="Manuscript not found")
        raise
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    author_id = str(ms.get("author_id") or "").strip()
    is_author = bool(author_id and author_id == user_id)
    is_internal = bool(roles.intersection({"admin", "managing_editor"}))
    if not (is_author or is_internal):
        raise HTTPException(status_code=403, detail="Forbidden")

    manuscript_id_str = str(manuscript_id)

    versions = _load_versions(manuscript_id_str)
    revisions = _load_revisions(manuscript_id_str)
    logs = _load_transition_logs(manuscript_id_str)
    review_reports = _load_review_reports(manuscript_id_str)
    decision_letters = _load_final_decision_letters(manuscript_id_str)
    cover_letters = _load_cover_letter_files(manuscript_id_str)

    # Reviewer 匿名编号
    reviewer_index: dict[str, int] = {}
    next_idx = 1
    for row in review_reports:
        rid = str(row.get("reviewer_id") or "").strip()
        if not rid:
            continue
        if rid not in reviewer_index:
            reviewer_index[rid] = next_idx
            next_idx += 1

    events: list[dict] = []

    # 1) Submission
    events.append(
        {
            "id": f"submission-{manuscript_id_str}",
            "timestamp": _safe_iso(ms.get("created_at")) or "",
            "actor": "author",
            "title": "投稿已提交",
            "message": "",
            "attachments": [],
        }
    )

    # 2) 状态流转（含作者可见 comment）
    for row in logs:
        from_status = _normalize_status_for_author(row.get("from_status"))
        to_status = _normalize_status_for_author(row.get("to_status"))
        ts = _safe_iso(row.get("created_at")) or ""
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        action = str(payload.get("action") or "").strip().lower()
        event_type = str(payload.get("event_type") or "").strip().lower()
        comment = str(row.get("comment") or "").strip()

        show_comment = False
        if action in AUTHOR_VISIBLE_TRANSITION_ACTIONS:
            show_comment = True
        if event_type in {"proofreading_submitted"}:
            show_comment = True
        if to_status in {"minor_revision", "major_revision", "revision_requested", "rejected", "approved", "published"}:
            show_comment = True

        title = f"状态更新：{_humanize_status(from_status) if from_status else '—'} → {_humanize_status(to_status)}"
        message = comment if (show_comment and comment) else ""

        events.append(
            {
                "id": f"log-{row.get('id') or ts}-{to_status}",
                "timestamp": ts,
                "actor": "system" if not comment else "editorial",
                "title": title,
                "message": message,
                "attachments": [],
            }
        )

    # 3) 修回请求 / 作者修回提交（确保可追溯）
    for row in revisions:
        rid = str(row.get("id") or "").strip()
        round_no = row.get("round_number")
        decision_type = str(row.get("decision_type") or "").strip().lower()
        editor_comment = str(row.get("editor_comment") or "").strip()
        response_letter = str(row.get("response_letter") or "").strip()
        status = str(row.get("status") or "").strip().lower()

        created_at = _safe_iso(row.get("created_at") or row.get("updated_at")) or ""
        submitted_at = _safe_iso(row.get("submitted_at") or row.get("updated_at")) or ""

        if editor_comment:
            events.append(
                {
                    "id": f"revision-request-{rid}",
                    "timestamp": created_at,
                    "actor": "editorial",
                    "title": f"编辑请求{_humanize_decision(decision_type + '_revision' if decision_type else 'revision')}",
                    "message": editor_comment,
                    "attachments": [],
                }
            )

        if status == "submitted" and (response_letter or submitted_at):
            version_no: int | None = None
            try:
                if isinstance(round_no, int):
                    version_no = round_no + 1
            except Exception:
                version_no = None
            attachments: list[dict] = []
            if version_no:
                attachments.append(
                    {
                        "type": "manuscript_pdf",
                        "label": f"修回稿 PDF (v{version_no})",
                        "download_url": f"/api/v1/manuscripts/{manuscript_id_str}/versions/{version_no}/pdf-signed",
                    }
                )
            events.append(
                {
                    "id": f"revision-submit-{rid}",
                    "timestamp": submitted_at,
                    "actor": "author",
                    "title": f"作者提交修回（第 {round_no or '?'} 轮）",
                    "message": response_letter,
                    "attachments": attachments,
                }
            )

    # 4) 审稿意见（匿名）
    for row in review_reports:
        status = str(row.get("status") or "").strip().lower()
        if status not in {"completed", "submitted"}:
            continue
        rid = str(row.get("reviewer_id") or "").strip()
        idx = reviewer_index.get(rid, 0) if rid else 0
        label = f"审稿人 #{idx}" if idx else "审稿人"
        report_id = str(row.get("id") or "").strip()
        ts = _safe_iso(row.get("updated_at") or row.get("created_at")) or ""
        public_text = str(row.get("comments_for_author") or row.get("content") or "").strip()
        attachment_path = str(row.get("attachment_path") or "").strip()
        attachments: list[dict] = []
        if attachment_path and report_id:
            attachments.append(
                {
                    "type": "review_attachment",
                    "label": f"{label} 附件",
                    "download_url": f"/api/v1/manuscripts/{manuscript_id_str}/review-reports/{report_id}/author-attachment",
                }
            )
        events.append(
            {
                "id": f"review-{report_id}",
                "timestamp": ts,
                "actor": "reviewer",
                "title": f"{label} 意见",
                "message": public_text,
                "attachments": attachments,
            }
        )

    # 5) Final decision letters（作者可见）
    for row in decision_letters:
        letter_id = str(row.get("id") or "").strip()
        decision = str(row.get("decision") or "").strip().lower()
        content = str(row.get("content") or "").strip()
        ts = _safe_iso(row.get("updated_at") or row.get("created_at")) or ""
        attachments: list[dict] = []
        paths = row.get("attachment_paths") if isinstance(row.get("attachment_paths"), list) else []
        for raw in paths:
            ref = str(raw or "").strip()
            if "|" not in ref:
                continue
            attachment_id = ref.split("|", 1)[0].strip()
            if not attachment_id:
                continue
            attachments.append(
                {
                    "type": "decision_attachment",
                    "label": "决策附件",
                    "signed_url_api": f"/api/v1/manuscripts/{manuscript_id_str}/decision-attachments/{attachment_id}/signed-url",
                }
            )
        events.append(
            {
                "id": f"decision-{letter_id}",
                "timestamp": ts,
                "actor": "editorial",
                "title": f"最终决定：{_humanize_decision(decision)}",
                "message": content,
                "attachments": attachments,
            }
        )

    # 排序：按 timestamp 升序（作者看流程更直观）
    def _sort_key(item: dict) -> datetime:
        return _timestamp_or_now(item.get("timestamp"))

    events.sort(key=_sort_key)

    cover_letter_items: list[dict] = []
    for row in cover_letters:
        bucket = str(row.get("bucket") or "manuscripts")
        path = str(row.get("path") or "").strip()
        if not path:
            continue
        cover_letter_items.append(
            {
                "id": str(row.get("id") or ""),
                "filename": str(row.get("original_filename") or "cover_letter"),
                "content_type": row.get("content_type"),
                "created_at": _safe_iso(row.get("created_at")),
                "signed_url": _sign_storage_url(bucket=bucket, path=path, expires_in_sec=60 * 10),
            }
        )

    current_pdf_url = _sign_storage_url(bucket="manuscripts", path=str(ms.get("file_path") or ""), expires_in_sec=60 * 10)
    proofreading_task = _load_latest_author_proofreading_task(manuscript_id_str, author_id=user_id)

    return {
        "success": True,
        "data": {
            "manuscript": {
                "id": manuscript_id_str,
                "title": ms.get("title") or "Untitled",
                "status": ms.get("status"),
                "status_label": _humanize_status(_normalize_status_for_author(ms.get("status"))),
                "created_at": _safe_iso(ms.get("created_at")),
                "updated_at": _safe_iso(ms.get("updated_at")),
            },
            "files": {
                "current_pdf_signed_url": current_pdf_url,
                "cover_letters": cover_letter_items,
            },
            "proofreading_task": proofreading_task,
            "timeline": events,
        },
    }


@router.get("/manuscripts/{manuscript_id}/review-reports/{report_id}/author-attachment")
async def download_review_attachment_for_author(
    manuscript_id: UUID,
    report_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    作者下载审稿附件（匿名，不泄露 storage object key）。
    """
    user_id = str(current_user.get("id") or "").strip()
    roles = set((profile or {}).get("roles") or [])

    ms_resp = (
        _m()
        .supabase_admin.table("manuscripts")
        .select("id,author_id")
        .eq("id", str(manuscript_id))
        .single()
        .execute()
    )
    ms = getattr(ms_resp, "data", None) or {}
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    author_id = str(ms.get("author_id") or "").strip()
    is_author = bool(author_id and author_id == user_id)
    is_internal = bool(roles.intersection({"admin", "managing_editor"}))
    if not (is_author or is_internal):
        raise HTTPException(status_code=403, detail="Forbidden")

    rr_resp = (
        _m()
        .supabase_admin.table("review_reports")
        .select("id,manuscript_id,attachment_path")
        .eq("id", str(report_id))
        .eq("manuscript_id", str(manuscript_id))
        .single()
        .execute()
    )
    rr = getattr(rr_resp, "data", None) or {}
    if not rr:
        raise HTTPException(status_code=404, detail="Review report not found")

    path = str(rr.get("attachment_path") or "").strip()
    if not path:
        raise HTTPException(status_code=404, detail="No attachment for this review report")

    # 通过 signed URL 在服务端拉取后转发，避免把 object key 暴露给作者。
    signed = _sign_storage_url(bucket="review-attachments", path=path, expires_in_sec=60 * 3)
    if not signed:
        raise HTTPException(status_code=500, detail="Failed to sign attachment url")

    ext = ""
    try:
        ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if len(ext) > 6:
            ext = ""
    except Exception:
        ext = ""

    filename = f"review_attachment_{str(report_id)[:8]}{ext or '.bin'}"
    media_type = "application/pdf" if (ext == ".pdf") else "application/octet-stream"

    try:
        resp = httpx.get(signed, timeout=30.0)
        resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch attachment: {e}") from e

    return Response(
        content=resp.content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename=\"{filename}\"',
            "Cache-Control": "no-store",
        },
    )


def _m():
    from app.api.v1 import manuscripts as manuscripts_api

    return manuscripts_api


@router.get(
    "/manuscripts/{manuscript_id}/versions", response_model=VersionHistoryResponse
)
async def get_manuscript_versions(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    获取稿件版本历史
    """
    service = RevisionService()

    manuscript = service.get_manuscript(str(manuscript_id))
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    is_author = str(manuscript.get("author_id")) == str(current_user["id"])

    if not is_author:
        try:
            profile_res = (
                _m()
                .supabase.table("user_profiles")
                .select("roles")
                .eq("id", current_user["id"])
                .single()
                .execute()
            )
            profile = getattr(profile_res, "data", {}) or {}
            roles = set(profile.get("roles", []) or [])
        except Exception:
            raise HTTPException(status_code=403, detail="Access denied")

        if roles.intersection({"managing_editor", "admin"}):
            pass
        elif "reviewer" in roles:
            try:
                ra = (
                    _m()
                    .supabase_admin.table("review_assignments")
                    .select("id")
                    .eq("manuscript_id", str(manuscript_id))
                    .eq("reviewer_id", str(current_user["id"]))
                    .limit(1)
                    .execute()
                )
                if not getattr(ra, "data", None):
                    raise HTTPException(status_code=403, detail="Access denied")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            raise HTTPException(status_code=403, detail="Access denied")

    result = service.get_version_history(str(manuscript_id))

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return VersionHistoryResponse(data=result["data"])


@router.get("/manuscripts/by-id/{manuscript_id}")
async def get_manuscript_detail(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    登录态稿件详情（非公开文章页）。
    """
    user_id = str(current_user["id"])
    roles = set((profile or {}).get("roles") or [])

    try:
        ms_resp = (
            _m()
            .supabase_admin.table("manuscripts")
            .select("*")
            .eq("id", str(manuscript_id))
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}
    except Exception as e:
        if _m()._is_postgrest_single_no_rows_error(str(e)):
            raise HTTPException(status_code=404, detail="Manuscript not found")
        raise
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    allowed = False
    if roles.intersection({"admin", "managing_editor"}):
        allowed = True
    elif str(ms.get("author_id") or "") == user_id:
        allowed = True
    else:
        try:
            ra = (
                _m()
                .supabase_admin.table("review_assignments")
                .select("id")
                .eq("manuscript_id", str(manuscript_id))
                .eq("reviewer_id", user_id)
                .limit(1)
                .execute()
            )
            if getattr(ra, "data", None):
                allowed = True
        except Exception:
            allowed = False

    if not allowed:
        raise HTTPException(status_code=403, detail="Forbidden")
    manuscript_id_str = str(manuscript_id)
    visited_statuses: set[str] = {"submitted"}
    current_status = _m()._normalize_private_progress_status(ms.get("status"))
    if current_status:
        visited_statuses.add(current_status)

    latest_feedback_comment: str | None = None
    latest_feedback_at: str | None = None
    latest_feedback_source: str | None = None
    latest_author_response_letter: str | None = None
    latest_author_response_at: str | None = None
    latest_author_response_round: int | None = None

    try:
        revision_resp = (
            _m()
            .supabase_admin.table("revisions")
            .select("editor_comment,created_at,updated_at")
            .eq("manuscript_id", manuscript_id_str)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        revision_rows = getattr(revision_resp, "data", None) or []
        for row in revision_rows:
            comment = str(row.get("editor_comment") or "").strip()
            if not comment:
                continue
            latest_feedback_comment = comment
            latest_feedback_at = str(row.get("created_at") or row.get("updated_at") or "")
            latest_feedback_source = "revision_request"
            break
    except Exception as e:
        print(f"[ById] revisions feedback fallback failed (ignored): {e}")

    revision_selects = [
        "response_letter,submitted_at,updated_at,round",
        "response_letter,updated_at",
    ]
    for select_clause in revision_selects:
        try:
            response_resp = (
                _m()
                .supabase_admin.table("revisions")
                .select(select_clause)
                .eq("manuscript_id", manuscript_id_str)
                .order("updated_at", desc=True)
                .limit(30)
                .execute()
            )
            response_rows = getattr(response_resp, "data", None) or []
            for row in response_rows:
                response_letter = str(row.get("response_letter") or "").strip()
                if not response_letter:
                    continue
                latest_author_response_letter = response_letter
                latest_author_response_at = str(row.get("submitted_at") or row.get("updated_at") or "")
                raw_round = row.get("round")
                try:
                    latest_author_response_round = int(raw_round) if raw_round is not None else None
                except Exception:
                    latest_author_response_round = None
                break
            break
        except Exception as e:
            lowered = str(e).lower()
            if "schema cache" in lowered or "column" in lowered or "pgrst" in lowered:
                continue
            print(f"[ById] latest author response fallback failed (ignored): {e}")
            break

    try:
        logs_resp = (
            _m()
            .supabase_admin.table("status_transition_logs")
            .select("from_status,to_status,comment,created_at,payload")
            .eq("manuscript_id", manuscript_id_str)
            .order("created_at", desc=True)
            .limit(120)
            .execute()
        )
        log_rows = getattr(logs_resp, "data", None) or []
        for row in log_rows:
            from_status = _m()._normalize_private_progress_status(row.get("from_status"))
            to_status = _m()._normalize_private_progress_status(row.get("to_status"))
            if from_status:
                visited_statuses.add(from_status)
            if to_status:
                visited_statuses.add(to_status)

            if latest_feedback_comment:
                continue

            comment = str(row.get("comment") or "").strip()
            if not comment:
                continue
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            action = str(payload.get("action") or "").strip().lower()
            is_revision_feedback = (
                to_status == "revision_requested"
                or action in {"precheck_intake_revision", "precheck_technical_revision"}
            )
            if is_revision_feedback:
                latest_feedback_comment = comment
                latest_feedback_at = str(row.get("created_at") or "")
                latest_feedback_source = "status_transition"
    except Exception as e:
        if not _m()._is_missing_table_error(str(e), "status_transition_logs"):
            print(f"[ById] transition logs fallback failed (ignored): {e}")

    enriched = dict(ms)
    enriched["workflow_visited_statuses"] = _m()._order_private_progress_statuses(visited_statuses)
    enriched["author_latest_feedback_comment"] = latest_feedback_comment
    enriched["author_latest_feedback_at"] = latest_feedback_at
    enriched["author_latest_feedback_source"] = latest_feedback_source
    enriched["author_latest_response_letter"] = latest_author_response_letter
    enriched["author_latest_response_at"] = latest_author_response_at
    enriched["author_latest_response_round"] = latest_author_response_round
    return {"success": True, "data": enriched}
