from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks, UploadFile, File, Form
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.role_matrix import normalize_roles
from app.services.notification_service import NotificationService
from uuid import UUID
from typing import Any, Dict, Optional
from postgrest.exceptions import APIError
from datetime import datetime, timedelta, timezone
import os
from urllib.parse import quote

from fastapi import Cookie

from app.core.security import create_magic_link_jwt, decode_magic_link_jwt
from app.schemas.review import InviteAcceptPayload, InviteDeclinePayload, ReviewSubmission
from app.schemas.token import MagicLinkPayload
from app.core.mail import email_service
from app.services.reviewer_service import ReviewPolicyService, ReviewerInviteService, ReviewerWorkspaceService

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
    """
    判断 Supabase/PostgREST 返回的“表不存在/Schema cache 未更新”等错误。

    中文注释:
    - 早期开发阶段可能还没建表；但不要对所有异常都“模拟成功”，否则会掩盖外键/权限等真实问题。
    """
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
    payload = await _require_magic_link_scope(assignment_id=assignment_id, magic_token=sf_review_magic)
    try:
        data = ReviewerWorkspaceService().get_workspace_data(
            assignment_id=assignment_id,
            reviewer_id=payload.reviewer_id,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load workspace: {e}")
    return {"success": True, "data": data.model_dump()}


@router.get("/reviewer/assignments/{assignment_id}/invite")
async def get_reviewer_invite_data(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    payload = await _require_magic_link_scope(assignment_id=assignment_id, magic_token=sf_review_magic)
    try:
        data = ReviewerInviteService().get_invite_view(
            assignment_id=assignment_id,
            reviewer_id=payload.reviewer_id,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load invite view: {e}")
    return {"success": True, "data": data.model_dump()}


@router.post("/reviewer/assignments/{assignment_id}/accept")
async def accept_reviewer_invitation(
    assignment_id: UUID,
    payload: InviteAcceptPayload,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    token_payload = await _require_magic_link_scope(assignment_id=assignment_id, magic_token=sf_review_magic)
    try:
        data = ReviewerInviteService().accept_invitation(
            assignment_id=assignment_id,
            reviewer_id=token_payload.reviewer_id,
            payload=payload,
        )
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to accept invitation: {e}")


@router.post("/reviewer/assignments/{assignment_id}/decline")
async def decline_reviewer_invitation(
    assignment_id: UUID,
    payload: InviteDeclinePayload,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    token_payload = await _require_magic_link_scope(assignment_id=assignment_id, magic_token=sf_review_magic)
    try:
        data = ReviewerInviteService().decline_invitation(
            assignment_id=assignment_id,
            reviewer_id=token_payload.reviewer_id,
            payload=payload,
        )
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to decline invitation: {e}")


@router.post("/reviewer/assignments/{assignment_id}/attachments")
async def upload_reviewer_workspace_attachment(
    assignment_id: UUID,
    file: UploadFile = File(...),
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    payload = await _require_magic_link_scope(assignment_id=assignment_id, magic_token=sf_review_magic)
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Attachment cannot be empty")
    try:
        path = ReviewerWorkspaceService().upload_attachment(
            assignment_id=assignment_id,
            reviewer_id=payload.reviewer_id,
            filename=file.filename or "attachment",
            content=raw,
            content_type=file.content_type,
        )
        signed_url = _get_signed_url_for_review_attachments_bucket(path, expires_in=60 * 5)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload attachment: {e}")
    return {"success": True, "data": {"path": path, "url": signed_url}}


@router.post("/reviewer/assignments/{assignment_id}/submit")
async def submit_reviewer_workspace_review(
    assignment_id: UUID,
    body: ReviewSubmission,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    payload = await _require_magic_link_scope(assignment_id=assignment_id, magic_token=sf_review_magic)
    try:
        result = ReviewerWorkspaceService().submit_review(
            assignment_id=assignment_id,
            reviewer_id=payload.reviewer_id,
            payload=body,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit review: {e}")
    return {"success": True, "data": {"status": result.get("status", "completed"), "redirect_to": "/review/thank-you"}}


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
    requester_roles = set(normalize_roles(_parse_roles(profile)))
    policy_service = ReviewPolicyService()
    reviewer_id_str = str(reviewer_id)
    manuscript_id_str = str(manuscript_id)

    # 读取稿件基础信息（含 journal_id 供冷却期策略判断）
    ms_res = (
        supabase.table("manuscripts")
        .select("id, author_id, title, version, status, owner_id, file_path, journal_id, assistant_editor_id")
        .eq("id", manuscript_id_str)
        .single()
        .execute()
    )
    manuscript = ms_res.data or {}
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")
    _ensure_review_management_access(
        manuscript=manuscript,
        user_id=str(current_user.get("id") or ""),
        roles=requester_roles,
    )

    if ms_res.data and str(ms_res.data["author_id"]) == str(reviewer_id):
        raise HTTPException(status_code=400, detail="作者不能评审自己的稿件")

    # 体验/数据兜底：没有 PDF 的稿件不允许分配审稿人，否则 reviewer 侧无法预览全文
    file_path = manuscript.get("file_path")
    if not file_path:
        raise HTTPException(
            status_code=400,
            detail="该稿件缺少 PDF（file_path 为空），无法分配审稿人。请先在投稿/修订流程上传 PDF。",
        )

    # Feature 023: 初审阶段必须绑定 Internal Owner（KPI 归属人）
    # 中文注释: 分配审稿人会把稿件推进到 under_review，因此这里强制要求 owner_id 已设置。
    owner_raw = manuscript.get("owner_id")
    if not owner_raw:
        # 体验优化：若 Editor 尚未手动绑定，则默认绑定为当前 Editor（仍满足“初审阶段完成绑定”的业务要求）
        try:
            supabase_admin.table("manuscripts").update({"owner_id": str(current_user["id"])}).eq(
                "id", manuscript_id_str
            ).execute()
            owner_raw = str(current_user["id"])
        except Exception as e:
            print(f"[OwnerBinding] auto-bind owner_id failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to bind Internal Owner")

    current_version = manuscript.get("version", 1) if manuscript else 1

    try:
        # 幂等保护：避免同一审稿人被重复指派（UI 可能因“已指派列表”加载失败而重复提交）
        existing = (
            supabase_admin.table("review_assignments")
            .select("id, status, due_at, reviewer_id, round_number")
            .eq("manuscript_id", manuscript_id_str)
            .eq("reviewer_id", reviewer_id_str)
            .eq("round_number", current_version)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if getattr(existing, "data", None):
            # 中文注释: 返回现有 assignment，前端可直接刷新展示。
            return {
                "success": True,
                "data": existing.data[0],
                "policy": policy_service.evaluate_candidates(manuscript=manuscript, reviewer_ids=[reviewer_id_str]).get(
                    reviewer_id_str
                )
                or {},
                "message": "Reviewer already assigned",
            }

        policy = policy_service.evaluate_candidates(manuscript=manuscript, reviewer_ids=[reviewer_id_str]).get(
            reviewer_id_str
        ) or {
            "can_assign": True,
            "allow_override": False,
            "cooldown_active": False,
            "conflict": False,
            "overdue_risk": False,
            "overdue_open_count": 0,
            "hits": [],
        }
        if policy.get("conflict"):
            raise HTTPException(status_code=400, detail="Invitation blocked: conflict of interest")
        if policy.get("cooldown_active"):
            if not override_cooldown:
                cooldown_until = str(policy.get("cooldown_until") or "")
                msg = (
                    f"Invitation blocked by cooldown policy ({policy_service.cooldown_days()} days in same journal)."
                    f"{f' Cooldown until {cooldown_until}.' if cooldown_until else ''}"
                )
                raise HTTPException(status_code=409, detail=msg)
            allowed_override_roles = {r.lower() for r in policy_service.cooldown_override_roles()}
            if not requester_roles.intersection(allowed_override_roles):
                raise HTTPException(status_code=403, detail="Only high-privilege roles can override cooldown policy")
            reason_clean = str(override_reason or "").strip()
            if not reason_clean:
                raise HTTPException(status_code=422, detail="override_reason is required when override_cooldown=true")
        elif override_cooldown:
            raise HTTPException(status_code=400, detail="override_cooldown=true is only valid when cooldown is active")

        # 默认邀请截止时间：+10 天（窗口可配置）
        _min_days, _max_days, default_days = policy_service.due_window_days()
        due_at = (datetime.now(timezone.utc) + timedelta(days=default_days)).isoformat()
        invited_at = datetime.now(timezone.utc).isoformat()
        insert_payload = {
            "manuscript_id": manuscript_id_str,
            "reviewer_id": reviewer_id_str,
            "status": "pending",
            "due_at": due_at,
            "invited_at": invited_at,
            "round_number": current_version,
        }
        try:
            res = (
                # 中文注释: 使用 service_role 写入，避免云端 RLS/权限导致“写入成功但读取不到”的不一致体验
                supabase_admin.table("review_assignments")
                .insert(insert_payload)
                .execute()
            )
        except Exception as insert_err:
            # 兼容未迁移 037 的云端：移除 invited_at 再试一次
            if "invited_at" in str(insert_err).lower() and "column" in str(insert_err).lower():
                insert_payload.pop("invited_at", None)
                res = (
                    supabase_admin.table("review_assignments")
                    .insert(insert_payload)
                    .execute()
                )
            else:
                raise
        # 更新稿件状态为评审中
        supabase_admin.table("manuscripts").update({"status": "under_review"}).eq(
            "id", manuscript_id_str
        ).execute()

        if override_cooldown:
            _safe_insert_invite_policy_audit(
                manuscript_id=manuscript_id_str,
                from_status=str(manuscript.get("status") or ""),
                to_status="under_review",
                changed_by=str(current_user.get("id") or ""),
                comment="reviewer_invite_cooldown_override",
                payload={
                    "action": "reviewer_invite_cooldown_override",
                    "reviewer_id": reviewer_id_str,
                    "manuscript_id": manuscript_id_str,
                    "override_reason": str(override_reason or "").strip(),
                    "cooldown_days": policy_service.cooldown_days(),
                    "policy_hits": policy.get("hits") or [],
                },
            )

        # === 通知中心 (Feature 011) ===
        # 站内信：审稿人收到邀请提醒
        manuscript_title = manuscript.get("title") or "Manuscript"
        NotificationService().create_notification(
            user_id=reviewer_id_str,
            manuscript_id=manuscript_id_str,
            type="review_invite",
            title="Review Invitation",
            content=f"You have been invited to review '{manuscript_title}'.",
        )

        # 邮件：审稿邀请（含免登录 Token 链接）
        try:
            profile_res = (
                supabase_admin.table("user_profiles")
                .select("email,full_name")
                .eq("id", reviewer_id_str)
                .single()
                .execute()
            )
            reviewer_profile = getattr(profile_res, "data", None) or {}
            reviewer_email = reviewer_profile.get("email")
            reviewer_name = reviewer_profile.get("full_name") or "Reviewer"
        except Exception:
            reviewer_email = None
            reviewer_name = "Reviewer"

        journal_title = "ScholarFlow Journal"
        journal_id = str(manuscript.get("journal_id") or "").strip()
        if journal_id:
            try:
                jr = (
                    supabase_admin.table("journals")
                    .select("title")
                    .eq("id", journal_id)
                    .single()
                    .execute()
                )
                journal_title = str((getattr(jr, "data", None) or {}).get("title") or journal_title)
            except Exception:
                pass

        if reviewer_email:
            # Feature 039: Magic Link (JWT, 14-day default)
            assignment_id = None
            try:
                assignment_id = (res.data or [])[0].get("id") if isinstance(res.data, list) else None
            except Exception:
                assignment_id = None
            if assignment_id:
                try:
                    expires_days = int((os.environ.get("MAGIC_LINK_EXPIRES_DAYS") or "14").strip())
                except ValueError:
                    expires_days = 14
                try:
                    assignment_uuid = UUID(str(assignment_id))
                except Exception:
                    assignment_uuid = None
                token = (
                    create_magic_link_jwt(
                        reviewer_id=reviewer_id,
                        manuscript_id=manuscript_id,
                        assignment_id=assignment_uuid,
                        expires_in_days=expires_days,
                    )
                    if assignment_uuid
                    else None
                )
            else:
                token = None

            frontend_base_url = (os.environ.get("FRONTEND_BASE_URL") or "http://localhost:3000").rstrip("/")
            review_url = (
                f"{frontend_base_url}/review/invite?token={quote(str(token))}"
                if token
                else f"{frontend_base_url}/dashboard"
            )
            
            background_tasks.add_task(
                email_service.send_email_background,
                to_email=reviewer_email,
                subject="Invitation to Review",
                template_name="invitation.html",
                context={
                    "review_url": review_url,
                    "reviewer_name": reviewer_name,
                    "manuscript_title": manuscript_title,
                    "manuscript_id": str(manuscript_id),
                    "journal_title": journal_title,
                    "due_at": due_at,
                    "due_date": str(due_at).split("T")[0],
                },
            )

        row = (getattr(res, "data", None) or [{}])[0]
        return {"success": True, "data": row, "policy": policy}
    except HTTPException:
        raise
    except APIError as e:
        # 中文注释:
        # - reviewer_id 外键指向 auth.users(id)，如果前端列表里混入了“仅 user_profiles 的 mock reviewer”，这里会触发 23503。
        if _is_foreign_key_user_error(e, constraint="review_assignments_reviewer_id_fkey"):
            raise HTTPException(
                status_code=400,
                detail=(
                    "该审稿人账号不存在于 Supabase Auth（可能是 mock user_profiles）。"
                    "请用「Invite New」创建真实账号，或运行 scripts/seed_mock_reviewers_auth.py 生成可指派 reviewer。"
                ),
            )
        if _is_missing_relation_error(e, relation="review_assignments"):
            raise HTTPException(
                status_code=500,
                detail="review_assignments 表不存在或 Schema cache 未更新（请先在云端 Supabase 创建/迁移该表）。",
            )
        raise HTTPException(status_code=500, detail=f"Failed to assign reviewer: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign reviewer: {e}")


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

    payload = await _require_magic_link_scope(assignment_id=assignment_id, magic_token=sf_review_magic)

    ms_resp = (
        supabase_admin.table("manuscripts")
        .select("id,title,abstract,file_path,status")
        .eq("id", str(payload.manuscript_id))
        .single()
        .execute()
    )
    ms = getattr(ms_resp, "data", None) or {}

    latest_revision = None
    try:
        rev_resp = (
            supabase_admin.table("revisions")
            .select("id, round_number, decision_type, editor_comment, response_letter, status, submitted_at, created_at")
            .eq("manuscript_id", str(payload.manuscript_id))
            .order("round_number", desc=True)
            .limit(1)
            .execute()
        )
        revs = getattr(rev_resp, "data", None) or []
        latest_revision = revs[0] if revs else None
    except Exception:
        latest_revision = None

    # review_reports 用于存储双通道意见与机密附件（可能尚未创建）
    review_report = None
    try:
        rr = (
            supabase_admin.table("review_reports")
            .select("id, manuscript_id, reviewer_id, status, score, comments_for_author, confidential_comments_to_editor, attachment_path")
            .eq("manuscript_id", str(payload.manuscript_id))
            .eq("reviewer_id", str(payload.reviewer_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = getattr(rr, "data", None) or []
        review_report = rows[0] if rows else None
    except Exception:
        review_report = None

    return {
        "success": True,
        "data": {
            "assignment_id": str(payload.assignment_id),
            "reviewer_id": str(payload.reviewer_id),
            "manuscript": ms,
            "review_report": review_report,
            "latest_revision": latest_revision,
        },
    }


@router.get("/reviews/magic/assignments/{assignment_id}/pdf-signed")
async def get_review_assignment_pdf_signed_via_magic_link(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    payload = await _require_magic_link_scope(assignment_id=assignment_id, magic_token=sf_review_magic)

    ms_resp = (
        supabase_admin.table("manuscripts")
        .select("id,file_path")
        .eq("id", str(payload.manuscript_id))
        .single()
        .execute()
    )
    ms = getattr(ms_resp, "data", None) or {}
    file_path = ms.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="Manuscript PDF not found")

    signed_url = _get_signed_url_for_manuscripts_bucket(str(file_path))
    return {"success": True, "data": {"signed_url": signed_url}}


@router.get("/reviews/magic/assignments/{assignment_id}/attachment-signed")
async def get_review_attachment_signed_via_magic_link(
    assignment_id: UUID,
    sf_review_magic: str | None = Cookie(default=None, alias="sf_review_magic"),
):
    payload = await _require_magic_link_scope(assignment_id=assignment_id, magic_token=sf_review_magic)

    try:
        rr = (
            supabase_admin.table("review_reports")
            .select("id, attachment_path")
            .eq("manuscript_id", str(payload.manuscript_id))
            .eq("reviewer_id", str(payload.reviewer_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = getattr(rr, "data", None) or []
        row = rows[0] if rows else None
    except Exception:
        row = None

    attachment_path = (row or {}).get("attachment_path") if row else None
    if not attachment_path:
        return {"success": True, "data": {"signed_url": None}}

    signed_url = _get_signed_url_for_review_attachments_bucket(str(attachment_path))
    return {"success": True, "data": {"signed_url": signed_url}}


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

    public_comments = (comments_for_author or content or "").strip()
    if not public_comments:
        raise HTTPException(status_code=400, detail="comments_for_author is required")
    if score < 1 or score > 5:
        raise HTTPException(status_code=400, detail="score must be 1..5")

    attachment_path = None
    if attachment is not None:
        file_bytes = await attachment.read()
        safe_name = (attachment.filename or "attachment").replace("/", "_")
        # 中文注释: 机密附件仅供编辑查看；存储路径不暴露给作者
        attachment_path = f"review_reports/{payload.assignment_id}/{safe_name}"
        try:
            _ensure_review_attachments_bucket_exists()
            supabase_admin.storage.from_("review-attachments").upload(
                attachment_path,
                file_bytes,
                {"content-type": attachment.content_type or "application/octet-stream"},
            )
        except Exception as e:
            print(f"[Review Attachment] upload failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload attachment")

    # 1) 写 review_reports（双通道评论）
    rr_payload = {
        "manuscript_id": str(payload.manuscript_id),
        "reviewer_id": str(payload.reviewer_id),
        "status": "completed",
        "comments_for_author": public_comments,
        "content": public_comments,  # 兼容旧字段
        "score": score,
        "confidential_comments_to_editor": confidential_comments_to_editor,
        "attachment_path": attachment_path,
    }
    try:
        existing = (
            supabase_admin.table("review_reports")
            .select("id")
            .eq("manuscript_id", str(payload.manuscript_id))
            .eq("reviewer_id", str(payload.reviewer_id))
            .limit(1)
            .execute()
        )
        rows = getattr(existing, "data", None) or []
        if rows:
            supabase_admin.table("review_reports").update(rr_payload).eq("id", rows[0]["id"]).execute()
        else:
            supabase_admin.table("review_reports").insert(
                {
                    **rr_payload,
                    "token": None,
                    "expiry_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                }
            ).execute()
    except Exception as e:
        print(f"[Reviews] upsert review_reports failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit review")

    # 2) 同步 review_assignments 状态
    try:
        supabase_admin.table("review_assignments").update(
            {
                "status": "completed",
                "comments": public_comments,
                "scores": {"overall": score},
            }
        ).eq("id", str(assignment_id)).execute()
    except Exception as e:
        print(f"[Reviews] update assignment failed (ignored): {e}")

    # 3) 若全部评审完成，推动稿件进入待终审状态（沿用既有逻辑）
    try:
        pending = (
            supabase_admin.table("review_assignments")
            .select("id")
            .eq("manuscript_id", str(payload.manuscript_id))
            .eq("status", "pending")
            .execute()
        )
        if not (getattr(pending, "data", None) or []):
            supabase_admin.table("manuscripts").update({"status": "pending_decision"}).eq(
                "id", str(payload.manuscript_id)
            ).execute()
    except Exception:
        pass

    return {"success": True, "data": {"assignment_id": str(assignment_id)}}


@router.delete("/reviews/assign/{assignment_id}")
async def unassign_reviewer(
    assignment_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["managing_editor", "assistant_editor", "admin"])),
):
    """
    撤销审稿指派
    """
    try:
        # 1. 获取 manuscript_id 以便后续状态检查
        assign_res = (
            supabase_admin.table("review_assignments")
            .select("manuscript_id, reviewer_id, round_number")
            .eq("id", str(assignment_id))
            .single()
            .execute()
        )
        if not assign_res.data:
            raise HTTPException(status_code=404, detail="Assignment not found")

        manuscript_id = assign_res.data["manuscript_id"]
        reviewer_id = assign_res.data["reviewer_id"]
        round_number = assign_res.data.get("round_number")
        manuscript_res = (
            supabase_admin.table("manuscripts")
            .select("id,journal_id,assistant_editor_id")
            .eq("id", str(manuscript_id))
            .single()
            .execute()
        )
        manuscript = getattr(manuscript_res, "data", None) or {}
        _ensure_review_management_access(
            manuscript=manuscript,
            user_id=str(current_user.get("id") or ""),
            roles=set(normalize_roles(_parse_roles(profile))),
        )

        # 2. 删除指派
        # 中文注释: 同一 reviewer 可能被重复指派（历史数据/并发），这里按 reviewer+round 做幂等清理。
        delete_q = (
            supabase_admin.table("review_assignments")
            .delete()
            .eq("manuscript_id", manuscript_id)
            .eq("reviewer_id", reviewer_id)
        )
        if round_number is not None:
            delete_q = delete_q.eq("round_number", round_number)
        delete_q.execute()

        # 3. 尝试删除关联的 review_reports (如果状态是 invited/pending)
        try:
            supabase_admin.table("review_reports").delete().eq(
                "manuscript_id", manuscript_id
            ).eq("reviewer_id", reviewer_id).in_(
                "status", ["invited", "pending"]
            ).execute()
        except Exception:
            pass

        # 4. 检查是否还有其他审稿人
        remaining_res = (
            supabase_admin.table("review_assignments")
            .select("id")
            .eq("manuscript_id", manuscript_id)
            .execute()
        )
        remaining_count = len(remaining_res.data or [])

        # 5. 如果没有审稿人了，回滚稿件状态为 pre_check（进入编辑预检阶段）
        if remaining_count == 0:
            supabase_admin.table("manuscripts").update({"status": "pre_check"}).eq(
                "id", manuscript_id
            ).execute()

        return {"success": True, "message": "Reviewer unassigned"}
    except Exception as e:
        print(f"Unassign failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    try:
        manuscript_res = (
            supabase_admin.table("manuscripts")
            .select("id,journal_id,assistant_editor_id")
            .eq("id", str(manuscript_id))
            .single()
            .execute()
        )
        manuscript = getattr(manuscript_res, "data", None) or {}
        if not manuscript:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        _ensure_review_management_access(
            manuscript=manuscript,
            user_id=str(current_user.get("id") or ""),
            roles=set(normalize_roles(_parse_roles(profile))),
        )

        res = (
            # 使用 service_role 读取，避免 RLS/权限导致编辑端看不到已指派数据
            supabase_admin.table("review_assignments")
            .select(
                "id, status, due_at, reviewer_id, round_number, created_at"
            )
            .eq("manuscript_id", str(manuscript_id))
            .order("created_at", desc=True)
            .execute()
        )
        assignments = res.data or []

        # 中文注释:
        # - UI 里的“Manage/Assign Reviewer”应默认聚焦在“当前轮次”。
        # - 但如果当前轮次尚未创建任何指派（例如 resubmitted 但尚未二审分配），则回退到已有的最新轮次，
        #   这样 Editor 至少能看到上一轮的 reviewer 与完成状态。
        target_round: int | None = None
        if round_number is not None:
            target_round = int(round_number)
        else:
            ms_version: int | None = None
            try:
                ms = (
                    supabase_admin.table("manuscripts")
                    .select("version")
                    .eq("id", str(manuscript_id))
                    .single()
                    .execute()
                )
                ms_version = int((getattr(ms, "data", None) or {}).get("version") or 1)
            except Exception:
                ms_version = None

            if assignments:
                try:
                    max_round = max(int(a.get("round_number") or 1) for a in assignments)
                except Exception:
                    max_round = 1

                if ms_version is not None and any(
                    int(a.get("round_number") or 1) == int(ms_version) for a in assignments
                ):
                    target_round = int(ms_version)
                else:
                    target_round = int(max_round)
            else:
                target_round = ms_version

        if target_round is not None and assignments:
            assignments = [
                a
                for a in assignments
                if int(a.get("round_number") or 1) == int(target_round)
            ]

        # 中文注释:
        # - review_assignments.reviewer_id 外键指向 auth.users(id)，并不指向 public.user_profiles(id)
        # - 因此不能用 PostgREST embed 语法直接 join user_profiles（会报错/返回空）
        # - 这里用两次查询做“应用层 join”，保证 UI 能拿到 reviewer_id 并正确预选
        reviewer_ids = list({a.get("reviewer_id") for a in assignments if a.get("reviewer_id")})
        profiles_by_id: Dict[str, Dict[str, Any]] = {}
        if reviewer_ids:
            try:
                profiles_res = (
                    supabase_admin.table("user_profiles")
                    .select("id, full_name, email")
                    .in_("id", reviewer_ids)
                    .execute()
                )
                for p in (profiles_res.data or []):
                    pid = p.get("id")
                    if pid:
                        profiles_by_id[str(pid)] = p
            except Exception as e:
                # 不阻塞主流程：仍返回 assignments，只是名称/邮箱为空
                print(f"Fetch reviewer profiles failed (fallback to ids only): {e}")

        # 去重：同一个 reviewer 在同一 round 被重复指派时，只返回最新一条（避免 UI 显示 2 个“同一人”）
        seen_keys = set()
        result = []
        for item in assignments:
            rid = str(item.get("reviewer_id") or "")
            rnd = item.get("round_number", 1)
            key = (rid, rnd)
            if not rid or key in seen_keys:
                continue
            seen_keys.add(key)
            profile = profiles_by_id.get(rid, {})
            result.append(
                {
                    "id": item["id"],  # assignment_id
                    "status": item.get("status"),
                    "due_at": item.get("due_at"),
                    "round_number": rnd,
                    "reviewer_id": rid,
                    "reviewer_name": profile.get("full_name") or "Unknown",
                    "reviewer_email": profile.get("email") or "",
                }
            )
        return {"success": True, "data": result}
    except Exception as e:
        print(f"Fetch assignments failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load reviewer assignments")


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
    public_comments = (comments_for_author or comments or "").strip()
    if not public_comments:
        raise HTTPException(status_code=400, detail="comments_for_author is required")

    try:
        # 逻辑: 更新状态并存储分数
        assignment_res = (
            supabase.table("review_assignments")
            .select("manuscript_id, reviewer_id")
            .eq("id", str(assignment_id))
            .single()
            .execute()
        )
        manuscript_id = None
        assignment_data = getattr(assignment_res, "data", None)
        if isinstance(assignment_data, list):
            assignment_data = assignment_data[0] if assignment_data else None
        if assignment_data:
            manuscript_id = assignment_data.get("manuscript_id")
            reviewer_id = assignment_data.get("reviewer_id")
        else:
            reviewer_id = None

        res = (
            supabase.table("review_assignments")
            .update({"status": "completed", "scores": scores, "comments": public_comments})
            .eq("id", str(assignment_id))
            .execute()
        )

        # === Feature 022: Reviewer Privacy（双通道评论落库到 review_reports） ===
        # 中文注释:
        # - review_assignments 用于任务状态机；review_reports 用于对外展示（按角色过滤机密字段）。
        if manuscript_id and reviewer_id:
            overall_score = None
            try:
                vals = list((scores or {}).values())
                overall_score = round(sum(vals) / max(len(vals), 1)) if vals else None
            except Exception:
                overall_score = None

            rr_payload = {
                "manuscript_id": str(manuscript_id),
                "reviewer_id": str(reviewer_id),
                "status": "completed",
                # 新字段（Author 可见）
                "comments_for_author": public_comments,
                # 兼容旧字段：历史页面仍可能读取 content
                "content": public_comments,
                "score": overall_score,
                "confidential_comments_to_editor": confidential_comments_to_editor,
                "attachment_path": attachment_path,
            }
            try:
                existing = (
                    supabase_admin.table("review_reports")
                    .select("id")
                    .eq("manuscript_id", str(manuscript_id))
                    .eq("reviewer_id", str(reviewer_id))
                    .limit(1)
                    .execute()
                )
                existing_rows = getattr(existing, "data", None) or []
                if existing_rows:
                    supabase_admin.table("review_reports").update(rr_payload).eq(
                        "id", existing_rows[0]["id"]
                    ).execute()
                else:
                    supabase_admin.table("review_reports").insert(
                        {
                            **rr_payload,
                            "token": None,
                            "expiry_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                        }
                    ).execute()
            except Exception as e:
                # 中文注释: 不因 review_reports 失败阻塞 review_assignments 主流程
                print(f"[Reviews] upsert review_reports failed (ignored): {e}")

        # 若全部评审完成，推动稿件进入待终审状态
        if manuscript_id:
            try:
                pending = (
                    supabase_admin.table("review_assignments")
                    .select("id")
                    .eq("manuscript_id", str(manuscript_id))
                    .eq("status", "pending")
                    .execute()
                )
                pending_rows = getattr(pending, "data", None) or []
            except Exception:
                pending = (
                    supabase.table("review_assignments")
                    .select("id")
                    .eq("manuscript_id", str(manuscript_id))
                    .eq("status", "pending")
                    .execute()
                )
                pending_rows = getattr(pending, "data", None) or []

            if not pending_rows:
                try:
                    supabase_admin.table("manuscripts").update({"status": "decision"}).eq(
                        "id", str(manuscript_id)
                    ).execute()
                except Exception:
                    supabase.table("manuscripts").update({"status": "decision"}).eq(
                        "id", str(manuscript_id)
                    ).execute()

        return {"success": True, "data": res.data[0] if res.data else {}}
    except APIError as e:
        # 缺表时，给出可读提示，避免 500
        print(f"Review submit failed: {e}")
        return {"success": False, "message": "review_assignments table not found"}


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
    try:
        rr_resp = (
            supabase_admin.table("review_reports")
            .select("id, manuscript_id, reviewer_id, status, expiry_date")
            .eq("token", token)
            .single()
            .execute()
        )
        rr = getattr(rr_resp, "data", None) or {}
        if not rr:
            raise HTTPException(status_code=404, detail="Review token not found")

        expiry = rr.get("expiry_date")
        # expiry_date 可能是字符串
        try:
            expiry_dt = (
                datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                if isinstance(expiry, str)
                else expiry
            )
        except Exception:
            expiry_dt = None
        if expiry_dt and expiry_dt < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Review token expired")

        ms_resp = (
            supabase_admin.table("manuscripts")
            .select("id,title,abstract,file_path,status")
            .eq("id", rr["manuscript_id"])
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}

        # 最新修订信息（用于二审/复审时给 reviewer 展示作者 response letter）
        latest_revision = None
        try:
            rev_resp = (
                supabase_admin.table("revisions")
                .select("id, round_number, decision_type, editor_comment, response_letter, status, submitted_at, created_at")
                .eq("manuscript_id", rr["manuscript_id"])
                .order("round_number", desc=True)
                .limit(1)
                .execute()
            )
            revs = getattr(rev_resp, "data", None) or []
            latest_revision = revs[0] if revs else None
        except Exception:
            latest_revision = None

        return {"success": True, "data": {"review_report": rr, "manuscript": ms, "latest_revision": latest_revision}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get review by token failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch review task")


@router.get("/reviews/token/{token}/pdf-signed")
async def get_review_pdf_signed_by_token(token: str):
    """
    免登录审稿：返回该 token 对应稿件 PDF 的 signed URL。

    中文注释:
    - 前端 iframe 无法携带 Authorization header，因此必须由后端生成 signed URL。
    - token 本身是访问凭证，必须严格校验有效性与过期时间。
    """
    try:
        rr_resp = (
            supabase_admin.table("review_reports")
            .select("id, manuscript_id, reviewer_id, status, expiry_date")
            .eq("token", token)
            .single()
            .execute()
        )
        rr = getattr(rr_resp, "data", None) or {}
        if not rr:
            raise HTTPException(status_code=404, detail="Review token not found")

        expiry = rr.get("expiry_date")
        try:
            expiry_dt = (
                datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                if isinstance(expiry, str)
                else expiry
            )
        except Exception:
            expiry_dt = None
        if expiry_dt and expiry_dt < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Review token expired")

        ms_resp = (
            supabase_admin.table("manuscripts")
            .select("id,file_path")
            .eq("id", rr["manuscript_id"])
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}
        file_path = ms.get("file_path")
        if not file_path:
            raise HTTPException(status_code=404, detail="Manuscript PDF not found")

        signed_url = _get_signed_url_for_manuscripts_bucket(str(file_path))
        return {"success": True, "data": {"signed_url": signed_url}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get review pdf signed url by token failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF preview URL")


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
    public_comments = (comments_for_author or content or "").strip()
    if not public_comments:
        raise HTTPException(status_code=400, detail="comments_for_author is required")
    if score < 1 or score > 5:
        raise HTTPException(status_code=400, detail="score must be 1..5")

    try:
        rr_resp = (
            supabase_admin.table("review_reports")
            .select("id, manuscript_id, reviewer_id, status, expiry_date")
            .eq("token", token)
            .single()
            .execute()
        )
        rr = getattr(rr_resp, "data", None) or {}
        if not rr:
            raise HTTPException(status_code=404, detail="Review token not found")

        expiry = rr.get("expiry_date")
        try:
            expiry_dt = (
                datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                if isinstance(expiry, str)
                else expiry
            )
        except Exception:
            expiry_dt = None
        if expiry_dt and expiry_dt < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Review token expired")

        attachment_path = None
        if attachment is not None:
            file_bytes = await attachment.read()
            # 中文注释: 机密附件仅供编辑查看；存储路径不暴露给作者
            safe_name = (attachment.filename or "attachment").replace("/", "_")
            attachment_path = f"review_reports/{rr['id']}/{safe_name}"
            try:
                _ensure_review_attachments_bucket_exists()
                supabase_admin.storage.from_("review-attachments").upload(
                    attachment_path,
                    file_bytes,
                    {"content-type": attachment.content_type or "application/octet-stream"},
                )
            except Exception as e:
                print(f"[Review Attachment] upload failed: {e}")
                raise HTTPException(status_code=500, detail="Failed to upload attachment")

        update_payload = {
            # 新字段（Author 可见）
            "comments_for_author": public_comments,
            # 兼容旧字段
            "content": public_comments,
            "score": score,
            "status": "completed",
            "confidential_comments_to_editor": confidential_comments_to_editor,
            "attachment_path": attachment_path,
        }
        supabase_admin.table("review_reports").update(update_payload).eq("id", rr["id"]).execute()

        # === 同步到 review_assignments / manuscripts（修复 Editor 状态不同步）===
        # 中文注释:
        # - Editor Pipeline 依赖 review_assignments 的 pending/completed 统计。
        # - 免登录 token 提交如果只更新 review_reports，会导致 Editor 侧看不到变化。
        try:
            ms_version = 1
            try:
                ms_v = (
                    supabase_admin.table("manuscripts")
                    .select("version")
                    .eq("id", rr["manuscript_id"])
                    .single()
                    .execute()
                )
                ms_version = int((getattr(ms_v, "data", None) or {}).get("version") or 1)
            except Exception:
                ms_version = 1

            assignment_rows = []
            try:
                a = (
                    supabase_admin.table("review_assignments")
                    .select("id")
                    .eq("manuscript_id", str(rr["manuscript_id"]))
                    .eq("reviewer_id", str(rr["reviewer_id"]))
                    .eq("round_number", ms_version)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                assignment_rows = getattr(a, "data", None) or []
            except Exception:
                assignment_rows = []

            if not assignment_rows:
                # 兼容旧数据：round_number 可能为空
                try:
                    a2 = (
                        supabase_admin.table("review_assignments")
                        .select("id")
                        .eq("manuscript_id", str(rr["manuscript_id"]))
                        .eq("reviewer_id", str(rr["reviewer_id"]))
                        .order("created_at", desc=True)
                        .limit(1)
                        .execute()
                    )
                    assignment_rows = getattr(a2, "data", None) or []
                except Exception:
                    assignment_rows = []

            if assignment_rows:
                supabase_admin.table("review_assignments").update(
                    {
                        "status": "completed",
                        "comments": public_comments,
                        "scores": {"overall": score},
                    }
                ).eq("id", assignment_rows[0]["id"]).execute()

            pending = (
                supabase_admin.table("review_assignments")
                .select("id")
                .eq("manuscript_id", str(rr["manuscript_id"]))
                .eq("status", "pending")
                .execute()
            )
            if not (getattr(pending, "data", None) or []):
                supabase_admin.table("manuscripts").update({"status": "decision"}).eq(
                    "id", str(rr["manuscript_id"])
                ).execute()
        except Exception as e:
            # 中文注释: 不因同步失败阻塞免登录提交主流程，但要打日志便于排查。
            print(f"[Reviews] token submit sync to assignments/manuscripts failed (ignored): {e}")

        return {"success": True, "data": {"review_report_id": rr["id"]}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Submit review by token failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit review")


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
    try:
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

        is_author = str(ms.get("author_id")) == str(current_user.get("id"))
        is_editor = _is_admin_email(current_user.get("email"))
        if not (is_author or is_editor):
            raise HTTPException(status_code=403, detail="Forbidden")

        rr_resp = (
            supabase_admin.table("review_reports")
            .select("id, manuscript_id, reviewer_id, status, comments_for_author, content, score, confidential_comments_to_editor, attachment_path")
            .eq("manuscript_id", str(manuscript_id))
            .order("created_at", desc=True)
            .execute()
        )
        rows = getattr(rr_resp, "data", None) or []

        if is_author:
            sanitized = []
            for r in rows:
                public_text = r.get("comments_for_author") or r.get("content")
                r2 = {
                    "id": r.get("id"),
                    "manuscript_id": r.get("manuscript_id"),
                    "reviewer_id": r.get("reviewer_id"),
                    "status": r.get("status"),
                    # 兼容：旧页面读取 content
                    "content": public_text,
                    "comments_for_author": public_text,
                    "score": r.get("score"),
                }
                sanitized.append(r2)
            return {"success": True, "data": sanitized}

        # Editor/Admin：返回机密字段，但保证 comments_for_author 有值，避免老数据为空
        for r in rows:
            if not r.get("comments_for_author") and r.get("content"):
                r["comments_for_author"] = r.get("content")
        return {"success": True, "data": rows}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Fetch review feedback failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch review feedback")


@router.get("/reviews/token/{token}/attachment-signed")
async def get_review_attachment_signed_by_token(token: str):
    """
    免登录审稿：返回该 token 对应 review attachment 的 signed URL（如果存在）。
    """
    try:
        rr_resp = (
            supabase_admin.table("review_reports")
            .select("id, attachment_path, expiry_date")
            .eq("token", token)
            .single()
            .execute()
        )
        rr = getattr(rr_resp, "data", None) or {}
        if not rr:
            raise HTTPException(status_code=404, detail="Review token not found")

        expiry = rr.get("expiry_date")
        try:
            expiry_dt = (
                datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                if isinstance(expiry, str)
                else expiry
            )
        except Exception:
            expiry_dt = None
        if expiry_dt and expiry_dt < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Review token expired")

        path = rr.get("attachment_path")
        if not path:
            raise HTTPException(status_code=404, detail="No attachment")

        signed_url = _get_signed_url_for_review_attachments_bucket(str(path))
        return {"success": True, "data": {"signed_url": signed_url}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get review attachment signed url by token failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate attachment URL")


@router.get("/reviews/reports/{review_report_id}/attachment-signed")
async def get_review_attachment_signed(
    review_report_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(["reviewer", "managing_editor", "admin"])),
):
    """
    登录态：Reviewer/Editor/Admin 下载机密附件（Author 禁止）。
    """
    try:
        rr_resp = (
            supabase_admin.table("review_reports")
            .select("id, reviewer_id, attachment_path")
            .eq("id", str(review_report_id))
            .single()
            .execute()
        )
        rr = getattr(rr_resp, "data", None) or {}
        if not rr:
            raise HTTPException(status_code=404, detail="Review report not found")

        roles = set(profile.get("roles") or [])
        is_editor = bool(roles.intersection({"managing_editor", "admin"}))
        if not is_editor and str(rr.get("reviewer_id") or "") != str(current_user.get("id") or ""):
            raise HTTPException(status_code=403, detail="Forbidden")

        path = rr.get("attachment_path")
        if not path:
            raise HTTPException(status_code=404, detail="No attachment")

        signed_url = _get_signed_url_for_review_attachments_bucket(str(path))
        return {"success": True, "data": {"signed_url": signed_url}}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get review attachment signed url failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate attachment URL")
