import asyncio
import os
import shutil
import tempfile
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.auth_utils import get_current_user
from app.core.email_normalization import normalize_email
from app.core.mail import EmailService
from app.models.revision import RevisionSubmitResponse
from app.models.schemas import ManuscriptCreate
from app.services.notification_service import NotificationService
from app.services.plagiarism_service import PlagiarismService
from app.services.revision_service import RevisionService

router = APIRouter(tags=["Manuscripts"])


def _m():
    # 中文注释:
    # - 运行时回取主模块，避免循环导入问题。
    # - 兼容现有测试通过 app.api.v1.manuscripts.* 做 monkeypatch。
    from app.api.v1 import manuscripts as manuscripts_api

    return manuscripts_api


def _ensure_author_role_membership(user_id: str, email: str | None) -> None:
    """
    投稿成功后，确保当前用户具备 author 角色。

    中文注释:
    - 历史上存在 reviewer-only 账号也可投稿的情况。
    - 若不在这里补 author，Dashboard 会因为 roles 缺 author 而不显示作者视图。
    - 这里做“幂等补齐”，不阻塞投稿主流程。
    """
    target_user_id = str(user_id or "").strip()
    if not target_user_id:
        return

    normalized_email = normalize_email(email)

    try:
        resp = (
            _m().supabase_admin.table("user_profiles")
            .select("id,email,roles")
            .eq("id", target_user_id)
            .limit(1)
            .execute()
        )
        existing = ((getattr(resp, "data", None) or [None])[0]) or None

        if existing:
            existing_roles = [str(role).strip() for role in (existing.get("roles") or []) if str(role).strip()]
            payload: dict[str, object] = {}
            if "author" not in existing_roles:
                payload["roles"] = [*existing_roles, "author"]
            existing_email = normalize_email(existing.get("email"))
            if normalized_email and normalized_email != existing_email:
                payload["email"] = normalized_email
            if payload:
                (
                    _m().supabase_admin.table("user_profiles")
                    .update(payload)
                    .eq("id", target_user_id)
                    .execute()
                )
            return

        (
            _m().supabase_admin.table("user_profiles")
            .insert(
                {
                    "id": target_user_id,
                    "email": normalized_email,
                    "roles": ["author"],
                }
            )
            .execute()
        )
    except Exception as e:
        print(f"[SubmissionAuthorRole] failed to ensure author role: {e}", flush=True)


@router.post("/manuscripts/upload")
async def upload_manuscript(
    background_tasks: BackgroundTasks, file: UploadFile = File(...)
):
    """稿件上传与 AI 解析"""
    filename = (file.filename or "").strip()
    lowered_name = filename.lower()
    is_pdf = lowered_name.endswith(".pdf")
    is_docx = lowered_name.endswith(".docx")
    is_doc = lowered_name.endswith(".doc")

    if not (is_pdf or is_docx or is_doc):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "仅支持 PDF / DOCX / DOC 格式文件",
                "data": {"title": "", "abstract": "", "authors": []},
            },
        )

    manuscript_id = uuid4()
    temp_path = None
    start = time.monotonic()
    trace_id = str(manuscript_id)[:8]
    try:
        suffix = ".pdf" if is_pdf else ".docx" if is_docx else ".doc"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
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

        parser_mode = "pdf" if is_pdf else "docx"

        if is_pdf:
            try:
                text, layout_lines = await asyncio.wait_for(
                    asyncio.to_thread(
                        _m().extract_text_and_layout_from_pdf,
                        temp_path,
                        max_pages=max_pages,
                        max_chars=max_chars,
                        layout_max_pages=layout_max_pages_override,
                    ),
                    timeout=timeout_sec,
                )
            except asyncio.TimeoutError:
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
        elif is_docx:
            try:
                text = await asyncio.wait_for(
                    asyncio.to_thread(
                        _m().extract_text_from_docx,
                        temp_path,
                        max_chars=max_chars,
                    ),
                    timeout=timeout_sec,
                )
                layout_lines = []
            except asyncio.TimeoutError:
                print(
                    f"[UploadManuscript:{trace_id}] timeout in docx extraction (> {timeout_sec:.1f}s), fallback manual fill",
                    flush=True,
                )
                return {
                    "success": True,
                    "id": manuscript_id,
                    "trace_id": trace_id,
                    "data": {"title": "", "abstract": "", "authors": []},
                    "message": f"DOCX 解析超时（>{timeout_sec:.0f}s），已跳过 AI 解析，可手动填写。",
                }
        else:
            # 中文注释：历史 .doc 二进制格式在无外部依赖条件下不做自动抽取，直接降级手填。
            text = None
            layout_lines = []
            print(
                f"[UploadManuscript:{trace_id}] legacy .doc uploaded, skip auto parsing",
                flush=True,
            )
            return {
                "success": True,
                "id": manuscript_id,
                "trace_id": trace_id,
                "data": {"title": "", "abstract": "", "authors": []},
                "message": "检测到 .doc（旧格式），暂不支持自动抽取，请手动填写标题与摘要。",
            }

        meta_start = time.monotonic()
        try:
            meta_timeout_sec = float(os.environ.get("PDF_METADATA_TIMEOUT_SEC", "4"))
        except Exception:
            meta_timeout_sec = 4.0

        try:
            metadata = await asyncio.wait_for(
                _m().parse_manuscript_metadata(text or "", layout_lines=layout_lines or []),
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
            f"[UploadManuscript:{trace_id}] parsed: mode={parser_mode} parse_timeout={timeout_sec:.1f}s max_pages={max_pages} "
            f"max_chars={max_chars} layout_override={layout_max_pages_override} meta_time={meta_cost:.2f}s total={total_cost:.2f}s"
            f" text_len={len(text or '')} layout_lines={len(layout_lines or [])}",
            flush=True,
        )

        if _m()._is_truthy_env("PLAGIARISM_CHECK_ENABLED", "0"):
            try:
                PlagiarismService().ensure_report(str(manuscript_id), reset_status=False)
            except Exception as e:
                print(f"[UploadManuscript:{trace_id}] init plagiarism report failed (ignored): {e}", flush=True)
            background_tasks.add_task(_m().plagiarism_check_worker, str(manuscript_id))
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
    word_file: UploadFile | None = File(None),
    pdf_file: UploadFile | None = File(None),
    file: UploadFile | None = File(None),  # 兼容旧客户端字段名（PDF）
    current_user: dict = Depends(get_current_user),
):
    """
    Author 提交修订稿 (Submit Revision)
    """
    # 中文注释:
    # - 业务改为修回必须同时提交 Word + PDF：Word 供后续编辑，PDF 供外审/阅读。
    # - 兼容旧客户端仅传 file=...（视作 PDF）。
    normalized_pdf_file = pdf_file or file
    if not normalized_pdf_file:
        raise HTTPException(status_code=400, detail="Please upload revised manuscript PDF.")
    if not word_file:
        raise HTTPException(status_code=400, detail="Please upload revised manuscript Word file.")

    pdf_filename = str(normalized_pdf_file.filename or "").strip()
    word_filename = str(word_file.filename or "").strip()
    if not pdf_filename:
        raise HTTPException(status_code=400, detail="Revised manuscript PDF filename is empty.")
    if not word_filename:
        raise HTTPException(status_code=400, detail="Revised manuscript Word filename is empty.")
    if not pdf_filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Revised manuscript PDF only supports .pdf")
    if not (word_filename.lower().endswith(".doc") or word_filename.lower().endswith(".docx")):
        raise HTTPException(status_code=400, detail="Revised manuscript Word only supports .doc/.docx")

    service = RevisionService()

    manuscript = service.get_manuscript(str(manuscript_id))
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    if str(manuscript.get("author_id")) != str(current_user["id"]):
        raise HTTPException(
            status_code=403, detail="Only the author can submit revisions"
        )

    pending = service.ensure_pending_revision_for_submit(
        str(manuscript_id), manuscript=manuscript
    )
    if not pending:
        raise HTTPException(status_code=400, detail="No pending revision request found")
    precheck_resubmit_stage: str | None = None
    if isinstance(pending, dict):
        derived_stage = str(pending.get("__derived_precheck_stage") or "").strip().lower()
        if derived_stage in {"intake", "technical"}:
            precheck_resubmit_stage = derived_stage

    next_version = (manuscript.get("version", 1)) + 1
    pdf_file_path = service.generate_versioned_file_path(
        str(manuscript_id), pdf_filename, next_version
    )
    word_file_path = service.generate_versioned_file_path(
        str(manuscript_id), word_filename, next_version
    )

    def _is_duplicate_upload_error(error: Exception) -> bool:
        lowered = str(error).lower()
        return "duplicate" in lowered or "already exists" in lowered or "409" in lowered

    def _upload_file_with_retry(path: str, content: bytes, content_type: str) -> str:
        try:
            _m().supabase_admin.storage.from_("manuscripts").upload(
                path, content, {"content-type": content_type}
            )
            return path
        except Exception as upload_error:
            if not _is_duplicate_upload_error(upload_error):
                raise
            base_path, ext = os.path.splitext(path)
            retry_path = f"{base_path}_{uuid4().hex[:8]}{ext}"
            _m().supabase_admin.storage.from_("manuscripts").upload(
                retry_path, content, {"content-type": content_type}
            )
            return retry_path

    uploaded_paths: list[str] = []
    word_metadata_saved = False
    uploaded_pdf_path: str | None = None
    uploaded_word_path: str | None = None

    try:
        pdf_content = await normalized_pdf_file.read()
        word_content = await word_file.read()
        if not pdf_content:
            raise HTTPException(status_code=400, detail="Uploaded PDF file is empty")
        if not word_content:
            raise HTTPException(status_code=400, detail="Uploaded Word file is empty")

        pdf_content_type = str(normalized_pdf_file.content_type or "").strip() or "application/pdf"
        word_content_type = str(word_file.content_type or "").strip()
        if not word_content_type:
            word_content_type = (
                "application/msword"
                if word_filename.lower().endswith(".doc")
                else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        uploaded_pdf_path = _upload_file_with_retry(pdf_file_path, pdf_content, pdf_content_type)
        uploaded_paths.append(uploaded_pdf_path)
        uploaded_word_path = _upload_file_with_retry(word_file_path, word_content, word_content_type)
        uploaded_paths.append(uploaded_word_path)

        try:
            _m().supabase_admin.table("manuscript_files").upsert(
                {
                    "manuscript_id": str(manuscript_id),
                    "file_type": "manuscript",
                    "bucket": "manuscripts",
                    "path": uploaded_word_path,
                    "original_filename": word_filename,
                    "content_type": word_content_type,
                    "uploaded_by": str(current_user.get("id") or "").strip() or None,
                },
                on_conflict="bucket,path",
            ).execute()
            word_metadata_saved = True
        except Exception as metadata_error:
            if _m()._is_missing_table_error(str(metadata_error), "manuscript_files"):
                raise HTTPException(status_code=500, detail="DB not migrated: manuscript_files table missing")
            raise HTTPException(status_code=500, detail="Failed to save revised Word file metadata")
    except HTTPException:
        if uploaded_paths:
            try:
                _m().supabase_admin.storage.from_("manuscripts").remove(uploaded_paths)
            except Exception as cleanup_error:
                print(f"[RevisionSubmit] upload rollback failed (ignored): {cleanup_error}")
        raise
    except Exception as e:
        if uploaded_paths:
            try:
                _m().supabase_admin.storage.from_("manuscripts").remove(uploaded_paths)
            except Exception as cleanup_error:
                print(f"[RevisionSubmit] upload rollback failed (ignored): {cleanup_error}")
        print(f"Revision files upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

    result = service.submit_revision(
        manuscript_id=str(manuscript_id),
        author_id=str(current_user["id"]),
        new_file_path=str(uploaded_pdf_path or ""),
        response_letter=response_letter,
        precheck_resubmit_stage=precheck_resubmit_stage,
    )

    if not result["success"]:
        if uploaded_paths:
            try:
                _m().supabase_admin.storage.from_("manuscripts").remove(uploaded_paths)
            except Exception as cleanup_error:
                print(f"[RevisionSubmit] cleanup failed (ignored): {cleanup_error}")
        if word_metadata_saved and uploaded_word_path:
            try:
                _m().supabase_admin.table("manuscript_files").delete().eq("bucket", "manuscripts").eq(
                    "path", uploaded_word_path
                ).execute()
            except Exception as cleanup_error:
                print(f"[RevisionSubmit] word metadata rollback failed (ignored): {cleanup_error}")
        raise HTTPException(status_code=400, detail=result["error"])

    try:
        notification_service = NotificationService()

        notification_service.create_notification(
            user_id=str(current_user["id"]),
            manuscript_id=str(manuscript_id),
            type="submission",
            title="Revision Submitted",
            content=f"Your revision for '{manuscript.get('title')}' has been submitted.",
        )

        recipients: set[str] = set()
        owner_id = manuscript.get("owner_id") or manuscript.get("kpi_owner_id")
        editor_id = manuscript.get("editor_id")
        if owner_id:
            recipients.add(str(owner_id))
        if editor_id:
            recipients.add(str(editor_id))

        result_data = (result or {}).get("data") or {}
        updated_status = str(result_data.get("manuscript_status") or "").strip().lower()
        updated_pre_stage = str(result_data.get("pre_check_status") or "").strip().lower()

        if updated_status == "pre_check":
            if updated_pre_stage == "technical":
                ae_id = str(manuscript.get("assistant_editor_id") or "").strip()
                if ae_id:
                    recipients.add(ae_id)
            elif updated_pre_stage == "intake" and not recipients:
                try:
                    logs_resp = (
                        _m()
                        .supabase_admin.table("status_transition_logs")
                        .select("changed_by,payload,to_status,created_at")
                        .eq("manuscript_id", str(manuscript_id))
                        .order("created_at", desc=True)
                        .limit(20)
                        .execute()
                    )
                    logs = getattr(logs_resp, "data", None) or []
                    for row in logs:
                        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
                        action = str(payload.get("action") or "").strip().lower()
                        changed_by = str(row.get("changed_by") or "").strip()
                        if action in {"precheck_intake_revision", "precheck_technical_revision"} and changed_by:
                            recipients.add(changed_by)
                            break
                except Exception as e:
                    print(f"[Notifications] load precheck fallback recipient failed (ignored): {e}")

        recipients.discard(str(current_user["id"]))

        inbox_title = "Revision Received"
        inbox_content = f"A revision for '{manuscript.get('title')}' has been submitted."
        if updated_status == "pre_check":
            if updated_pre_stage == "intake":
                inbox_title = "Revision Returned to Intake"
                inbox_content = f"Author resubmitted '{manuscript.get('title')}'. Please review it in Intake Queue."
            elif updated_pre_stage == "technical":
                inbox_title = "Revision Returned to Technical Check"
                inbox_content = f"Author resubmitted '{manuscript.get('title')}'. Please continue technical check."

        if updated_status == "pre_check" and updated_pre_stage == "intake":
            editor_action_url = f"/editor/manuscript/{manuscript_id}?from=intake"
        elif updated_status == "pre_check" and updated_pre_stage == "technical":
            editor_action_url = f"/editor/manuscript/{manuscript_id}?from=workspace"
        else:
            editor_action_url = f"/editor/manuscript/{manuscript_id}?from=process"

        for uid in sorted(recipients):
            notification_service.create_notification(
                user_id=uid,
                manuscript_id=str(manuscript_id),
                type="system",
                title=inbox_title,
                content=inbox_content,
                action_url=editor_action_url,
            )

    except Exception as e:
        print(f"[Notifications] Failed to send revision notification: {e}")

    return RevisionSubmitResponse(data=result["data"])


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

    try:
        _m().validate_internal_owner_id(resolved_owner_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="owner_id must be managing_editor/admin")

    result = await _m().process_quality_check(manuscript_id, passed, resolved_owner_id)
    return {"success": True, "data": result}


@router.post("/manuscripts")
async def create_manuscript(
    manuscript: ManuscriptCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """创建新稿件（需要登录）"""
    try:
        manuscript_id = uuid4()
        current_user_id = str(current_user.get("id") or "").strip()

        pdf_path = str(manuscript.file_path or "").strip()
        if not pdf_path:
            raise HTTPException(status_code=422, detail="file_path is required")
        if ".." in pdf_path or pdf_path.startswith("/"):
            raise HTTPException(status_code=422, detail="Invalid file_path")
        if current_user_id and not pdf_path.startswith(f"{current_user_id}/"):
            raise HTTPException(status_code=422, detail="file_path must belong to current user")
        if not pdf_path.lower().endswith(".pdf"):
            raise HTTPException(status_code=422, detail="Manuscript PDF only supports .pdf")

        manuscript_word_path = str(manuscript.manuscript_word_path or "").strip()
        if not manuscript_word_path:
            raise HTTPException(status_code=422, detail="manuscript_word_path is required")
        if ".." in manuscript_word_path or manuscript_word_path.startswith("/"):
            raise HTTPException(status_code=422, detail="Invalid manuscript_word_path")
        if current_user_id and not manuscript_word_path.startswith(f"{current_user_id}/"):
            raise HTTPException(status_code=422, detail="manuscript_word_path must belong to current user")
        lowered_word_path = manuscript_word_path.lower()
        if not (lowered_word_path.endswith(".doc") or lowered_word_path.endswith(".docx")):
            raise HTTPException(status_code=422, detail="Manuscript Word file only supports .doc/.docx")

        manuscript_word_filename = str(manuscript.manuscript_word_filename or "").strip() or None
        manuscript_word_content_type = str(manuscript.manuscript_word_content_type or "").strip() or None
        submission_email = str(manuscript.submission_email or "").strip().lower()
        author_contacts = [item.model_dump(mode="json") for item in manuscript.author_contacts]
        author_names = [str(item.get("name") or "").strip() for item in author_contacts if str(item.get("name") or "").strip()]
        corresponding_author = next((item for item in author_contacts if item.get("is_corresponding")), None) or {}

        cover_letter_path = str(manuscript.cover_letter_path or "").strip()
        cover_letter_filename = str(manuscript.cover_letter_filename or "").strip() or None
        cover_letter_content_type = str(manuscript.cover_letter_content_type or "").strip() or None
        validated_journal_id = _m()._validate_submission_journal_id(manuscript.journal_id)

        if cover_letter_path:
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

        data = {
            "id": str(manuscript_id),
            "title": manuscript.title,
            "abstract": manuscript.abstract,
            "file_path": pdf_path,
            "dataset_url": manuscript.dataset_url,
            "source_code_url": manuscript.source_code_url,
            "authors": author_names,
            "submission_email": submission_email,
            "author_contacts": author_contacts,
            "special_issue": manuscript.special_issue,
            "journal_id": validated_journal_id,
            "author_id": current_user_id,
            "status": "pre_check",
            "owner_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        response = _m().supabase.table("manuscripts").insert(data).execute()

        if response.data:
            created = response.data[0]

            _ensure_author_role_membership(current_user_id, current_user.get("email"))

            supplemental_files = [
                {
                    "manuscript_id": str(manuscript_id),
                    "file_type": "manuscript",
                    "bucket": "manuscripts",
                    "path": manuscript_word_path,
                    "original_filename": manuscript_word_filename,
                    "content_type": manuscript_word_content_type,
                    "uploaded_by": current_user_id or None,
                },
            ]
            if cover_letter_path:
                supplemental_files.append(
                    {
                        "manuscript_id": str(manuscript_id),
                        "file_type": "cover_letter",
                        "bucket": "manuscripts",
                        "path": cover_letter_path,
                        "original_filename": cover_letter_filename,
                        "content_type": cover_letter_content_type,
                        "uploaded_by": current_user_id or None,
                    }
                )

            try:
                for file_item in supplemental_files:
                    _m().supabase_admin.table("manuscript_files").upsert(
                        file_item,
                        on_conflict="bucket,path",
                    ).execute()
            except Exception as e:
                try:
                    _m().supabase_admin.table("manuscripts").delete().eq("id", str(manuscript_id)).execute()
                except Exception as rollback_error:
                    print(f"[SubmissionFiles] rollback manuscript failed: {rollback_error}")

                if _m()._is_missing_table_error(str(e), "manuscript_files"):
                    raise HTTPException(status_code=500, detail="DB not migrated: manuscript_files table missing")
                print(f"[SubmissionFiles] persist failed: {e}")
                raise HTTPException(status_code=500, detail="Failed to save submission file metadata")

            notification_service = NotificationService()
            notification_service.create_notification(
                user_id=current_user["id"],
                manuscript_id=str(manuscript_id),
                type="submission",
                title="Submission Received",
                content=f"Your manuscript '{manuscript.title}' has been successfully submitted.",
            )

            try:
                author_email = submission_email or str(current_user.get("email") or "").strip().lower()
                if author_email:
                    email_service = EmailService()
                    background_tasks.add_task(
                        email_service.send_template_email,
                        to_email=author_email,
                        subject="Submission Received",
                        template_name="submission_ack.html",
                        context={
                            "subject": "Submission Received",
                            "recipient_name": str(corresponding_author.get("name") or "").strip()
                            or author_email.split("@")[0].replace(".", " ").title(),
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
        raise HTTPException(status_code=500, detail="Failed to create manuscript")
