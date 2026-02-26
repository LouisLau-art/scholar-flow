from datetime import datetime
from uuid import UUID

import httpx
from fastapi import HTTPException
from fastapi.responses import Response

from app.api.v1 import manuscripts_detail_utils as utils

async def get_manuscript_author_context_impl(
    manuscript_id: UUID,
    current_user: dict,
    profile: dict,
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
            utils._m()
            .supabase_admin.table("manuscripts")
            .select("id,title,status,created_at,updated_at,author_id,file_path,journal_id")
            .eq("id", str(manuscript_id))
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}
    except Exception as e:
        if utils._m()._is_postgrest_single_no_rows_error(str(e)):
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

    versions = utils._load_versions(manuscript_id_str)
    revisions = utils._load_revisions(manuscript_id_str)
    logs = utils._load_transition_logs(manuscript_id_str)
    review_reports = utils._load_review_reports(manuscript_id_str)
    decision_letters = utils._load_final_decision_letters(manuscript_id_str)
    cover_letters = utils._load_cover_letter_files(manuscript_id_str)

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
            "timestamp": utils._safe_iso(ms.get("created_at")) or "",
            "actor": "author",
            "title": "投稿已提交",
            "message": "",
            "attachments": [],
        }
    )

    # 2) 状态流转（含作者可见 comment）
    for row in logs:
        from_status = utils._normalize_status_for_author(row.get("from_status"))
        to_status = utils._normalize_status_for_author(row.get("to_status"))
        ts = utils._safe_iso(row.get("created_at")) or ""
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        action = str(payload.get("action") or "").strip().lower()
        event_type = str(payload.get("event_type") or "").strip().lower()
        comment = str(row.get("comment") or "").strip()

        show_comment = False
        if action in utils.AUTHOR_VISIBLE_TRANSITION_ACTIONS:
            show_comment = True
        if event_type in {"proofreading_submitted"}:
            show_comment = True
        if to_status in {"minor_revision", "major_revision", "revision_requested", "rejected", "approved", "published"}:
            show_comment = True

        title = f"状态更新：{utils._humanize_status(from_status) if from_status else '—'} → {utils._humanize_status(to_status)}"
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

        created_at = utils._safe_iso(row.get("created_at") or row.get("updated_at")) or ""
        submitted_at = utils._safe_iso(row.get("submitted_at") or row.get("updated_at")) or ""

        if editor_comment:
            events.append(
                {
                    "id": f"revision-request-{rid}",
                    "timestamp": created_at,
                    "actor": "editorial",
                    "title": f"编辑请求{utils._humanize_decision(decision_type + '_revision' if decision_type else 'revision')}",
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
        ts = utils._safe_iso(row.get("updated_at") or row.get("created_at")) or ""
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
        ts = utils._safe_iso(row.get("updated_at") or row.get("created_at")) or ""
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
                "title": f"最终决定：{utils._humanize_decision(decision)}",
                "message": content,
                "attachments": attachments,
            }
        )

    # 排序：按 timestamp 升序（作者看流程更直观）
    def _sort_key(item: dict) -> datetime:
        return utils._timestamp_or_now(item.get("timestamp"))

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
                "created_at": utils._safe_iso(row.get("created_at")),
                "signed_url": utils._sign_storage_url(bucket=bucket, path=path, expires_in_sec=60 * 10),
            }
        )

    current_pdf_url = utils._sign_storage_url(bucket="manuscripts", path=str(ms.get("file_path") or ""), expires_in_sec=60 * 10)
    proofreading_task = utils._load_latest_author_proofreading_task(manuscript_id_str, author_id=user_id)

    return {
        "success": True,
        "data": {
            "manuscript": {
                "id": manuscript_id_str,
                "title": ms.get("title") or "Untitled",
                "status": ms.get("status"),
                "status_label": utils._humanize_status(utils._normalize_status_for_author(ms.get("status"))),
                "created_at": utils._safe_iso(ms.get("created_at")),
                "updated_at": utils._safe_iso(ms.get("updated_at")),
            },
            "files": {
                "current_pdf_signed_url": current_pdf_url,
                "cover_letters": cover_letter_items,
            },
            "proofreading_task": proofreading_task,
            "timeline": events,
        },
    }


async def download_review_attachment_for_author_impl(
    manuscript_id: UUID,
    report_id: UUID,
    current_user: dict,
    profile: dict,
):
    """
    作者下载审稿附件（匿名，不泄露 storage object key）。
    """
    user_id = str(current_user.get("id") or "").strip()
    roles = set((profile or {}).get("roles") or [])

    ms_resp = (
        utils._m()
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
        utils._m()
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
    signed = utils._sign_storage_url(bucket="review-attachments", path=path, expires_in_sec=60 * 3)
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

