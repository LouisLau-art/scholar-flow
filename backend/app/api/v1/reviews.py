from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks, UploadFile, File, Form, Response
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.role_matrix import normalize_roles
from app.services.notification_service import NotificationService
from uuid import UUID
from typing import Any, Dict, Optional
from postgrest.exceptions import APIError
from datetime import datetime, timezone
import os

from fastapi import Cookie

from app.core.security import create_magic_link_jwt, decode_magic_link_jwt
from app.schemas.review import InviteAcceptPayload, InviteDeclinePayload, ReviewSubmission
from app.schemas.token import MagicLinkPayload
from app.core.mail import email_service
from app.services.reviewer_service import ReviewPolicyService, ReviewerInviteService, ReviewerWorkspaceService
from app.api.v1.reviews_heavy_handlers import (
    assign_reviewer_impl,
    establish_reviewer_workspace_session_impl,
    get_review_by_token_impl,
    get_manuscript_assignments_impl,
    submit_review_by_token_impl,
    submit_review_impl,
    submit_review_via_magic_link_impl,
    unassign_reviewer_impl,
)
from app.api.v1.reviews_handlers_workspace_magic import (
    accept_reviewer_invitation_impl,
    decline_reviewer_invitation_impl,
    get_review_assignment_pdf_signed_via_magic_link_impl,
    get_review_assignment_via_magic_link_impl,
    get_review_attachment_signed_by_token_impl,
    get_review_attachment_signed_impl,
    get_review_attachment_signed_via_magic_link_impl,
    get_review_feedback_for_manuscript_impl,
    get_review_pdf_signed_by_token_impl,
    get_reviewer_invite_data_impl,
    get_reviewer_workspace_data_impl,
    submit_reviewer_workspace_review_impl,
    upload_reviewer_workspace_attachment_impl,
)

router = APIRouter(tags=["Reviews"])

def _get_signed_url_for_manuscripts_bucket(file_path: str, *, expires_in: int = 60 * 10) -> str:
    """
    生成 manuscripts bucket 的 signed URL（优先使用 service_role）。

    中文注释:
    - 免登录 token 页面与 iframe 无法携带 Authorization header，因此需要后端返回可访问的 signed URL。
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


def _get_signed_url_for_review_attachments_bucket(file_path: str, *, expires_in: int = 60 * 10) -> str:
    """
    生成 review-attachments bucket 的 signed URL（优先使用 service_role）。

    中文注释:
    - review-attachments 是私有桶：Author 不可见；Reviewer/Editor 通过后端鉴权拿 signed URL 下载。
    """
    last_err: Exception | None = None
    for client in (supabase_admin, supabase):
        try:
            signed = client.storage.from_("review-attachments").create_signed_url(file_path, expires_in)
            url = (signed or {}).get("signedUrl") or (signed or {}).get("signedURL")
            if url:
                return str(url)
        except Exception as e:
            last_err = e
            continue
    raise HTTPException(status_code=500, detail=f"Failed to create signed url: {last_err}")


def _ensure_review_attachments_bucket_exists() -> None:
    """
    确保 review-attachments 桶存在（用于开发/演示环境的一键可用）。

    中文注释:
    - 正式环境建议通过 migration / Dashboard 创建 bucket。
    - 但为了减少“缺桶导致 500”的踩坑，这里做一次性兜底创建。
    """
    storage = getattr(supabase_admin, "storage", None)
    # 单元测试里会用 FakeStorage 替换；若不支持 bucket 管理方法则直接跳过
    if storage is None or not hasattr(storage, "get_bucket") or not hasattr(storage, "create_bucket"):
        return

    try:
        storage.get_bucket("review-attachments")
        return
    except Exception:
        pass
    try:
        storage.create_bucket("review-attachments", options={"public": False})
    except Exception as e:
        text = str(e).lower()
        if "already" in text or "exists" in text or "duplicate" in text:
            return
        raise

def _is_missing_relation_error(err: Exception, *, relation: str) -> bool:
    """判断是否为缺表/Schema cache 未更新错误。"""
    if not isinstance(err, APIError):
        return False
    text = str(err).lower()
    # 常见信号：
    # - Postgres: 42P01 (undefined_table)
    # - PostgREST: PGRST205 / "schema cache"
    # - 直接报 "relation ... does not exist"
    return (
        "42p01" in text
        or "pgrst205" in text
        or "schema cache" in text
        or f'"{relation.lower()}"' in text
        and "does not exist" in text
    )


def _is_foreign_key_user_error(err: Exception, *, constraint: str) -> bool:
    if not isinstance(err, APIError):
        return False
    text = str(err).lower()
    return ("23503" in text or "foreign key" in text) and constraint.lower() in text


def _safe_insert_invite_policy_audit(
    *,
    manuscript_id: str,
    from_status: str,
    to_status: str,
    changed_by: str | None,
    comment: str | None,
    payload: dict[str, Any],
) -> None:
    """
    邀请策略相关审计日志（fail-open，不影响主流程）。
    """
    base = {
        "manuscript_id": manuscript_id,
        "from_status": from_status,
        "to_status": to_status,
        "comment": comment,
        "changed_by": changed_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    candidates = [dict(base)]
    no_payload = dict(base)
    no_payload.pop("payload", None)
    candidates.append(no_payload)
    if changed_by:
        changed_by_none = dict(base)
        changed_by_none["changed_by"] = None
        changed_by_none["payload"] = {**payload, "changed_by_raw": changed_by}
        candidates.append(changed_by_none)
        changed_by_none_no_payload = dict(changed_by_none)
        changed_by_none_no_payload.pop("payload", None)
        candidates.append(changed_by_none_no_payload)

    for row in candidates:
        try:
            supabase_admin.table("status_transition_logs").insert(row).execute()
            return
        except Exception:
            continue


def _parse_roles(profile: dict | None) -> list[str]:
    raw = (profile or {}).get("roles") or []
    return [str(r).strip().lower() for r in raw if str(r).strip()]


def _ensure_review_management_access(
    *,
    manuscript: dict[str, Any],
    user_id: str,
    roles: set[str],
) -> None:
    """
    审稿人管理权限校验（assign/unassign/list）。

    规则：
    - admin: 全局允许
    - managing_editor: 受 journal scope 约束
    - assistant_editor: 仅可操作 assistant_editor_id == 自己 的稿件
    """
    if "admin" in roles:
        return

    manuscript_id = str(manuscript.get("id") or "").strip()
    if not manuscript_id:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    if "managing_editor" in roles:
        ensure_manuscript_scope_access(
            manuscript_id=manuscript_id,
            user_id=str(user_id),
            roles=roles,
        )
        return

    if "assistant_editor" in roles:
        assigned_ae = str(manuscript.get("assistant_editor_id") or "").strip()
        if assigned_ae != str(user_id).strip():
            raise HTTPException(status_code=403, detail="Forbidden: manuscript not assigned to current assistant editor")
        return

    raise HTTPException(status_code=403, detail="Insufficient role")


@router.get("/reviewer/assignments/{assignment_id}/workspace")
async def get_reviewer_workspace_data(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await get_reviewer_workspace_data_impl(
        assignment_id=assignment_id,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        reviewer_workspace_service_cls=ReviewerWorkspaceService,
    )


@router.get("/reviewer/assignments/{assignment_id}/invite")
async def get_reviewer_invite_data(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await get_reviewer_invite_data_impl(
        assignment_id=assignment_id,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        reviewer_invite_service_cls=ReviewerInviteService,
    )


@router.post("/reviewer/assignments/{assignment_id}/accept")
async def accept_reviewer_invitation(
    assignment_id: UUID,
    payload: InviteAcceptPayload,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await accept_reviewer_invitation_impl(
        assignment_id=assignment_id,
        body=payload,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        reviewer_invite_service_cls=ReviewerInviteService,
    )


@router.post("/reviewer/assignments/{assignment_id}/decline")
async def decline_reviewer_invitation(
    assignment_id: UUID,
    payload: InviteDeclinePayload,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await decline_reviewer_invitation_impl(
        assignment_id=assignment_id,
        body=payload,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        reviewer_invite_service_cls=ReviewerInviteService,
    )


@router.post("/reviewer/assignments/{assignment_id}/attachments")
async def upload_reviewer_workspace_attachment(
    assignment_id: UUID,
    file: UploadFile = File(...),
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await upload_reviewer_workspace_attachment_impl(
        assignment_id=assignment_id,
        file=file,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        reviewer_workspace_service_cls=ReviewerWorkspaceService,
        get_signed_url_for_review_attachments_bucket_fn=_get_signed_url_for_review_attachments_bucket,
    )


@router.post("/reviewer/assignments/{assignment_id}/submit")
async def submit_reviewer_workspace_review(
    assignment_id: UUID,
    body: ReviewSubmission,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await submit_reviewer_workspace_review_impl(
        assignment_id=assignment_id,
        body=body,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        reviewer_workspace_service_cls=ReviewerWorkspaceService,
    )


# === 1. 分配审稿人 (Editor Task) ===
@router.post("/reviews/assign")
async def assign_reviewer(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "assistant_editor", "admin"])),
    manuscript_id: UUID = Body(..., embed=True),
    reviewer_id: UUID = Body(..., embed=True),
    override_cooldown: bool = Body(False, embed=True),
    override_reason: str | None = Body(None, embed=True),
):
    """
    编辑分配审稿人

    中文注释:
    1. 校验逻辑: 确保 reviewer_id 不是稿件的作者 (通过 manuscripts 表查询)。
    2. 插入 review_assignments 表。
    """
    return await assign_reviewer_impl(
        background_tasks=background_tasks,
        current_user=current_user,
        profile=profile,
        manuscript_id=manuscript_id,
        reviewer_id=reviewer_id,
        override_cooldown=override_cooldown,
        override_reason=override_reason,
        supabase_client=supabase,
        supabase_admin_client=supabase_admin,
        normalize_roles_fn=normalize_roles,
        parse_roles_fn=_parse_roles,
        review_policy_service_cls=ReviewPolicyService,
        ensure_review_management_access_fn=_ensure_review_management_access,
        safe_insert_invite_policy_audit_fn=_safe_insert_invite_policy_audit,
        notification_service_cls=NotificationService,
        email_service_obj=email_service,
        create_magic_link_jwt_fn=create_magic_link_jwt,
        is_foreign_key_user_error_fn=_is_foreign_key_user_error,
        is_missing_relation_error_fn=_is_missing_relation_error,
    )


def _get_magic_link_from_cookie(magic_token: str | None) -> str:
    if not magic_token:
        raise HTTPException(status_code=401, detail="Missing magic link session")
    return magic_token


async def _require_magic_link_scope(
    *,
    assignment_id: UUID,
    magic_token: str | None,
) -> MagicLinkPayload:
    token = _get_magic_link_from_cookie(magic_token)
    payload = decode_magic_link_jwt(token)
    if str(payload.assignment_id) != str(assignment_id):
        raise HTTPException(status_code=401, detail="Magic link scope mismatch")

    try:
        a = (
            supabase_admin.table("review_assignments")
            .select("id, status, manuscript_id, reviewer_id, due_at")
            .eq("id", str(assignment_id))
            .single()
            .execute()
        )
        assignment = getattr(a, "data", None) or {}
    except Exception:
        assignment = {}

    if not assignment:
        raise HTTPException(status_code=401, detail="Assignment not found")
    status = str(assignment.get("status") or "").lower()
    if status == "cancelled":
        raise HTTPException(status_code=401, detail="Invitation revoked")
    if str(assignment.get("manuscript_id")) != str(payload.manuscript_id):
        raise HTTPException(status_code=401, detail="Magic link scope mismatch")
    if str(assignment.get("reviewer_id")) != str(payload.reviewer_id):
        raise HTTPException(status_code=401, detail="Magic link scope mismatch")

    return payload


@router.get("/reviews/magic/assignments/{assignment_id}")
async def get_review_assignment_via_magic_link(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    """
    Magic Link 审稿任务入口（Feature 039）

    中文注释:
    - 通过 httpOnly cookie `sf_review_magic`（JWT）鉴权。
    - 严格限制仅可访问 token 指向的 assignment。
    """

    return await get_review_assignment_via_magic_link_impl(
        assignment_id=assignment_id,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        supabase_admin_client=supabase_admin,
    )


@router.post("/reviewer/assignments/{assignment_id}/session")
async def establish_reviewer_workspace_session(
    assignment_id: UUID,
    response: Response,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    登录态 Reviewer 会话桥接（Dashboard -> Reviewer Workspace v2）。

    中文注释:
    - 内部登录 reviewer 不走邮件链接时，也需要一个 assignment-scoped 的 `sf_review_magic` cookie。
    - 这里严格校验 assignment 属于当前用户后，签发同 scope JWT 并写入 httpOnly cookie。
    """
    return await establish_reviewer_workspace_session_impl(
        assignment_id=assignment_id,
        response=response,
        current_user=current_user,
        supabase_admin_client=supabase_admin,
        create_magic_link_jwt_fn=create_magic_link_jwt,
    )


@router.get("/reviews/magic/assignments/{assignment_id}/pdf-signed")
async def get_review_assignment_pdf_signed_via_magic_link(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await get_review_assignment_pdf_signed_via_magic_link_impl(
        assignment_id=assignment_id,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        supabase_admin_client=supabase_admin,
        get_signed_url_for_manuscripts_bucket_fn=_get_signed_url_for_manuscripts_bucket,
    )


@router.get("/reviews/magic/assignments/{assignment_id}/attachment-signed")
async def get_review_attachment_signed_via_magic_link(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    return await get_review_attachment_signed_via_magic_link_impl(
        assignment_id=assignment_id,
        magic_token=sf_review_magic,
        require_magic_link_scope_fn=_require_magic_link_scope,
        supabase_admin_client=supabase_admin,
        get_signed_url_for_review_attachments_bucket_fn=_get_signed_url_for_review_attachments_bucket,
    )


@router.post("/reviews/magic/assignments/{assignment_id}/submit")
async def submit_review_via_magic_link(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
    comments_for_author: str | None = Form(None),
    content: str | None = Form(None),
    score: int = Form(...),
    confidential_comments_to_editor: str | None = Form(None),
    attachment: UploadFile | None = File(None),
):
    payload = await _require_magic_link_scope(assignment_id=assignment_id, magic_token=sf_review_magic)
    return await submit_review_via_magic_link_impl(
        assignment_id=assignment_id,
        payload=payload,
        comments_for_author=comments_for_author,
        content=content,
        score=score,
        confidential_comments_to_editor=confidential_comments_to_editor,
        attachment=attachment,
        supabase_admin_client=supabase_admin,
        ensure_review_attachments_bucket_exists_fn=_ensure_review_attachments_bucket_exists,
    )


@router.delete("/reviews/assign/{assignment_id}")
async def unassign_reviewer(
    assignment_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "assistant_editor", "admin"])),
):
    """
    撤销审稿指派
    """
    return await unassign_reviewer_impl(
        assignment_id=assignment_id,
        current_user=current_user,
        profile=profile,
        supabase_admin_client=supabase_admin,
        ensure_review_management_access_fn=_ensure_review_management_access,
        normalize_roles_fn=normalize_roles,
        parse_roles_fn=_parse_roles,
    )


@router.get("/reviews/assignments/{manuscript_id}")
async def get_manuscript_assignments(
    manuscript_id: UUID,
    round_number: int | None = None,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "assistant_editor", "admin"])),
):
    """
    获取某篇稿件的审稿指派列表
    """
    return await get_manuscript_assignments_impl(
        manuscript_id=manuscript_id,
        round_number=round_number,
        current_user=current_user,
        profile=profile,
        supabase_admin_client=supabase_admin,
        ensure_review_management_access_fn=_ensure_review_management_access,
        normalize_roles_fn=normalize_roles,
        parse_roles_fn=_parse_roles,
    )


# === 2. 获取我的审稿任务 (Reviewer Task) ===
@router.get("/reviews/my-tasks")
async def get_my_review_tasks(
    user_id: UUID,
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["reviewer", "admin"])),
):
    """
    审稿人获取自己名下的任务
    """
    if str(user_id) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Cannot access other user's tasks")
    try:
        res = (
            supabase.table("review_assignments")
            .select("*, manuscripts(title, abstract, file_path)")
            .eq("reviewer_id", str(user_id))
            .eq("status", "pending")
            .execute()
        )
        return {"success": True, "data": res.data}
    except APIError as e:
        # 中文注释:
        # 1) 云端 Supabase 可能还没创建 review_assignments 表（schema cache 里会 404/PGRST205）。
        # 2) Reviewer Tab 属于“可选能力”，不要因为缺表把整个 Dashboard 打崩，降级为空列表。
        print(f"Review tasks query failed (fallback to empty): {e}")
        return {
            "success": True,
            "data": [],
            "message": "review_assignments table not found",
        }


# === 3. 提交多维度评价 (Submission) ===
@router.post("/reviews/submit")
async def submit_review(
    assignment_id: UUID = Body(..., embed=True),
    scores: Dict[str, int] = Body(..., embed=True),  # {novelty: 5, rigor: 4, ...}
    # Feature 022 completion: comments_for_author 必填；兼容旧字段 comments
    comments_for_author: str | None = Body(None, embed=True),
    comments: str | None = Body(None, embed=True),
    confidential_comments_to_editor: str | None = Body(None, embed=True),
    attachment_path: str | None = Body(None, embed=True),
):
    """
    提交结构化评审意见
    """
    return await submit_review_impl(
        assignment_id=assignment_id,
        scores=scores,
        comments_for_author=comments_for_author,
        comments=comments,
        confidential_comments_to_editor=confidential_comments_to_editor,
        attachment_path=attachment_path,
        supabase_client=supabase,
        supabase_admin_client=supabase_admin,
    )


@router.post("/reviews/assignments/{assignment_id}/attachment")
async def upload_review_attachment(
    assignment_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["reviewer", "admin"])),
    attachment: UploadFile = File(...),
):
    """
    Reviewer 上传机密附件（Annotated PDF）

    中文注释:
    - 文件存储在 review-attachments 私有桶
    - 仅 reviewer 本人（或 admin）可上传
    - 返回 attachment_path，前端在提交 review 时写入 review_reports.attachment_path
    """
    if attachment is None:
        raise HTTPException(status_code=400, detail="attachment is required")

    safe_name = (attachment.filename or "attachment").replace("/", "_")
    is_pdf = (attachment.content_type == "application/pdf") or safe_name.lower().endswith(".pdf")
    if not is_pdf:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        assignment_res = (
            supabase_admin.table("review_assignments")
            .select("id, reviewer_id")
            .eq("id", str(assignment_id))
            .single()
            .execute()
        )
        assignment = getattr(assignment_res, "data", None) or {}
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        is_admin = "admin" in (profile.get("roles") or [])
        if not is_admin and str(assignment.get("reviewer_id") or "") != str(current_user.get("id") or ""):
            raise HTTPException(status_code=403, detail="Forbidden")

        file_bytes = await attachment.read()
        path = f"review_assignments/{assignment_id}/{safe_name}"
        try:
            _ensure_review_attachments_bucket_exists()
            supabase_admin.storage.from_("review-attachments").upload(
                path,
                file_bytes,
                {"content-type": attachment.content_type or "application/pdf"},
            )
        except Exception as e:
            print(f"[Review Attachment] upload failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload attachment")

        return {"success": True, "data": {"attachment_path": path}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload review attachment failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload attachment")


def _is_admin_email(email: Optional[str]) -> bool:
    if not email:
        return False
    admins = [e.strip().lower() for e in (os.environ.get("ADMIN_EMAILS") or "").split(",") if e.strip()]
    return email.strip().lower() in set(admins)


@router.get("/reviews/token/{token}")
async def get_review_by_token(token: str):
    """
    免登录审稿入口：通过 token 获取审稿任务与稿件信息

    中文注释:
    - 这是 Reviewer 无需登录的落地页能力；必须严格校验 token 有效性与过期时间。
    """
    return await get_review_by_token_impl(
        token=token,
        supabase_admin_client=supabase_admin,
    )


@router.get("/reviews/token/{token}/pdf-signed")
async def get_review_pdf_signed_by_token(token: str):
    """
    免登录审稿：返回该 token 对应稿件 PDF 的 signed URL。

    中文注释:
    - 前端 iframe 无法携带 Authorization header，因此必须由后端生成 signed URL。
    - token 本身是访问凭证，必须严格校验有效性与过期时间。
    """
    return await get_review_pdf_signed_by_token_impl(
        token=token,
        supabase_admin_client=supabase_admin,
        get_signed_url_for_manuscripts_bucket_fn=_get_signed_url_for_manuscripts_bucket,
    )


@router.post("/reviews/token/{token}/submit")
async def submit_review_by_token(
    token: str,
    # Feature 022 completion: comments_for_author 必填；兼容旧字段 content
    comments_for_author: str | None = Form(None),
    content: str | None = Form(None),
    score: int = Form(...),
    confidential_comments_to_editor: str | None = Form(None),
    attachment: UploadFile | None = File(None),
):
    """
    免登录审稿提交：支持双通道评论 + 机密附件
    """
    return await submit_review_by_token_impl(
        token=token,
        comments_for_author=comments_for_author,
        content=content,
        score=score,
        confidential_comments_to_editor=confidential_comments_to_editor,
        attachment=attachment,
        supabase_admin_client=supabase_admin,
        ensure_review_attachments_bucket_exists_fn=_ensure_review_attachments_bucket_exists,
    )


@router.get("/reviews/feedback/{manuscript_id}")
async def get_review_feedback_for_manuscript(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    获取某稿件的审稿反馈（按身份过滤机密字段）

    中文注释:
    - Author 只能看到公开字段（content/score）
    - Editor/Admin 可以看到机密字段（confidential_comments_to_editor/attachment_path）
    """
    return await get_review_feedback_for_manuscript_impl(
        manuscript_id=manuscript_id,
        current_user=current_user,
        supabase_admin_client=supabase_admin,
        is_admin_email_fn=_is_admin_email,
    )


@router.get("/reviews/token/{token}/attachment-signed")
async def get_review_attachment_signed_by_token(token: str):
    """
    免登录审稿：返回该 token 对应 review attachment 的 signed URL（如果存在）。
    """
    return await get_review_attachment_signed_by_token_impl(
        token=token,
        supabase_admin_client=supabase_admin,
        get_signed_url_for_review_attachments_bucket_fn=_get_signed_url_for_review_attachments_bucket,
    )


@router.get("/reviews/reports/{review_report_id}/attachment-signed")
async def get_review_attachment_signed(
    review_report_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["reviewer", "managing_editor", "admin"])),
):
    """
    登录态：Reviewer/Editor/Admin 下载机密附件（Author 禁止）。
    """
    return await get_review_attachment_signed_impl(
        review_report_id=review_report_id,
        current_user=current_user,
        profile=profile,
        supabase_admin_client=supabase_admin,
        get_signed_url_for_review_attachments_bucket_fn=_get_signed_url_for_review_attachments_bucket,
    )
