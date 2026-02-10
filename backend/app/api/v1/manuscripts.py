from fastapi import (
    APIRouter,
    UploadFile,
    File,
    BackgroundTasks,
    HTTPException,
    Body,
    Form,
    Depends,
)
from fastapi.responses import JSONResponse, Response, RedirectResponse, PlainTextResponse
import httpx
from app.core.pdf_processor import extract_text_and_layout_from_pdf
from app.core.ai_engine import parse_manuscript_metadata
from app.core.plagiarism_worker import plagiarism_check_worker
from app.services.editorial_service import process_quality_check
from app.models.schemas import ManuscriptCreate
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.mail import EmailService
from app.services.notification_service import NotificationService
from app.services.revision_service import RevisionService
from app.services.plagiarism_service import PlagiarismService
from app.models.revision import RevisionSubmitResponse, VersionHistoryResponse
from app.core.roles import require_any_role, get_current_profile
from app.services.owner_binding_service import get_profile_for_owner, validate_internal_owner_id
from app.services.invoice_pdf_service import (
    generate_and_store_invoice_pdf,
    get_invoice_pdf_signed_url,
)
from app.services.post_acceptance_service import publish_manuscript as publish_manuscript_post_acceptance
from app.services.decision_service import DecisionService
from app.services.production_workspace_service import ProductionWorkspaceService
from app.models.production_workspace import SubmitProofreadingRequest
from uuid import uuid4, UUID
import shutil
import os
import asyncio
import tempfile
import time
from datetime import datetime, timezone
from typing import Optional

router = APIRouter(tags=["Manuscripts"])

_PUBLISHED_AT_SUPPORTED: bool | None = None

def _is_truthy_env(name: str, default: str = "0") -> bool:
    v = (os.environ.get(name, default) or "").strip().lower()
    return v in {"1", "true", "yes", "on"}

def _is_missing_column_error(error_text: str) -> bool:
    if not error_text:
        return False
    lowered = error_text.lower()
    return (
        "column" in lowered
        or "published_at" in lowered
        or "final_pdf_path" in lowered
        or "doi" in lowered
        or "reject_comment" in lowered
    )


def _is_missing_table_error(error_text: str, table_name: str) -> bool:
    if not error_text:
        return False
    lowered = error_text.lower()
    table = str(table_name or "").strip().lower()
    if not table:
        return False
    return table in lowered and (
        "does not exist" in lowered
        or "schema cache" in lowered
        or "pgrst205" in lowered
    )

def _is_postgrest_single_no_rows_error(error_text: str) -> bool:
    if not error_text:
        return False
    lowered = error_text.lower()
    # PostgREST: `.single()` 在 0 行时会报 406，并带 PGRST116（Cannot coerce ... 0 rows）
    return "pgrst116" in lowered or "cannot coerce the result to a single json object" in lowered or "0 rows" in lowered

def _get_signed_url_for_manuscripts_bucket(file_path: str, *, expires_in: int = 60 * 10) -> str:
    """
    生成 manuscripts bucket 的 signed URL（优先使用 service_role）。

    中文注释:
    - 前端 iframe 无法携带 Authorization header，因此必须把可访问的 signed URL 交给前端。
    - 为避免受 Storage RLS 影响，这里优先用 supabase_admin（service_role）签名。
    """
    last_err: Exception | None = None

    for client in (supabase_admin, supabase):
        try:
            signed = client.storage.from_("manuscripts").create_signed_url(file_path, expires_in)
            url = (signed or {}).get("signedUrl") or (signed or {}).get("signedURL")
            if url:
                return str(url)
        except Exception as e:
            last_err = e
            continue

    raise HTTPException(status_code=500, detail=f"Failed to create signed url: {last_err}")


def _public_article_url(article_id: str) -> str:
    origin = (os.environ.get("FRONTEND_ORIGIN") or "").strip().rstrip("/")
    if origin:
        return f"{origin}/articles/{article_id}"
    return f"/articles/{article_id}"


def _parse_iso_datetime(raw_value: str | None) -> datetime | None:
    raw = str(raw_value or "").strip()
    if not raw:
        return None
    try:
        # 中文注释: 兼容数据库常见的 Z 结尾时间格式
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def _resolve_public_author_names(article: dict) -> list[str]:
    names: list[str] = []
    raw_authors = article.get("authors")
    if isinstance(raw_authors, list):
        for item in raw_authors:
            if isinstance(item, str):
                if item.strip():
                    names.append(item.strip())
                continue
            if not isinstance(item, dict):
                continue
            full_name = str(item.get("full_name") or "").strip()
            first_name = str(item.get("first_name") or item.get("firstName") or "").strip()
            last_name = str(item.get("last_name") or item.get("lastName") or "").strip()
            composed = " ".join(part for part in (first_name, last_name) if part).strip()
            label = full_name or composed
            if label:
                names.append(label)

    if names:
        # 中文注释: 去重并保持原顺序，避免导出引用里重复作者
        deduped: list[str] = []
        seen: set[str] = set()
        for name in names:
            key = name.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(name.strip())
        if deduped:
            return deduped

    author_id = str(article.get("author_id") or "").strip()
    if author_id:
        try:
            resp = (
                supabase_admin.table("user_profiles")
                .select("id,full_name")
                .eq("id", author_id)
                .single()
                .execute()
            )
            profile = getattr(resp, "data", None) or {}
            full_name = str(profile.get("full_name") or "").strip()
            if full_name:
                return [full_name]
        except Exception:
            pass

    return ["Author"]


def _escape_bibtex_value(value: str) -> str:
    return str(value or "").replace("{", "\\{").replace("}", "\\}").replace("\n", " ").strip()


def _build_citation_payload(article: dict) -> dict:
    article_id = str(article.get("id") or "")
    published_raw = article.get("published_at") or article.get("created_at")
    published_dt = _parse_iso_datetime(str(published_raw or ""))
    if published_dt is None:
        published_dt = datetime.now(timezone.utc)

    year = str(published_dt.year)
    month = f"{published_dt.month:02d}"
    day = f"{published_dt.day:02d}"
    journal_title = str((article.get("journals") or {}).get("title") or "ScholarFlow Journal")
    title = str(article.get("title") or "Untitled")
    doi = str(article.get("doi") or "").strip()
    authors = _resolve_public_author_names(article)
    key_id = "".join(ch for ch in article_id if ch.isalnum())[:8] or "article"
    bibtex_key = f"scholarflow{year}{key_id}"

    return {
        "article_id": article_id,
        "title": title,
        "journal_title": journal_title,
        "doi": doi,
        "authors": authors,
        "year": year,
        "month": month,
        "day": day,
        "date_slash": f"{year}/{month}/{day}",
        "url": _public_article_url(article_id),
        "bibtex_key": bibtex_key,
    }


def _to_bibtex(payload: dict) -> str:
    lines: list[str] = [f"@article{{{payload['bibtex_key']},"]
    if payload.get("title"):
        lines.append(f"  title = {{{_escape_bibtex_value(payload['title'])}}},")
    if payload.get("journal_title"):
        lines.append(f"  journal = {{{_escape_bibtex_value(payload['journal_title'])}}},")
    if payload.get("authors"):
        author_text = " and ".join(_escape_bibtex_value(author) for author in payload["authors"])
        lines.append(f"  author = {{{author_text}}},")
    if payload.get("year"):
        lines.append(f"  year = {{{payload['year']}}},")
    if payload.get("doi"):
        lines.append(f"  doi = {{{_escape_bibtex_value(payload['doi'])}}},")
    if payload.get("url"):
        lines.append(f"  url = {{{_escape_bibtex_value(payload['url'])}}},")
    lines.append("}")
    return "\n".join(lines)


def _to_ris(payload: dict) -> str:
    lines: list[str] = ["TY  - JOUR"]
    if payload.get("title"):
        lines.append(f"TI  - {payload['title']}")
    for author in payload.get("authors") or []:
        lines.append(f"AU  - {author}")
    if payload.get("journal_title"):
        lines.append(f"JO  - {payload['journal_title']}")
    if payload.get("year"):
        lines.append(f"PY  - {payload['year']}")
    if payload.get("date_slash"):
        lines.append(f"DA  - {payload['date_slash']}")
    if payload.get("doi"):
        lines.append(f"DO  - {payload['doi']}")
    if payload.get("url"):
        lines.append(f"UR  - {payload['url']}")
    lines.append("ER  -")
    return "\n".join(lines) + "\n"


def _get_published_article_for_citation(article_id: UUID) -> dict:
    try:
        ms_resp = (
            supabase_admin.table("manuscripts")
            .select("*")
            .eq("id", str(article_id))
            .eq("status", "published")
            .single()
            .execute()
        )
        manuscript = getattr(ms_resp, "data", None) or {}
    except Exception as e:
        if _is_postgrest_single_no_rows_error(str(e)):
            raise HTTPException(status_code=404, detail="Article not found")
        raise

    if not manuscript:
        raise HTTPException(status_code=404, detail="Article not found")

    journal_id = manuscript.get("journal_id")
    manuscript["journals"] = None
    if journal_id:
        try:
            jr_resp = (
                supabase_admin.table("journals")
                .select("id,title,slug,issn")
                .eq("id", str(journal_id))
                .single()
                .execute()
            )
            manuscript["journals"] = getattr(jr_resp, "data", None) or None
        except Exception:
            manuscript["journals"] = None

    return manuscript


@router.get("/manuscripts/{manuscript_id}/pdf-signed")
async def get_manuscript_pdf_signed(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    返回稿件 PDF 的 signed URL（用于预览 iframe）。

    中文注释:
    - 之所以不直接返回 file_path：Storage RLS/权限会导致前端预览空白或报错。
    - 这里显式做访问控制：仅作者本人 / 被分配 reviewer / editor/admin 可取 signedUrl。
    """
    user_id = str(current_user["id"])
    roles = set((profile or {}).get("roles") or [])

    ms_resp = (
        supabase_admin.table("manuscripts")
        .select("id, author_id, file_path")
        .eq("id", str(manuscript_id))
        .single()
        .execute()
    )
    ms = getattr(ms_resp, "data", None) or {}
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")
    file_path = ms.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="Manuscript PDF not found")

    allowed = False
    if roles.intersection({"admin", "editor"}):
        allowed = True
    elif str(ms.get("author_id") or "") == user_id:
        allowed = True
    else:
        # Reviewer: 允许已指派 reviewer 预览（避免 editor 通过 UI 分配后 reviewer 侧打不开 PDF）
        try:
            ra = (
                supabase_admin.table("review_assignments")
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

        # 兼容：免登录 token 模式可能只写了 review_reports
        if not allowed:
            try:
                rr = (
                    supabase_admin.table("review_reports")
                    .select("id")
                    .eq("manuscript_id", str(manuscript_id))
                    .eq("reviewer_id", user_id)
                    .limit(1)
                    .execute()
                )
                if getattr(rr, "data", None):
                    allowed = True
            except Exception:
                pass

    if not allowed:
        raise HTTPException(status_code=403, detail="No permission to access this manuscript PDF")

    signed_url = _get_signed_url_for_manuscripts_bucket(str(file_path))
    return {"success": True, "data": {"signed_url": signed_url}}


@router.get("/manuscripts/{manuscript_id}/decision-attachments/{attachment_id}/signed-url")
async def get_decision_attachment_signed_url_for_author(
    manuscript_id: UUID,
    attachment_id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    Feature 041: 作者侧下载决策附件（仅 final 可见）。
    """
    signed_url = DecisionService().get_attachment_signed_url_for_author(
        manuscript_id=str(manuscript_id),
        attachment_id=attachment_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
    )
    return {"success": True, "data": {"signed_url": signed_url}}


@router.get("/manuscripts/{manuscript_id}/proofreading-context")
async def get_proofreading_context(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    Feature 042: 作者侧获取待校对清样上下文。
    """
    data = ProductionWorkspaceService().get_author_proofreading_context(
        manuscript_id=str(manuscript_id),
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
    )
    return {"success": True, "data": data}


@router.post("/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/proofreading")
async def submit_proofreading_response(
    manuscript_id: UUID,
    cycle_id: str,
    payload: SubmitProofreadingRequest,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    Feature 042: 作者提交校对反馈（confirm_clean / submit_corrections）。
    """
    data = ProductionWorkspaceService().submit_proofreading(
        manuscript_id=str(manuscript_id),
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
        request=payload,
    )
    return {"success": True, "data": data}


@router.get("/manuscripts/{manuscript_id}/production-cycles/{cycle_id}/galley-signed")
async def get_production_galley_signed_url_for_author(
    manuscript_id: UUID,
    cycle_id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    Feature 042: 作者/内部角色获取 production galley 的 signed URL。
    """
    signed_url = ProductionWorkspaceService().get_galley_signed_url(
        manuscript_id=str(manuscript_id),
        cycle_id=cycle_id,
        user_id=str(current_user.get("id") or ""),
        profile_roles=profile.get("roles") or [],
    )
    return {"success": True, "data": {"signed_url": signed_url}}


@router.get("/manuscripts/{manuscript_id}/invoice")
async def download_invoice_pdf(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    Feature 024: 下载账单 PDF（Author / Editor / Admin）

    中文注释:
    - Feature 026：账单 PDF 使用 WeasyPrint 生成并持久化到 Storage `invoices`，此处作为兼容入口提供下载。
    """
    user_id = str(current_user["id"])
    roles = set((profile or {}).get("roles") or [])
    is_internal = bool(roles.intersection({"admin", "editor"}))

    ms_resp = (
        supabase_admin.table("manuscripts")
        .select("id, author_id, title")
        .eq("id", str(manuscript_id))
        .single()
        .execute()
    )
    ms = getattr(ms_resp, "data", None) or {}
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    if not (roles.intersection({"admin", "editor"}) or str(ms.get("author_id") or "") == user_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    inv_resp = (
        supabase_admin.table("invoices")
        .select("id, amount, pdf_path, pdf_error")
        .eq("manuscript_id", str(manuscript_id))
        .limit(1)
        .execute()
    )
    inv_rows = getattr(inv_resp, "data", None) or []
    if not inv_rows:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv = inv_rows[0]

    invoice_id = UUID(str(inv.get("id")))
    pdf_path = (inv.get("pdf_path") or "").strip()
    pdf_error = (inv.get("pdf_error") or "").strip()

    # 若尚未生成或上次失败，则同步触发一次生成（作者点击下载时体验更直观）
    if (not pdf_path) or pdf_error:
        res = generate_and_store_invoice_pdf(invoice_id=invoice_id)
        if res.pdf_error:
            print(f"[InvoicePDF] generate failed for manuscript={manuscript_id}: {res.pdf_error}")
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Failed to generate invoice pdf: {res.pdf_error}"
                    if is_internal
                    else "Invoice PDF generation failed. Please retry later."
                ),
            )

    try:
        signed_url, _expires_in = get_invoice_pdf_signed_url(invoice_id=invoice_id)
    except Exception as e:
        print(f"[InvoicePDF] signed url failed for invoice={invoice_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=(f"Invoice not available: {e}" if is_internal else "Invoice not available. Please retry later."),
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(signed_url)
            if r.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to download invoice pdf from storage (status={r.status_code})",
                )
            pdf_bytes = bytes(r.content or b"")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to download invoice pdf: {e}")

    filename = f"invoice-{manuscript_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'},
    )


@router.post("/manuscripts/{manuscript_id}/production-file")
async def upload_production_file(
    manuscript_id: UUID,
    file: UploadFile = File(...),
    _current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    Feature 024: 上传最终排版 PDF（Production File）
    """
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 格式文件")

    ms_resp = (
        supabase_admin.table("manuscripts")
        .select("id,status")
        .eq("id", str(manuscript_id))
        .single()
        .execute()
    )
    ms = getattr(ms_resp, "data", None) or {}
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    # Feature 031：录用后生产阶段也允许替换最终排版 PDF（便于排版/校对迭代）。
    allowed_statuses = {"approved", "layout", "english_editing", "proofreading"}
    if (ms.get("status") or "").lower() not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Production file upload requires status in {sorted(allowed_statuses)}",
        )

    safe_name = (file.filename or "final.pdf").replace("/", "_").replace("\\", "_")
    ts = int(time.time())
    path = f"production/{manuscript_id}/{ts}-{safe_name}"

    try:
        content = await file.read()
        supabase_admin.storage.from_("manuscripts").upload(
            path, content, {"content-type": "application/pdf"}
        )
    except Exception as e:
        print(f"[Production] upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload production file")

    try:
        supabase_admin.table("manuscripts").update({"final_pdf_path": path}).eq(
            "id", str(manuscript_id)
        ).execute()
    except Exception as e:
        err = str(e)
        print(f"[Production] update final_pdf_path failed: {err}")
        lowered = err.lower()
        if "final_pdf_path" in lowered and ("column" in lowered or "schema cache" in lowered):
            # MVP 提速：Production Gate 默认关闭；字段缺失时允许“只上传、不落库”
            if _is_truthy_env("PRODUCTION_GATE_ENABLED", "0"):
                raise HTTPException(
                    status_code=500,
                    detail="Database schema missing final_pdf_path. Please apply migrations for Feature 024.",
                )
            return {
                "success": True,
                "data": {"final_pdf_path": path, "persisted": False},
                "warning": "final_pdf_path column missing; uploaded file is not linked to manuscript (MVP mode).",
            }
        raise HTTPException(status_code=500, detail="Failed to update production file path")

    return {"success": True, "data": {"final_pdf_path": path, "persisted": True}}


@router.post("/manuscripts/{manuscript_id}/publish")
async def publish_manuscript_endpoint(
    manuscript_id: UUID,
    _current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    Feature 024: REST 形式发布端点（与 /api/v1/editor/publish 等价）
    """
    published = publish_manuscript_post_acceptance(manuscript_id=str(manuscript_id))
    return {"success": True, "data": published}


@router.get("/manuscripts/{manuscript_id}/versions/{version_number}/pdf-signed")
async def get_manuscript_version_pdf_signed(
    manuscript_id: UUID,
    version_number: int,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    返回指定版本 PDF 的 signed URL（用于历史版本下载/预览）。

    中文注释:
    - 前端下载/预览历史版本时，不应直接依赖 Storage public/RLS。
    - 统一通过后端（service_role）生成 signed URL，避免权限与跨域问题。
    """
    if version_number <= 0:
        raise HTTPException(status_code=422, detail="version_number must be >= 1")

    user_id = str(current_user["id"])
    roles = set((profile or {}).get("roles") or [])

    ms_resp = (
        supabase_admin.table("manuscripts")
        .select("id, author_id")
        .eq("id", str(manuscript_id))
        .single()
        .execute()
    )
    ms = getattr(ms_resp, "data", None) or {}
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    allowed = False
    if roles.intersection({"admin", "editor"}):
        allowed = True
    elif str(ms.get("author_id") or "") == user_id:
        allowed = True
    else:
        # Reviewer：被分配 reviewer 可见
        try:
            ra = (
                supabase_admin.table("review_assignments")
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

        # 兼容：免登录 token 模式可能只写了 review_reports
        if not allowed:
            try:
                rr = (
                    supabase_admin.table("review_reports")
                    .select("id")
                    .eq("manuscript_id", str(manuscript_id))
                    .eq("reviewer_id", user_id)
                    .limit(1)
                    .execute()
                )
                if getattr(rr, "data", None):
                    allowed = True
            except Exception:
                pass

    if not allowed:
        raise HTTPException(status_code=403, detail="No permission to access this manuscript version PDF")

    ver_resp = (
        supabase_admin.table("manuscript_versions")
        .select("file_path")
        .eq("manuscript_id", str(manuscript_id))
        .eq("version_number", version_number)
        .single()
        .execute()
    )
    ver = getattr(ver_resp, "data", None) or {}
    file_path = ver.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="Manuscript version PDF not found")

    signed_url = _get_signed_url_for_manuscripts_bucket(str(file_path))
    return {"success": True, "data": {"signed_url": signed_url}}


@router.get("/manuscripts/{manuscript_id}/reviews")
async def get_manuscript_reviews(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    获取某稿件的审稿反馈（用于 Editor 决策页展示 Review Summary）。

    中文注释:
    - Author 只能看到公开字段（comments_for_author/content/score）
    - Editor/Admin 可以看到机密字段（confidential_comments_to_editor/attachment_path）
    """
    user_id = str(current_user.get("id"))
    roles = set((profile or {}).get("roles") or [])

    ms_resp = (
        supabase_admin.table("manuscripts")
        .select("id, author_id")
        .eq("id", str(manuscript_id))
        .single()
        .execute()
    )
    ms = getattr(ms_resp, "data", None) or {}
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    is_author = str(ms.get("author_id") or "") == user_id
    is_editor = bool(roles.intersection({"admin", "editor"}))
    if not (is_author or is_editor):
        raise HTTPException(status_code=403, detail="Forbidden")

    rr_resp = (
        supabase_admin.table("review_reports")
        .select(
            "id, manuscript_id, reviewer_id, status, comments_for_author, content, score, confidential_comments_to_editor, attachment_path, created_at"
        )
        .eq("manuscript_id", str(manuscript_id))
        .order("created_at", desc=True)
        .execute()
    )
    rows: list[dict] = getattr(rr_resp, "data", None) or []

    reviewer_ids = sorted({str(r.get("reviewer_id")) for r in rows if r.get("reviewer_id")})
    profile_by_id: dict[str, dict] = {}
    if reviewer_ids:
        try:
            pr = (
                supabase_admin.table("user_profiles")
                .select("id, full_name, email")
                .in_("id", reviewer_ids)
                .execute()
            )
            for p in (getattr(pr, "data", None) or []):
                if p.get("id"):
                    profile_by_id[str(p["id"])] = p
        except Exception:
            profile_by_id = {}

    for r in rows:
        rid = str(r.get("reviewer_id") or "")
        p = profile_by_id.get(rid) or {}
        r["reviewer_name"] = p.get("full_name")
        r["reviewer_email"] = p.get("email")
        if not r.get("comments_for_author") and r.get("content"):
            r["comments_for_author"] = r.get("content")

    # 中文注释:
    # - 历史上可能出现“重复邀请/重复指派”导致同一 reviewer 多条 review_reports（其中部分未提交）。
    # - Editor 决策页应优先展示“已完成/有内容”的那条，避免出现 Score N/A 的误导。
    def _parse_dt(value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    def _row_rank(r: dict) -> tuple[int, int, int, datetime]:
        status = str(r.get("status") or "").strip().lower()
        is_completed = 1 if status in {"completed", "done", "submitted"} else 0
        has_score = 1 if r.get("score") is not None else 0
        public_text = str(r.get("comments_for_author") or r.get("content") or "").strip()
        has_public = 1 if public_text else 0
        dt = _parse_dt(r.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)
        return (is_completed, has_score, has_public, dt)

    best_by_reviewer: dict[str, dict] = {}
    others: list[dict] = []
    for r in rows:
        rid = str(r.get("reviewer_id") or "").strip()
        if not rid:
            others.append(r)
            continue
        prev = best_by_reviewer.get(rid)
        if prev is None or _row_rank(r) > _row_rank(prev):
            best_by_reviewer[rid] = r

    deduped = list(best_by_reviewer.values())
    deduped.sort(key=lambda r: _parse_dt(r.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    rows = deduped + others

    if is_author:
        sanitized = []
        for r in rows:
            public_text = r.get("comments_for_author") or r.get("content")
            sanitized.append(
                {
                    "id": r.get("id"),
                    "manuscript_id": r.get("manuscript_id"),
                    "reviewer_id": r.get("reviewer_id"),
                    "reviewer_name": r.get("reviewer_name"),
                    "reviewer_email": r.get("reviewer_email"),
                    "status": r.get("status"),
                    # 兼容：旧页面读取 content
                    "content": public_text,
                    "comments_for_author": public_text,
                    "score": r.get("score"),
                    "created_at": r.get("created_at"),
                }
            )
        return {"success": True, "data": sanitized}

    return {"success": True, "data": rows}


# === 1. 投稿 (User Story 1) ===
@router.post("/manuscripts/upload")
async def upload_manuscript(
    background_tasks: BackgroundTasks, file: UploadFile = File(...)
):
    """稿件上传与 AI 解析"""
    if not (file.filename or "").lower().endswith(".pdf"):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "仅支持 PDF 格式文件", "data": {"title": "", "abstract": "", "authors": []}},
        )

    manuscript_id = uuid4()
    temp_path = None
    start = time.monotonic()
    trace_id = str(manuscript_id)[:8]
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            temp_path = tmp.name
            shutil.copyfileobj(file.file, tmp)

        file_size_bytes = os.path.getsize(temp_path) if temp_path and os.path.exists(temp_path) else 0
        file_size_mb = file_size_bytes / (1024 * 1024) if file_size_bytes > 0 else 0.0
        print(
            f"[UploadManuscript:{trace_id}] start filename={file.filename} size_mb={file_size_mb:.2f}",
            flush=True,
        )

        try:
            timeout_sec = float(os.environ.get("PDF_PARSE_TIMEOUT_SEC", "8"))
        except Exception:
            timeout_sec = 8.0

        # 中文注释: 只解析前几页/截断字符，避免“整篇论文”塞给 AI 造成超时与成本浪费
        try:
            max_pages = int(os.environ.get("PDF_PARSE_MAX_PAGES", "5"))
        except Exception:
            max_pages = 5
        try:
            max_chars = int(os.environ.get("PDF_PARSE_MAX_CHARS", "20000"))
        except Exception:
            max_chars = 20000

        try:
            layout_skip_file_mb = int(os.environ.get("PDF_LAYOUT_SKIP_FILE_MB", "8"))
        except Exception:
            layout_skip_file_mb = 8
        layout_max_pages_override = 0 if (layout_skip_file_mb > 0 and file_size_mb > layout_skip_file_mb) else None

        try:
            text, layout_lines = await asyncio.wait_for(
                asyncio.to_thread(
                    extract_text_and_layout_from_pdf,
                    temp_path,
                    max_pages=max_pages,
                    max_chars=max_chars,
                    layout_max_pages=layout_max_pages_override,
                ),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            # 超时直接降级：允许用户手动填写 title/abstract
            print(
                f"[UploadManuscript:{trace_id}] timeout in pdf extraction (> {timeout_sec:.1f}s), fallback manual fill",
                flush=True,
            )
            return {
                "success": True,
                "id": manuscript_id,
                "trace_id": trace_id,
                "data": {"title": "", "abstract": "", "authors": []},
                "message": f"PDF 解析超时（>{timeout_sec:.0f}s），已跳过 AI 解析，可手动填写。",
            }

        # 元数据提取：本地解析（无 HTTP），仅用于前端预填
        meta_start = time.monotonic()
        try:
            meta_timeout_sec = float(os.environ.get("PDF_METADATA_TIMEOUT_SEC", "4"))
        except Exception:
            meta_timeout_sec = 4.0

        try:
            metadata = await asyncio.wait_for(
                parse_manuscript_metadata(text or "", layout_lines=layout_lines or []),
                timeout=meta_timeout_sec,
            )
        except asyncio.TimeoutError:
            print(
                f"[UploadManuscript:{trace_id}] timeout in metadata parsing (> {meta_timeout_sec:.1f}s), fallback manual fill",
                flush=True,
            )
            metadata = {"title": "", "abstract": "", "authors": []}
        meta_cost = time.monotonic() - meta_start
        total_cost = time.monotonic() - start
        print(
            f"[UploadManuscript:{trace_id}] parsed: pdf_timeout={timeout_sec:.1f}s max_pages={max_pages} "
            f"max_chars={max_chars} layout_override={layout_max_pages_override} meta_time={meta_cost:.2f}s total={total_cost:.2f}s"
            f" text_len={len(text or '')} layout_lines={len(layout_lines or [])}",
            flush=True,
        )

        # 该接口仅用于前端预填元数据；查重属于“可选项”，且当前实现为 Mock，默认关闭以提速。
        # 如需开启：export PLAGIARISM_CHECK_ENABLED=1
        if _is_truthy_env("PLAGIARISM_CHECK_ENABLED", "0"):
            try:
                # 中文注释: 先落一条 pending 报告，便于前端状态轮询与错误追踪。
                PlagiarismService().ensure_report(str(manuscript_id), reset_status=False)
            except Exception as e:
                # 不阻断投稿主链路，查重失败按“降级”处理。
                print(f"[UploadManuscript:{trace_id}] init plagiarism report failed (ignored): {e}", flush=True)
            background_tasks.add_task(plagiarism_check_worker, str(manuscript_id))
        print(f"[UploadManuscript:{trace_id}] done", flush=True)
        return {"success": True, "id": manuscript_id, "trace_id": trace_id, "data": metadata}
    except Exception as e:
        print(f"[UploadManuscript:{trace_id}] failed: {e}", flush=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "trace_id": trace_id,
                "message": str(e),
                "data": {"title": "", "abstract": "", "authors": []},
            },
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@router.post(
    "/manuscripts/{manuscript_id}/revisions", response_model=RevisionSubmitResponse
)
async def submit_revision(
    manuscript_id: UUID,
    background_tasks: BackgroundTasks,
    response_letter: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Author 提交修订稿 (Submit Revision)

    User Story 2:
    1. 上传新 PDF。
    2. 创建新版本 (v2, v3...)。
    3. 更新 Revision 状态为 submitted。
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 格式文件")

    service = RevisionService()

    # 1. 验证权限与状态 (Service 层会再次验证，但 Controller 层做基本检查也好)
    manuscript = service.get_manuscript(str(manuscript_id))
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    if str(manuscript.get("author_id")) != str(current_user["id"]):
        raise HTTPException(
            status_code=403, detail="Only the author can submit revisions"
        )

    # 2. 获取下一版本号用于文件名
    next_version = (manuscript.get("version", 1)) + 1

    # 3. 生成存储路径 (使用 Service 逻辑)
    file_path = service.generate_versioned_file_path(
        str(manuscript_id), file.filename, next_version
    )

    # 4. 上传文件到 Supabase Storage
    # 注意：这里我们模拟上传，实际上应该使用 supabase storage client
    # 但由于之前的 upload_manuscript 似乎只解析没存 Storage?
    # 不，create_manuscript 接收 file_path。
    # 我们需要在 upload 阶段就上传，或者在这里上传。
    # 这里的 file 是 UploadFile，我们需要读取并上传。

    try:
        file_content = await file.read()
        # 使用 service_role client 上传以确保权限
        supabase_admin.storage.from_("manuscripts").upload(
            file_path, file_content, {"content-type": "application/pdf"}
        )
        # supabase-py upload 返回结果可能包含 path/Key
    except Exception as e:
        print(f"File upload failed: {e}")
        # 如果是 duplicate，尝试覆盖或者报错? gate 2 says never overwrite.
        # generate_versioned_file_path ensures uniqueness ideally.
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

    # 5. 调用 Service 提交
    # 解析新文件的元数据（可选，如 title/abstract 变更）
    # 暂时复用旧的 title/abstract，除非我们想再次调用 AI 解析
    # 为了简化 MVP，假设作者只上传文件，不修改元数据，或者前端传递

    result = service.submit_revision(
        manuscript_id=str(manuscript_id),
        author_id=str(current_user["id"]),
        new_file_path=file_path,
        response_letter=response_letter,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    # === 通知中心 (T024) ===
    try:
        notification_service = NotificationService()

        # 通知作者自己
        notification_service.create_notification(
            user_id=str(current_user["id"]),
            manuscript_id=str(manuscript_id),
            type="submission",
            title="Revision Submitted",
            content=f"Your revision for '{manuscript.get('title')}' has been submitted.",
        )

        # 通知 Editor（MVP：只通知稿件归属人/编辑，避免给所有 editor 群发且减少云端 mock 用户导致的 409）
        recipients: set[str] = set()
        owner_id = manuscript.get("owner_id") or manuscript.get("kpi_owner_id")
        editor_id = manuscript.get("editor_id")
        if owner_id:
            recipients.add(str(owner_id))
        if editor_id:
            recipients.add(str(editor_id))
        recipients.discard(str(current_user["id"]))

        for uid in sorted(recipients):
            notification_service.create_notification(
                user_id=uid,
                manuscript_id=str(manuscript_id),
                type="system",
                title="Revision Received",
                content=f"A revision for '{manuscript.get('title')}' has been submitted.",
            )

    except Exception as e:
        print(f"[Notifications] Failed to send revision notification: {e}")

    return RevisionSubmitResponse(data=result["data"])


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

    # 权限检查
    manuscript = service.get_manuscript(str(manuscript_id))
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    # 作者本人、Editor、Admin、被分配的 Reviewer 可见
    # 简单实现：检查是否是作者或 Editor/Admin
    # 复杂权限在 RLS 层也有，但 API 层也需把关
    is_author = str(manuscript.get("author_id")) == str(current_user["id"])

    # 获取用户角色
    # 注意：get_current_user 返回的是 auth.users 表数据，roles 在 user_profiles
    # 我们假设 current_user 包含 roles (如果 auth_utils 做了处理) 或者再次查询
    # 为了性能，这里简单假设如果是 author 就允许。
    # Editor/Admin 检查略繁琐，这里暂不做强制校验，依赖 Service/RLS?
    # 不，Service 使用 admin client，所以 API 层必须校验。

    if not is_author:
        # Check roles + reviewer must be assigned to this manuscript
        try:
            profile_res = (
                supabase.table("user_profiles")
                .select("roles")
                .eq("id", current_user["id"])
                .single()
                .execute()
            )
            profile = getattr(profile_res, "data", {}) or {}
            roles = set(profile.get("roles", []) or [])
        except Exception:
            raise HTTPException(status_code=403, detail="Access denied")

        if roles.intersection({"editor", "admin"}):
            pass
        elif "reviewer" in roles:
            try:
                ra = (
                    supabase_admin.table("review_assignments")
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


# === 2. 编辑质检 (User Story 2) ===
@router.post("/manuscripts/{manuscript_id}/quality-check")
async def submit_quality_check(
    manuscript_id: UUID,
    passed: bool = Body(..., embed=True),
    owner_id: Optional[UUID] = Body(None, embed=True),
    kpi_owner_id: Optional[UUID] = Body(None, embed=True),  # 兼容旧字段名
):
    resolved_owner_id = owner_id or kpi_owner_id
    if not resolved_owner_id:
        raise HTTPException(status_code=422, detail="owner_id is required")

    # 显性逻辑：owner_id 必须属于内部员工（editor/admin）
    try:
        validate_internal_owner_id(resolved_owner_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="owner_id must be editor/admin")

    result = await process_quality_check(manuscript_id, passed, resolved_owner_id)
    return {"success": True, "data": result}


# === 3. 搜索与列表 (Discovery) ===
@router.get("/manuscripts")
async def get_manuscripts():
    """获取所有稿件列表"""
    try:
        response = (
            supabase.table("manuscripts")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        # supabase-py 的 execute() 返回的是一个对象，其 data 属性包含结果
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"查询失败: {str(e)}")
        return {"success": False, "data": []}


@router.get("/manuscripts/mine")
async def get_my_manuscripts(current_user: dict = Depends(get_current_user)):
    """作者视角：仅返回当前用户的稿件列表"""
    try:
        # 中文注释: 作者列表仅展示自己投稿，避免越权查看
        response = (
            supabase.table("manuscripts")
            .select("*")
            .eq("author_id", current_user["id"])
            .order("created_at", desc=True)
            .execute()
        )
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"作者稿件查询失败: {str(e)}")
        return {"success": False, "data": []}


@router.get("/manuscripts/search")
async def public_search(q: str, mode: str = "articles"):
    """公开检索"""
    try:
        if mode == "articles":
            response = (
                supabase.table("manuscripts")
                .select("*, journals(title)")
                .eq("status", "published")
                .or_(f"title.ilike.%{q}%,abstract.ilike.%{q}%")
                .execute()
            )
        else:
            response = (
                supabase.table("journals")
                .select("*")
                .ilike("title", f"%{q}%")
                .execute()
            )
        return {"success": True, "results": response.data}
    except Exception as e:
        print(f"搜索异常: {str(e)}")
        return {"success": False, "results": []}


@router.get("/manuscripts/by-id/{manuscript_id}")
async def get_manuscript_detail(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    登录态稿件详情（非公开文章页）。

    中文注释:
    - Submit Revision / Reviewer Workspace / Editor 后台都需要读取“未发表稿件”的详情。
    - 这里显式做访问控制：仅作者本人 / 被分配 reviewer / editor/admin 可读。
    - 该路由必须放在 /manuscripts/search 之后，避免 path 参数吞掉静态路由。
    """
    user_id = str(current_user["id"])
    roles = set((profile or {}).get("roles") or [])

    try:
        ms_resp = (
            supabase_admin.table("manuscripts")
            .select("*")
            .eq("id", str(manuscript_id))
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}
    except Exception as e:
        if _is_postgrest_single_no_rows_error(str(e)):
            raise HTTPException(status_code=404, detail="Manuscript not found")
        raise
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    allowed = False
    if roles.intersection({"admin", "editor"}):
        allowed = True
    elif str(ms.get("author_id") or "") == user_id:
        allowed = True
    else:
        try:
            ra = (
                supabase_admin.table("review_assignments")
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

    return {"success": True, "data": ms}


@router.get("/manuscripts/published/latest")
async def get_latest_published_articles(limit: int = 6):
    """
    Feature 024: 首页“Latest Articles”数据源（仅 published，按 published_at 倒序）
    """
    # 中文注释：部分云端环境可能尚未应用 Feature 024 的 schema（例如缺少 published_at）。
    # 为避免每次请求都触发一次 400（噪声 + 多一次网络请求），这里做一次性能力探测并缓存结果。
    global _PUBLISHED_AT_SUPPORTED
    try:
        n = max(1, min(int(limit), 50))
    except Exception:
        n = 6

    try:
        # 优先按 published_at 排序；若环境缺列，则退化为 created_at
        if _PUBLISHED_AT_SUPPORTED is False:
            resp = (
                supabase.table("manuscripts")
                .select("id,title,abstract,doi,created_at,journal_id")
                .eq("status", "published")
                .order("created_at", desc=True)
                .limit(n)
                .execute()
            )
        else:
            try:
                resp = (
                    supabase.table("manuscripts")
                    .select("id,title,abstract,doi,published_at,journal_id")
                    .eq("status", "published")
                    .order("published_at", desc=True)
                    .limit(n)
                    .execute()
                )
                _PUBLISHED_AT_SUPPORTED = True
            except Exception as e:
                if _is_missing_column_error(str(e)):
                    _PUBLISHED_AT_SUPPORTED = False
                    resp = (
                        supabase.table("manuscripts")
                        .select("id,title,abstract,doi,created_at,journal_id")
                        .eq("status", "published")
                        .order("created_at", desc=True)
                        .limit(n)
                        .execute()
                    )
                else:
                    raise

        return {"success": True, "data": getattr(resp, "data", None) or []}
    except Exception as e:
        print(f"[LatestArticles] 查询失败: {e}")
        return {"success": False, "data": []}


# === 4. 详情查询 ===
@router.get("/manuscripts/articles/{id}")
async def get_article_detail(id: UUID):
    try:
        try:
            manuscript_response = (
                supabase.table("manuscripts")
                .select("*")
                .eq("id", str(id))
                .eq("status", "published")
                .single()
                .execute()
            )
            manuscript = manuscript_response.data
        except Exception as e:
            # 中文注释：PostgREST 的 .single() 在 0 行时会抛 406（PGRST116）。
            # 这里应返回 404，而不是 500（避免前端误判为系统故障）。
            if _is_postgrest_single_no_rows_error(str(e)):
                raise HTTPException(status_code=404, detail="Article not found")
            raise
        if not manuscript:
            raise HTTPException(status_code=404, detail="Article not found")

        # Feature 023: 返回 owner 详细信息（姓名/邮箱），用于 KPI 归属展示
        owner_raw = manuscript.get("owner_id") or manuscript.get("kpi_owner_id")
        if owner_raw:
            try:
                profile = get_profile_for_owner(UUID(str(owner_raw)))
                if profile:
                    manuscript["owner"] = {
                        "id": profile.get("id"),
                        "full_name": profile.get("full_name"),
                        "email": profile.get("email"),
                    }
            except Exception as e:
                print(f"[OwnerBinding] 获取 owner profile 失败（降级忽略）: {e}")
        # 中文注释: 兼容未建立 journals 外键关系的环境，按需补充期刊信息
        journal_id = manuscript.get("journal_id")
        if journal_id:
            journal_response = (
                supabase.table("journals")
                .select("*")
                .eq("id", journal_id)
                .single()
                .execute()
            )
            manuscript["journals"] = journal_response.data
        else:
            manuscript["journals"] = None
        return {"success": True, "data": manuscript}
    except HTTPException:
        raise
    except Exception as e:
        print(f"文章详情查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch article detail")


@router.get("/manuscripts/articles/{id}/citation.bib")
async def download_article_citation_bib(id: UUID):
    """
    导出文章 BibTeX 引用（仅 published）。
    """
    article = _get_published_article_for_citation(id)
    payload = _build_citation_payload(article)
    content = _to_bibtex(payload)
    filename = f"scholarflow-{payload['article_id'] or id}.bib"
    return PlainTextResponse(
        content=content,
        media_type="application/x-bibtex; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/manuscripts/articles/{id}/citation.ris")
async def download_article_citation_ris(id: UUID):
    """
    导出文章 RIS 引用（仅 published）。
    """
    article = _get_published_article_for_citation(id)
    payload = _build_citation_payload(article)
    content = _to_ris(payload)
    filename = f"scholarflow-{payload['article_id'] or id}.ris"
    return PlainTextResponse(
        content=content,
        media_type="application/x-research-info-systems; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/manuscripts/articles/{id}/pdf-signed")
async def get_published_article_pdf_signed(id: UUID):
    """
    公开文章页 PDF 预览：返回 published 稿件的 signed URL。

    中文注释:
    - 文章页通常不要求登录；前端 iframe 无法携带 Authorization header。
    - 因此这里使用 service_role（supabase_admin）为已 published 的稿件生成 signedUrl。
    - 严格限制为 published，避免任何未发表稿件被匿名访问。
    """
    try:
        ms_resp = (
            supabase_admin.table("manuscripts")
            .select("id,status,file_path")
            .eq("id", str(id))
            .eq("status", "published")
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}
    except Exception as e:
        if _is_postgrest_single_no_rows_error(str(e)):
            raise HTTPException(status_code=404, detail="Article not found")
        raise
    if not ms:
        raise HTTPException(status_code=404, detail="Article not found")
    file_path = ms.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="Article PDF not found")

    signed_url = _get_signed_url_for_manuscripts_bucket(str(file_path))
    return {"success": True, "data": {"signed_url": signed_url}}

@router.get("/manuscripts/articles/{id}/pdf")
async def get_published_article_pdf(id: UUID):
    """
    公开文章页 PDF 下载入口：302 重定向到 signed URL。

    中文注释:
    - MVP 允许用 redirect 方式提供 PDF 下载。
    - signed URL 有有效期；若需要长期稳定 URL，可在未来把 published 文件迁到 public bucket 或配置 public read policy。
    """
    try:
        ms_resp = (
            supabase_admin.table("manuscripts")
            .select("id,status,file_path")
            .eq("id", str(id))
            .eq("status", "published")
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}
    except Exception as e:
        if _is_postgrest_single_no_rows_error(str(e)):
            raise HTTPException(status_code=404, detail="Article not found")
        raise
    if not ms:
        raise HTTPException(status_code=404, detail="Article not found")
    file_path = ms.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="Article PDF not found")

    signed_url = _get_signed_url_for_manuscripts_bucket(str(file_path))
    resp = RedirectResponse(url=signed_url, status_code=302)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@router.patch("/manuscripts/{manuscript_id}")
async def update_manuscript(
    manuscript_id: UUID,
    owner_id: Optional[UUID] = Body(None, embed=True),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    Feature 023: 允许 Editor/Admin 更新稿件 owner_id（KPI 归属人绑定）。

    中文注释:
    - owner_id 允许为空（自然投稿/未绑定）。
    - 若传入非空 owner_id，必须校验其角色为 editor/admin（防止误绑定外部作者/审稿人）。
    """
    try:
        update_data = {
            "owner_id": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if owner_id is not None:
            try:
                validate_internal_owner_id(owner_id)
            except ValueError:
                raise HTTPException(status_code=422, detail="owner_id must be editor/admin")
            update_data["owner_id"] = str(owner_id)

        resp = (
            supabase_admin.table("manuscripts")
            .update(update_data)
            .eq("id", str(manuscript_id))
            .execute()
        )
        data = getattr(resp, "data", None) or []
        if not data:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        return {"success": True, "data": data[0]}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[OwnerBinding] 更新 owner_id 失败: {e}")
        raise HTTPException(status_code=500, detail="Failed to update manuscript")


@router.post("/manuscripts")
async def create_manuscript(
    manuscript: ManuscriptCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """创建新稿件（需要登录）"""
    try:
        # 生成新的稿件 ID
        manuscript_id = uuid4()
        current_user_id = str(current_user.get("id") or "").strip()

        cover_letter_path = str(manuscript.cover_letter_path or "").strip()
        cover_letter_filename = str(manuscript.cover_letter_filename or "").strip() or None
        cover_letter_content_type = str(manuscript.cover_letter_content_type or "").strip() or None

        if cover_letter_path:
            # 中文注释: 防止恶意构造 path 绑定他人文件或目录穿越路径
            if ".." in cover_letter_path or cover_letter_path.startswith("/"):
                raise HTTPException(status_code=422, detail="Invalid cover_letter_path")
            if current_user_id and not cover_letter_path.startswith(f"{current_user_id}/"):
                raise HTTPException(status_code=422, detail="cover_letter_path must belong to current user")
            lowered_cover_path = cover_letter_path.lower()
            if not (
                lowered_cover_path.endswith(".pdf")
                or lowered_cover_path.endswith(".doc")
                or lowered_cover_path.endswith(".docx")
            ):
                raise HTTPException(status_code=422, detail="Cover letter only supports .pdf/.doc/.docx")

        # 使用当前登录用户的 ID，而不是传入的 author_id
        data = {
            "id": str(manuscript_id),
            "title": manuscript.title,
            "abstract": manuscript.abstract,
            "file_path": manuscript.file_path,
            "dataset_url": manuscript.dataset_url,
            "source_code_url": manuscript.source_code_url,
            "author_id": current_user_id,  # 使用真实的用户 ID
            "status": "pre_check",
            "owner_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # 插入到数据库
        response = supabase.table("manuscripts").insert(data).execute()

        if response.data:
            created = response.data[0]

            if cover_letter_path:
                try:
                    supabase_admin.table("manuscript_files").upsert(
                        {
                            "manuscript_id": str(manuscript_id),
                            "file_type": "cover_letter",
                            "bucket": "manuscripts",
                            "path": cover_letter_path,
                            "original_filename": cover_letter_filename,
                            "content_type": cover_letter_content_type,
                            "uploaded_by": current_user_id or None,
                        },
                        on_conflict="bucket,path",
                    ).execute()
                except Exception as e:
                    # 中文注释: cover letter 元数据写入失败时回滚稿件，避免出现“稿件已提交但附件丢失”
                    try:
                        supabase_admin.table("manuscripts").delete().eq("id", str(manuscript_id)).execute()
                    except Exception as rollback_error:
                        print(f"[CoverLetter] rollback manuscript failed: {rollback_error}")

                    if _is_missing_table_error(str(e), "manuscript_files"):
                        raise HTTPException(status_code=500, detail="DB not migrated: manuscript_files table missing")
                    print(f"[CoverLetter] persist failed: {e}")
                    raise HTTPException(status_code=500, detail="Failed to save cover letter metadata")

            # === 通知中心 (Feature 011) ===
            # 中文注释:
            # 1) 投稿成功：作者收到站内信 + 邮件（异步）。
            # 2) 新投稿提醒：所有 editor/admin 账号收到站内信（邮件可在后续扩展）。
            notification_service = NotificationService()
            notification_service.create_notification(
                user_id=current_user["id"],
                manuscript_id=str(manuscript_id),
                type="submission",
                title="Submission Received",
                content=f"Your manuscript '{manuscript.title}' has been successfully submitted.",
            )

            # MVP：不再给“所有编辑”群发通知。
            # 中文注释:
            # - Editor Pipeline 本身就能看到 submitted 列表；
            # - 云端可能存在 mock user_profiles（不对应 auth.users），群发会导致大量 409(外键冲突) 日志刷屏。

            # 异步发送邮件（失败不影响主流程）
            try:
                author_email = current_user.get("email")
                if author_email:
                    email_service = EmailService()
                    background_tasks.add_task(
                        email_service.send_template_email,
                        to_email=author_email,
                        subject="Submission Received",
                        template_name="submission_ack.html",
                        context={
                            "subject": "Submission Received",
                            "recipient_name": author_email.split("@")[0]
                            .replace(".", " ")
                            .title(),
                            "manuscript_title": manuscript.title,
                            "manuscript_id": str(manuscript_id),
                        },
                    )
            except Exception as e:
                print(f"[SMTP] 异步发送任务创建失败（降级忽略）: {e}")

            return {"success": True, "data": created}
        else:
            return {"success": False, "message": "Failed to create manuscript"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"创建稿件失败: {str(e)}")
        return {"success": False, "message": str(e)}


@router.get("/manuscripts/journals/{slug}")
async def get_journal_detail(slug: str):
    try:
        journal_response = (
            supabase.table("journals").select("*").eq("slug", slug).single().execute()
        )
        journal = journal_response.data
        if not journal:
            raise HTTPException(status_code=404, detail="Journal not found")
        articles_response = (
            supabase.table("manuscripts")
            .select("*")
            .eq("journal_id", journal["id"])
            .eq("status", "published")
            .execute()
        )
        return {"success": True, "journal": journal, "articles": articles_response.data}
    except HTTPException:
        raise
    except Exception as e:
        print(f"期刊详情查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch journal detail")
