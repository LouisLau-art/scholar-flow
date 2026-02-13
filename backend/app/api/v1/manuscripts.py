from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Body,
    Depends,
)
from fastapi.responses import Response
import httpx
from app.core.pdf_processor import extract_text_and_layout_from_pdf
from app.core.ai_engine import parse_manuscript_metadata
from app.core.plagiarism_worker import plagiarism_check_worker
from app.services.editorial_service import process_quality_check
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role, get_current_profile
from app.services.owner_binding_service import validate_internal_owner_id
from app.api.v1.manuscripts_detail import router as manuscripts_detail_router
from app.api.v1.manuscripts_public import router as manuscripts_public_router
from app.api.v1.manuscripts_submission import router as manuscripts_submission_router
from app.services.invoice_pdf_service import (
    generate_and_store_invoice_pdf,
    get_invoice_pdf_signed_url,
)
from app.services.post_acceptance_service import publish_manuscript as publish_manuscript_post_acceptance
from app.services.decision_service import DecisionService
from app.services.production_workspace_service import ProductionWorkspaceService
from app.models.production_workspace import SubmitProofreadingRequest
from uuid import UUID
import os
import time
from datetime import datetime, timezone
from typing import Optional, Any

router = APIRouter(tags=["Manuscripts"])
router.include_router(manuscripts_detail_router)
router.include_router(manuscripts_public_router)
router.include_router(manuscripts_submission_router)

# 中文注释:
# - 兼容历史测试通过 `app.api.v1.manuscripts.*` 做 monkeypatch 的路径。
# - 实际路由实现已拆到子模块，但仍需在此模块保留符号导出。
_MONKEYPATCH_COMPAT_EXPORTS = (
    extract_text_and_layout_from_pdf,
    parse_manuscript_metadata,
    plagiarism_check_worker,
    process_quality_check,
)

_PRIVATE_PROGRESS_ORDER: list[str] = [
    "submitted",
    "pre_check",
    "under_review",
    "revision_requested",
    "resubmitted",
    "decision",
    "approved",
    "layout",
    "english_editing",
    "proofreading",
    "published",
]

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


def _is_missing_specific_column_error(error_text: str, column_name: str) -> bool:
    lowered = str(error_text or "").lower()
    col = str(column_name or "").strip().lower()
    if not col:
        return False
    return col in lowered and "does not exist" in lowered


def _validate_submission_journal_id(journal_id: UUID | None) -> str | None:
    """
    校验投稿绑定的 journal_id 是否可用（存在且未停用）。

    中文注释:
    - 仅当作者提交了 journal_id 才触发校验，保持历史客户端兼容。
    - 若云端尚未迁移 journals.is_active，则退化为“只校验存在性”。
    """
    if journal_id is None:
        return None

    target_id = str(journal_id)
    try:
        resp = (
            supabase_admin.table("journals")
            .select("id,is_active")
            .eq("id", target_id)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=422, detail="Invalid journal_id")
        row = rows[0] or {}
        if row.get("is_active") is False:
            raise HTTPException(status_code=422, detail="Selected journal is inactive")
        return target_id
    except HTTPException:
        raise
    except Exception as e:
        if _is_missing_specific_column_error(str(e), "is_active"):
            fallback = (
                supabase_admin.table("journals")
                .select("id")
                .eq("id", target_id)
                .limit(1)
                .execute()
            )
            rows = getattr(fallback, "data", None) or []
            if not rows:
                raise HTTPException(status_code=422, detail="Invalid journal_id")
            return target_id
        raise HTTPException(status_code=500, detail="Failed to validate journal")


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

def _normalize_private_progress_status(raw_status: Any) -> str:
    status = str(raw_status or "").strip().lower()
    if status in {"minor_revision", "major_revision", "revision_required", "revision_requested", "returned_for_revision", "return_for_revision"}:
        return "revision_requested"
    if status == "decision_done":
        return "decision"
    return status


def _order_private_progress_statuses(statuses: set[str]) -> list[str]:
    ordered: list[str] = [step for step in _PRIVATE_PROGRESS_ORDER if step in statuses]
    extras = sorted(status for status in statuses if status and status not in _PRIVATE_PROGRESS_ORDER)
    ordered.extend(extras)
    return ordered


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
    - 这里显式做访问控制：仅作者本人 / 被分配 reviewer / managing_editor/admin 可取 signedUrl。
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
    if roles.intersection({"admin", "managing_editor"}):
        allowed = True
    elif str(ms.get("author_id") or "") == user_id:
        allowed = True
    else:
        # Reviewer: 允许已指派 reviewer 预览（避免 managing_editor 通过 UI 分配后 reviewer 侧打不开 PDF）
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
    is_internal = bool(roles.intersection({"admin", "managing_editor"}))

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

    if not (roles.intersection({"admin", "managing_editor"}) or str(ms.get("author_id") or "") == user_id):
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
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
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
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
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
    if roles.intersection({"admin", "managing_editor"}):
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
    - Internal（admin / managing_editor / editor_in_chief / assistant_editor）可读取内部视图
    - assistant_editor 仅可读取自己被分配稿件，避免越权
    """
    user_id = str(current_user.get("id"))
    roles = {str(role).strip().lower() for role in ((profile or {}).get("roles") or []) if str(role).strip()}

    ms_resp = (
        supabase_admin.table("manuscripts")
        .select("id, author_id, assistant_editor_id")
        .eq("id", str(manuscript_id))
        .single()
        .execute()
    )
    ms = getattr(ms_resp, "data", None) or {}
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    is_author = str(ms.get("author_id") or "") == user_id
    is_internal = bool(roles.intersection({"admin", "managing_editor", "editor_in_chief", "assistant_editor"}))
    if not (is_author or is_internal):
        raise HTTPException(status_code=403, detail="Forbidden")

    # 中文注释:
    # - assistant_editor 只能查看自己名下稿件的审稿反馈；
    # - 对 admin / managing_editor / editor_in_chief 保持现有内部可见行为。
    has_privileged_internal_role = bool(roles.intersection({"admin", "managing_editor", "editor_in_chief"}))
    if not is_author and "assistant_editor" in roles and not has_privileged_internal_role:
        assigned_ae_id = str(ms.get("assistant_editor_id") or "").strip()
        if not assigned_ae_id or assigned_ae_id != user_id:
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
        rows = response.data or []

        # 中文注释: 生产校对（Proofreading）任务入口。
        # - 作者端需要知道哪些稿件“正在等待作者校对”，否则只看到发票/稿件下载会造成流程断裂。
        # - 为避免前端对每条稿件再发 N 次请求，这里做一次批量查询并把结果附在列表项上（向后兼容）。
        proofreading_by_ms: dict[str, dict] = {}
        try:
            manuscript_ids = [str(r.get("id") or "").strip() for r in rows if r.get("id")]
            manuscript_ids = [mid for mid in manuscript_ids if mid]
            if manuscript_ids:
                pc_resp = (
                    supabase.table("production_cycles")
                    .select("id,manuscript_id,cycle_no,status,proof_due_at,updated_at")
                    .in_("manuscript_id", manuscript_ids)
                    .eq("proofreader_author_id", str(current_user.get("id") or ""))
                    .in_("status", ["awaiting_author", "author_confirmed", "author_corrections_submitted"])
                    .order("cycle_no", desc=True)
                    .order("updated_at", desc=True)
                    .execute()
                )
                pc_rows = getattr(pc_resp, "data", None) or []
                for row in pc_rows:
                    mid = str(row.get("manuscript_id") or "").strip()
                    if not mid:
                        continue
                    current = proofreading_by_ms.get(mid)
                    if not current:
                        proofreading_by_ms[mid] = row
                        continue
                    try:
                        if int(row.get("cycle_no") or 0) > int(current.get("cycle_no") or 0):
                            proofreading_by_ms[mid] = row
                    except Exception:
                        # 保守: 不因为脏数据影响列表
                        pass
        except Exception as e:
            # 保守兜底：某些环境可能尚未迁移 production_cycles；作者列表不应被阻塞。
            print(f"[AuthorMine] proofreading task probe failed (ignored): {e}")
            proofreading_by_ms = {}

        for r in rows:
            mid = str(r.get("id") or "").strip()
            task = proofreading_by_ms.get(mid)
            if task:
                status = str(task.get("status") or "").strip()
                r["proofreading_task"] = {
                    "cycle_id": task.get("id"),
                    "cycle_no": task.get("cycle_no"),
                    "status": status,
                    "proof_due_at": task.get("proof_due_at"),
                    "action_required": status == "awaiting_author",
                    "url": f"/proofreading/{mid}",
                }
            else:
                r["proofreading_task"] = None

        return {"success": True, "data": rows}
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

@router.patch("/manuscripts/{manuscript_id}")
async def update_manuscript(
    manuscript_id: UUID,
    owner_id: Optional[UUID] = Body(None, embed=True),
    _profile: dict = Depends(require_any_role(["managing_editor", "admin"])),
):
    """
    Feature 023: 允许 Editor/Admin 更新稿件 owner_id（KPI 归属人绑定）。

    中文注释:
    - owner_id 允许为空（自然投稿/未绑定）。
    - 若传入非空 owner_id，必须校验其角色为 managing_editor/admin（防止误绑定外部作者/审稿人）。
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
                raise HTTPException(status_code=422, detail="owner_id must be managing_editor/admin")
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
