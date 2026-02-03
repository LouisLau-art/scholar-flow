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
from fastapi.responses import JSONResponse, Response
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
from app.models.revision import RevisionSubmitResponse, VersionHistoryResponse
from app.core.roles import require_any_role, get_current_profile
from app.services.owner_binding_service import get_profile_for_owner, validate_internal_owner_id
from app.core.invoice_generator import build_invoice_pdf_bytes
from app.services.post_acceptance_service import publish_manuscript as publish_manuscript_post_acceptance
from uuid import uuid4, UUID
import shutil
import os
import asyncio
import tempfile
import time
from datetime import datetime, timezone
from typing import Optional

router = APIRouter(tags=["Manuscripts"])

def _is_truthy_env(name: str, default: str = "0") -> bool:
    v = (os.environ.get(name, default) or "").strip().lower()
    return v in {"1", "true", "yes", "on"}

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


@router.get("/manuscripts/{manuscript_id}/invoice")
async def download_invoice_pdf(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    Feature 024: 下载账单 PDF（Author / Editor / Admin）

    中文注释:
    - PDF 即时生成（ReportLab），避免存储/权限复杂度。
    """
    user_id = str(current_user["id"])
    roles = set((profile or {}).get("roles") or [])

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
        .select("id, amount")
        .eq("manuscript_id", str(manuscript_id))
        .limit(1)
        .execute()
    )
    inv_rows = getattr(inv_resp, "data", None) or []
    if not inv_rows:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv = inv_rows[0]

    try:
        amount = float(inv.get("amount") or 0)
    except Exception:
        amount = 0.0

    pdf_bytes = build_invoice_pdf_bytes(
        invoice_id=UUID(str(inv.get("id"))),
        manuscript_title=str(ms.get("title") or "Manuscript"),
        amount=float(amount),
    )
    if not pdf_bytes:
        raise HTTPException(status_code=500, detail="Failed to generate invoice pdf")

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

    if (ms.get("status") or "").lower() != "approved":
        raise HTTPException(status_code=400, detail="Only approved manuscripts can upload production file")

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
        if "final_pdf_path" in err.lower() and "column" in err.lower():
            raise HTTPException(
                status_code=500,
                detail="Database schema missing final_pdf_path. Please apply migrations for Feature 024.",
            )
        raise HTTPException(status_code=500, detail="Failed to update production file path")

    return {"success": True, "data": {"final_pdf_path": path}}


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
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            temp_path = tmp.name
            shutil.copyfileobj(file.file, tmp)

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
            text, layout_lines = await asyncio.wait_for(
                asyncio.to_thread(extract_text_and_layout_from_pdf, temp_path, max_pages=max_pages, max_chars=max_chars),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            # 超时直接降级：允许用户手动填写 title/abstract
            return {
                "success": True,
                "id": manuscript_id,
                "data": {"title": "", "abstract": "", "authors": []},
                "message": f"PDF 解析超时（>{timeout_sec:.0f}s），已跳过 AI 解析，可手动填写。",
            }

        # 元数据提取：本地解析（无 HTTP），仅用于前端预填
        meta_start = time.monotonic()
        metadata = await parse_manuscript_metadata(text or "", layout_lines=layout_lines or [])
        meta_cost = time.monotonic() - meta_start
        total_cost = time.monotonic() - start
        print(
            f"[UploadManuscript] parsed: pdf_timeout={timeout_sec:.1f}s max_pages={max_pages} "
            f"max_chars={max_chars} meta_time={meta_cost:.2f}s total={total_cost:.2f}s"
        )

        # 该接口仅用于前端预填元数据；查重属于“可选项”，且当前实现为 Mock，默认关闭以提速。
        # 如需开启：export PLAGIARISM_CHECK_ENABLED=1
        if _is_truthy_env("PLAGIARISM_CHECK_ENABLED", "0"):
            background_tasks.add_task(plagiarism_check_worker, str(manuscript_id))
        return {"success": True, "id": manuscript_id, "data": metadata}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e), "data": {"title": "", "abstract": "", "authors": []}},
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
        res = supabase_admin.storage.from_("manuscripts").upload(
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


@router.get("/manuscripts/published/latest")
async def get_latest_published_articles(limit: int = 6):
    """
    Feature 024: 首页“Latest Articles”数据源（仅 published，按 published_at 倒序）
    """
    try:
        n = max(1, min(int(limit), 50))
    except Exception:
        n = 6

    try:
        # 优先按 published_at 排序；若环境缺列，则退化为 created_at
        try:
            resp = (
                supabase.table("manuscripts")
                .select("id,title,abstract,doi,published_at,journal_id")
                .eq("status", "published")
                .order("published_at", desc=True)
                .limit(n)
                .execute()
            )
        except Exception as e:
            if "published_at" in str(e).lower():
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
        manuscript_response = (
            supabase.table("manuscripts")
            .select("*")
            .eq("id", str(id))
            .single()
            .execute()
        )
        manuscript = manuscript_response.data
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
        # 使用当前登录用户的 ID，而不是传入的 author_id
        data = {
            "id": str(manuscript_id),
            "title": manuscript.title,
            "abstract": manuscript.abstract,
            "file_path": manuscript.file_path,
            "dataset_url": manuscript.dataset_url,
            "source_code_url": manuscript.source_code_url,
            "author_id": current_user["id"],  # 使用真实的用户 ID
            "status": "submitted",
            "owner_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # 插入到数据库
        response = supabase.table("manuscripts").insert(data).execute()

        if response.data:
            created = response.data[0]

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
