from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter, time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.editor_common import (
    get_signed_url as _get_signed_url,
    is_missing_table_error as _is_missing_table_error,
    require_action_or_403 as _require_action_or_403,
)
from app.core.auth_utils import get_current_user
from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.role_matrix import normalize_roles
from app.core.roles import require_any_role
from app.lib.api_client import supabase_admin
from app.models.internal_task import InternalTaskStatus
from app.models.manuscript import ManuscriptStatus, normalize_status

# 与 editor.py 保持一致：这些角色可进入 Editor Command Center。
EDITOR_SCOPE_COMPAT_ROLES = [
    "admin",
    "managing_editor",
    "assistant_editor",
    "production_editor",
    "editor_in_chief",
]

router = APIRouter(tags=["Editor Command Center"])
_AUTH_PROFILE_FALLBACK_TTL_SEC = 60 * 5
_auth_profile_fallback_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}


def _get_cached_auth_profile(uid: str) -> tuple[bool, dict[str, Any] | None]:
    now = time()
    cached = _auth_profile_fallback_cache.get(uid)
    if not cached:
        return False, None
    expires_at, value = cached
    if expires_at <= now:
        _auth_profile_fallback_cache.pop(uid, None)
        return False, None
    return True, value


def _set_cached_auth_profile(uid: str, profile: dict[str, Any] | None) -> None:
    _auth_profile_fallback_cache[uid] = (time() + _AUTH_PROFILE_FALLBACK_TTL_SEC, profile)


def _load_manuscript_or_404(manuscript_id: str) -> dict[str, Any]:
    try:
        resp = (
            supabase_admin.table("manuscripts")
            .select("*, journals(title,slug)")
            .eq("id", manuscript_id)
            .single()
            .execute()
        )
        ms = getattr(resp, "data", None) or None
    except Exception as e:
        raise HTTPException(status_code=404, detail="Manuscript not found") from e
    if not ms:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    normalized_status = normalize_status(str(ms.get("status") or ""))
    if normalized_status:
        ms["status"] = normalized_status
    return ms


def _authorize_manuscript_detail_access(
    *,
    manuscript_id: str,
    manuscript: dict[str, Any],
    current_user: dict[str, Any],
    profile: dict[str, Any],
) -> None:
    # RBAC / Journal Scope:
    # - admin: always allow
    # - assistant_editor: allow if assigned to this manuscript (even if user also has managing_editor role but missing scope)
    # - managing_editor/editor_in_chief: enforce journal_role_scopes
    # - production_editor: allow if assigned to an active production cycle (layout_editor_id matches)
    viewer_user_id = str(current_user.get("id") or "").strip()
    viewer_roles = sorted(normalize_roles(profile.get("roles") or []))
    viewer_role_set = set(viewer_roles)

    if "admin" in viewer_role_set:
        return

    assigned_owner_id = str(manuscript.get("owner_id") or "").strip()
    if assigned_owner_id and assigned_owner_id == viewer_user_id and "owner" in viewer_role_set:
        return

    assigned_ae_id = str(manuscript.get("assistant_editor_id") or "").strip()
    if assigned_ae_id and assigned_ae_id == viewer_user_id:
        return

    allowed = False
    if viewer_role_set.intersection({"managing_editor", "editor_in_chief"}):
        ensure_manuscript_scope_access(
            manuscript_id=manuscript_id,
            user_id=viewer_user_id,
            roles=viewer_roles,
            allow_admin_bypass=True,
        )
        allowed = True

    if (not allowed) and ("production_editor" in viewer_role_set):
        try:
            active_statuses = [
                "draft",
                "awaiting_author",
                "author_corrections_submitted",
                "author_confirmed",
                "in_layout_revision",
            ]
            pc = (
                supabase_admin.table("production_cycles")
                .select("id")
                .eq("manuscript_id", manuscript_id)
                .eq("layout_editor_id", viewer_user_id)
                .in_("status", active_statuses)
                .limit(1)
                .execute()
            )
            if getattr(pc, "data", None):
                allowed = True
            else:
                # Feature 042B: 协作者（collaborator_editor_ids）同样可访问详情页。
                try:
                    pc2 = (
                        supabase_admin.table("production_cycles")
                        .select("id")
                        .eq("manuscript_id", manuscript_id)
                        .contains("collaborator_editor_ids", [viewer_user_id])
                        .in_("status", active_statuses)
                        .limit(1)
                        .execute()
                    )
                    if getattr(pc2, "data", None):
                        allowed = True
                except Exception:
                    # 兼容旧环境未迁移 collaborator_editor_ids：忽略即可
                    pass
        except Exception:
            allowed = False

    if not allowed:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/manuscripts/{id}")
async def get_editor_manuscript_detail(
    id: str,
    skip_cards: bool = Query(False, description="首屏详情是否跳过统计卡片计算"),
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES + ["owner"])),
):
    """
    Feature 028 / US2: Editor 专用稿件详情（包含 invoice_metadata、owner/editor profile、journal 信息）。
    """
    _require_action_or_403(action="manuscript:view_detail", roles=profile.get("roles") or [])

    ms = _load_manuscript_or_404(id)
    _authorize_manuscript_detail_access(
        manuscript_id=id,
        manuscript=ms,
        current_user=current_user,
        profile=profile,
    )

    t_total_start = perf_counter()
    timings: dict[str, float] = {}

    def _mark(name: str, t_start: float) -> None:
        timings[name] = round((perf_counter() - t_start) * 1000, 1)

    # 票据/支付状态（容错：没有 invoice 也不应 500）
    invoice = None
    t0 = perf_counter()
    try:
        inv_resp = (
            supabase_admin.table("invoices")
            .select("id,manuscript_id,amount,status,confirmed_at,invoice_number,pdf_path,pdf_generated_at,pdf_error")
            .eq("manuscript_id", id)
            .single()
            .execute()
        )
        invoice = getattr(inv_resp, "data", None) or None
    except Exception:
        invoice = None
    _mark("invoice", t0)
    ms["invoice"] = invoice

    # Feature 033: 内部文件（cover letter / editor peer review attachments）
    mf_rows: list[dict[str, Any]] = []
    t0 = perf_counter()
    try:
        mf = (
            supabase_admin.table("manuscript_files")
            .select("id,file_type,bucket,path,original_filename,content_type,created_at,uploaded_by")
            .eq("manuscript_id", id)
            .order("created_at", desc=True)
            .execute()
        )
        mf_rows = getattr(mf, "data", None) or []
    except Exception as e:
        # 中文注释: 云端未应用 migration 时不应导致详情页 500
        if not _is_missing_table_error(str(e)):
            print(f"[ManuscriptFiles] load manuscript_files failed (ignored): {e}")
    _mark("manuscript_files", t0)

    # 审稿报告（用于附件 + submitted_at 聚合），尽量复用同一查询结果，避免重复打 DB。
    rr_rows: list[dict[str, Any]] = []
    t0 = perf_counter()
    try:
        rr = (
            supabase_admin.table("review_reports")
            .select("id,reviewer_id,attachment_path,created_at,status")
            .eq("manuscript_id", id)
            .order("created_at", desc=True)
            .execute()
        )
        rr_rows = getattr(rr, "data", None) or []
    except Exception as e:
        print(f"[ReviewReports] load failed (ignored): {e}")
    _mark("review_reports", t0)

    # 作者最近一次修回说明（Response Letter），用于 editor 详情页快速查看。
    ms["latest_author_response_letter"] = None
    ms["latest_author_response_submitted_at"] = None
    ms["latest_author_response_round"] = None
    ms["author_response_history"] = []
    # 中文注释:
    # - 云端历史 schema 可能无 revisions.updated_at，仅有 created_at；
    # - 这里按“排序列 + select”双重降级，确保 response_letter 可回显。
    t0 = perf_counter()
    revision_query_variants = [
        ("updated_at", "id,response_letter,submitted_at,updated_at,round"),
        ("created_at", "id,response_letter,submitted_at,created_at,round"),
        ("created_at", "id,response_letter,created_at"),
    ]
    for order_key, select_clause in revision_query_variants:
        try:
            revision_resp = (
                supabase_admin.table("revisions")
                .select(select_clause)
                .eq("manuscript_id", id)
                .order(order_key, desc=True)
                .limit(30)
                .execute()
            )
            revision_rows = getattr(revision_resp, "data", None) or []
            for row in revision_rows:
                response_letter = str(row.get("response_letter") or "").strip()
                if not response_letter:
                    continue
                submitted_at = row.get("submitted_at") or row.get("updated_at") or row.get("created_at")
                round_value = row.get("round")
                try:
                    round_value = int(round_value) if round_value is not None else None
                except Exception:
                    round_value = None

                ms["author_response_history"].append(
                    {
                        "id": row.get("id"),
                        "response_letter": response_letter,
                        "submitted_at": submitted_at,
                        "round": round_value,
                    }
                )

                if ms["latest_author_response_letter"] is None:
                    ms["latest_author_response_letter"] = response_letter
                    ms["latest_author_response_submitted_at"] = submitted_at
                    ms["latest_author_response_round"] = round_value
            break
        except Exception as e:
            lowered = str(e).lower()
            if "schema cache" in lowered or "column" in lowered or "pgrst" in lowered:
                continue
            print(f"[Revisions] load latest response letter failed (ignored): {e}")
            break
    _mark("revisions", t0)

    # 预审时间线
    tl_rows: list[dict[str, Any]] = []
    t0 = perf_counter()
    if not skip_cards:
        try:
            tl_resp = (
                supabase_admin.table("status_transition_logs")
                .select("id,created_at,comment,payload")
                .eq("manuscript_id", id)
                .order("created_at", desc=False)
                .limit(300)
                .execute()
            )
            tl_rows = getattr(tl_resp, "data", None) or []
        except Exception as e:
            print(f"[PrecheckTimeline] load failed (ignored): {e}")
    _mark("status_logs", t0)

    # Reviewer 邀请时间线
    ra_rows: list[dict[str, Any]] = []
    t0 = perf_counter()
    try:
        ra_resp = (
            supabase_admin.table("review_assignments")
            .select(
                "id,reviewer_id,status,due_at,invited_at,opened_at,accepted_at,declined_at,decline_reason,decline_note,created_at"
            )
            .eq("manuscript_id", id)
            .order("created_at", desc=True)
            .execute()
        )
        ra_rows = getattr(ra_resp, "data", None) or []
    except Exception as e:
        print(f"[ReviewerInvites] load failed (ignored): {e}")
    _mark("review_assignments", t0)

    # Feature 045: 稿件级任务逾期摘要（详情页右侧摘要使用）
    ms["task_summary"] = {
        "open_tasks_count": 0,
        "overdue_tasks_count": 0,
        "is_overdue": False,
        "nearest_due_at": None,
    }
    t0 = perf_counter()
    if not skip_cards:
        try:
            t_resp = (
                supabase_admin.table("internal_tasks")
                .select("id,status,due_at")
                .eq("manuscript_id", id)
                .execute()
            )
            t_rows = getattr(t_resp, "data", None) or []
            open_rows = [r for r in t_rows if str(r.get("status") or "").lower() != InternalTaskStatus.DONE.value]
            overdue_count = 0
            nearest_due: str | None = None
            now = datetime.now(timezone.utc)
            for row in open_rows:
                due_raw = str(row.get("due_at") or "")
                if not due_raw:
                    continue
                try:
                    due_at = datetime.fromisoformat(due_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
                except Exception:
                    continue
                if due_at < now:
                    overdue_count += 1
                if not nearest_due:
                    nearest_due = due_at.isoformat()
                else:
                    try:
                        prev = datetime.fromisoformat(nearest_due.replace("Z", "+00:00")).astimezone(timezone.utc)
                        if due_at < prev:
                            nearest_due = due_at.isoformat()
                    except Exception:
                        nearest_due = due_at.isoformat()

            ms["task_summary"] = {
                "open_tasks_count": len(open_rows),
                "overdue_tasks_count": overdue_count,
                "is_overdue": overdue_count > 0,
                "nearest_due_at": nearest_due,
            }
        except Exception as e:
            if not _is_missing_table_error(str(e)):
                print(f"[InternalTasks] task summary failed (ignored): {e}")
    _mark("task_summary", t0)

    # 合并构建 profile id，减少 user_profiles 的重复查询。
    profile_ids: set[str] = set()
    if ms.get("author_id"):
        profile_ids.add(str(ms["author_id"]))
    if ms.get("owner_id"):
        profile_ids.add(str(ms["owner_id"]))
    if ms.get("editor_id"):
        profile_ids.add(str(ms["editor_id"]))
    if ms.get("assistant_editor_id"):
        profile_ids.add(str(ms["assistant_editor_id"]))
    for row in rr_rows:
        rid = str(row.get("reviewer_id") or "").strip()
        if rid:
            profile_ids.add(rid)
    for row in ra_rows:
        rid = str(row.get("reviewer_id") or "").strip()
        if rid:
            profile_ids.add(rid)

    profiles_map: dict[str, dict] = {}
    t0 = perf_counter()
    if profile_ids:
        try:
            p = (
                supabase_admin.table("user_profiles")
                .select("id,email,full_name,roles,affiliation")
                .in_("id", sorted(profile_ids))
                .execute()
            )
            for row in (getattr(p, "data", None) or []):
                pid = str(row.get("id") or "")
                if pid:
                    profiles_map[pid] = row
        except Exception as e:
            print(f"[Profiles] load failed (ignored): {e}")
    _mark("profiles", t0)

    # Profile fallback（Auth -> Email/Name）:
    # 中文注释:
    # - 在少数环境下，auth.users 与 public.user_profiles 的同步触发器可能未生效，
    #   导致内部员工在详情页只显示 UUID（非常影响 UAT 可用性）。
    # - 这里做“只读兜底”：对缺失 profile 的用户，尝试从 Auth Admin API 拉取 email/full_name。
    try:
        missing_ids = [pid for pid in sorted(profile_ids) if pid and pid not in profiles_map]
    except Exception:
        missing_ids = []

    if missing_ids:
        # 限流：避免单次详情页触发过多 admin 调用。
        for uid in missing_ids[:20]:
            cache_hit, cached_profile = _get_cached_auth_profile(str(uid))
            if cache_hit:
                if cached_profile:
                    profiles_map[str(uid)] = cached_profile
                continue
            try:
                res = supabase_admin.auth.admin.get_user_by_id(str(uid))
                user = getattr(res, "user", None)
                if user is None and isinstance(res, dict):
                    user = res.get("user") or res.get("data")
                if not user:
                    _set_cached_auth_profile(str(uid), None)
                    continue
                if isinstance(user, dict):
                    email = user.get("email")
                    meta = user.get("user_metadata") or {}
                else:
                    email = getattr(user, "email", None)
                    meta = getattr(user, "user_metadata", None) or {}
                full_name = None
                try:
                    full_name = (meta or {}).get("full_name")
                except Exception:
                    full_name = None
                profiles_map[str(uid)] = {
                    "id": str(uid),
                    "email": email,
                    "full_name": full_name,
                    "roles": None,
                    "affiliation": None,
                }
                _set_cached_auth_profile(str(uid), profiles_map[str(uid)])
            except Exception:
                _set_cached_auth_profile(str(uid), None)
                continue

    aid = str(ms.get("author_id") or "")
    oid = str(ms.get("owner_id") or "")
    eid = str(ms.get("editor_id") or "")
    aeid = str(ms.get("assistant_editor_id") or "")
    ms["author"] = (
        {
            "id": aid,
            "full_name": (profiles_map.get(aid) or {}).get("full_name"),
            "email": (profiles_map.get(aid) or {}).get("email"),
            "affiliation": (profiles_map.get(aid) or {}).get("affiliation"),
        }
        if aid
        else None
    )
    ms["owner"] = (
        {"id": oid, "full_name": (profiles_map.get(oid) or {}).get("full_name"), "email": (profiles_map.get(oid) or {}).get("email")}
        if oid
        else None
    )
    ms["editor"] = (
        {"id": eid, "full_name": (profiles_map.get(eid) or {}).get("full_name"), "email": (profiles_map.get(eid) or {}).get("email")}
        if eid
        else None
    )
    ms["assistant_editor"] = (
        {
            "id": aeid,
            "full_name": (profiles_map.get(aeid) or {}).get("full_name"),
            "email": (profiles_map.get(aeid) or {}).get("email"),
        }
        if aeid
        else None
    )

    # 作者元信息兜底：若 invoice_metadata 未填写，详情页仍可回显作者姓名与机构。
    meta = ms.get("invoice_metadata")
    if not isinstance(meta, dict):
        meta = {}
        ms["invoice_metadata"] = meta
    if not str(meta.get("authors") or "").strip():
        meta["authors"] = str((ms.get("author") or {}).get("full_name") or "").strip() or None
    if not str(meta.get("affiliation") or "").strip():
        meta["affiliation"] = str((ms.get("author") or {}).get("affiliation") or "").strip() or None

    # 文件签名（原稿 PDF + 审稿附件）
    file_path = str(ms.get("file_path") or "").strip()
    original_signed_url = _get_signed_url("manuscripts", file_path) if file_path else None
    ms["files"] = []
    ms["signed_files"] = {
        "original_manuscript": {
            "bucket": "manuscripts",
            "path": file_path or None,
            "signed_url": original_signed_url,
        },
        "peer_review_reports": [],
    }
    if file_path:
        ms["files"].append(
            {
                "id": "original_manuscript",
                "file_type": "manuscript",
                "bucket": "manuscripts",
                "path": file_path,
                "label": "Current Manuscript PDF",
                "signed_url": original_signed_url,
                "created_at": ms.get("updated_at") or ms.get("created_at"),
            }
        )

    # 内部文件（cover letter / editor peer review attachments）
    for row in mf_rows:
        bucket = str(row.get("bucket") or "").strip()
        path = str(row.get("path") or "").strip()
        if not bucket or not path:
            continue
        ms["files"].append(
            {
                "id": row.get("id"),
                "file_type": row.get("file_type"),
                "bucket": bucket,
                "path": path,
                "label": row.get("original_filename") or path,
                "signed_url": _get_signed_url(bucket, path),
                "created_at": row.get("created_at"),
                "uploaded_by": row.get("uploaded_by"),
            }
        )

    # 从同一份 review_reports 行中同时构建:
    # - reviewer report 附件列表
    # - reviewer 提交时间 submitted_map（用于 Reviewer Invite Timeline）
    submitted_map: dict[str, str] = {}
    for row in rr_rows:
        rid = str(row.get("reviewer_id") or "").strip()
        status_raw = str(row.get("status") or "").lower()
        created_at = str(row.get("created_at") or "")
        if rid and status_raw == "completed" and rid not in submitted_map and created_at:
            submitted_map[rid] = created_at

    for row in rr_rows:
        path = str(row.get("attachment_path") or "").strip()
        if not path:
            continue
        rid = str(row.get("reviewer_id") or "").strip()
        prof = profiles_map.get(rid) or {}
        signed_url = _get_signed_url("review-attachments", path)
        ms["signed_files"]["peer_review_reports"].append(
            {
                "review_report_id": row.get("id"),
                "reviewer_id": row.get("reviewer_id"),
                "reviewer_name": prof.get("full_name"),
                "reviewer_email": prof.get("email"),
                "status": row.get("status"),
                "created_at": row.get("created_at"),
                "bucket": "review-attachments",
                "path": path,
                "signed_url": signed_url,
            }
        )
        ms["files"].append(
            {
                "id": row.get("id"),
                "file_type": "review_attachment",
                "bucket": "review-attachments",
                "path": path,
                "label": f"{prof.get('full_name') or prof.get('email') or rid or 'Reviewer'} — Annotated PDF",
                "signed_url": signed_url,
                "created_at": row.get("created_at"),
                "uploaded_by": row.get("reviewer_id"),
            }
        )

    # 044: 预审队列可视化（详情页）
    role_map = {
        "intake": "managing_editor",
        "technical": "assistant_editor",
        "academic": "editor_in_chief",
    }
    pre_stage = str(ms.get("pre_check_status") or "intake").strip().lower() or "intake"
    current_status = normalize_status(str(ms.get("status") or "")) or str(ms.get("status") or "").strip().lower()
    in_precheck = current_status == ManuscriptStatus.PRE_CHECK.value
    current_role = role_map.get(pre_stage, "managing_editor") if in_precheck else "completed"
    current_assignee = None
    current_assignee_label = None
    if in_precheck and pre_stage == "technical" and ms.get("assistant_editor_id"):
        aid2 = str(ms.get("assistant_editor_id"))
        aprof = profiles_map.get(aid2) or {}
        current_assignee = {"id": aid2, "full_name": aprof.get("full_name"), "email": aprof.get("email")}
    elif in_precheck and pre_stage == "academic":
        current_assignee_label = "Journal EIC Queue"
    elif in_precheck and pre_stage == "intake":
        current_assignee_label = "Managing Editor Queue"
    elif not in_precheck:
        current_assignee_label = "Pre-check completed"

    ms["precheck_timeline"] = []
    assigned_at = None
    technical_completed_at = None
    academic_completed_at = None
    if not skip_cards:
        for row in tl_rows:
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            action = str(payload.get("action") or "")
            if action.startswith("precheck_"):
                ms["precheck_timeline"].append(row)
                created_at = str(row.get("created_at") or "")
                if action in {"precheck_assign_ae", "precheck_reassign_ae"}:
                    assigned_at = created_at or assigned_at
                if action in {"precheck_technical_pass", "precheck_technical_revision", "precheck_technical_to_under_review"}:
                    technical_completed_at = created_at or technical_completed_at
                if action in {"precheck_academic_to_review", "precheck_academic_to_decision"}:
                    academic_completed_at = created_at or academic_completed_at

    ms["role_queue"] = {
        "current_role": current_role,
        "current_assignee": current_assignee,
        "current_assignee_label": current_assignee_label,
        "assigned_at": assigned_at,
        "technical_completed_at": technical_completed_at,
        "academic_completed_at": academic_completed_at,
    }

    # Feature 037: Reviewer invite timeline（Editor 可见）
    ms["reviewer_invites"] = []
    for row in ra_rows:
        rid = str(row.get("reviewer_id") or "").strip()
        prof = profiles_map.get(rid) or {}
        status_raw = str(row.get("status") or "").lower()
        if status_raw == "completed":
            invite_state = "submitted"
        elif status_raw == "declined" or row.get("declined_at"):
            invite_state = "declined"
        elif row.get("accepted_at"):
            invite_state = "accepted"
        else:
            invite_state = "invited"

        ms["reviewer_invites"].append(
            {
                "id": row.get("id"),
                "reviewer_id": row.get("reviewer_id"),
                "reviewer_name": prof.get("full_name"),
                "reviewer_email": prof.get("email"),
                "status": invite_state,
                "due_at": row.get("due_at"),
                "invited_at": row.get("invited_at") or row.get("created_at"),
                "opened_at": row.get("opened_at"),
                "accepted_at": row.get("accepted_at"),
                "declined_at": row.get("declined_at"),
                "submitted_at": submitted_map.get(rid),
                "decline_reason": row.get("decline_reason"),
                "decline_note": row.get("decline_note"),
            }
        )

    total_ms = round((perf_counter() - t_total_start) * 1000, 1)
    timing_text = " ".join([f"{k}={v}ms" for k, v in timings.items()])
    print(f"[EditorDetail:{id}] total={total_ms}ms {timing_text}")

    return {"success": True, "data": ms}


@router.get("/manuscripts/{id}/cards-context")
async def get_editor_manuscript_cards_context(
    id: str,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(require_any_role(EDITOR_SCOPE_COMPAT_ROLES + ["owner"])),
):
    """
    详情页统计卡片上下文（延迟加载）：
    - Task SLA Summary
    - Pre-check Role Queue
    """
    _require_action_or_403(action="manuscript:view_detail", roles=profile.get("roles") or [])

    ms = _load_manuscript_or_404(id)
    _authorize_manuscript_detail_access(
        manuscript_id=id,
        manuscript=ms,
        current_user=current_user,
        profile=profile,
    )

    task_summary = {
        "open_tasks_count": 0,
        "overdue_tasks_count": 0,
        "is_overdue": False,
        "nearest_due_at": None,
    }
    try:
        t_resp = (
            supabase_admin.table("internal_tasks")
            .select("id,status,due_at")
            .eq("manuscript_id", id)
            .execute()
        )
        t_rows = getattr(t_resp, "data", None) or []
        open_rows = [r for r in t_rows if str(r.get("status") or "").lower() != InternalTaskStatus.DONE.value]
        overdue_count = 0
        nearest_due: str | None = None
        now = datetime.now(timezone.utc)
        for row in open_rows:
            due_raw = str(row.get("due_at") or "")
            if not due_raw:
                continue
            try:
                due_at = datetime.fromisoformat(due_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
            except Exception:
                continue
            if due_at < now:
                overdue_count += 1
            if not nearest_due:
                nearest_due = due_at.isoformat()
            else:
                try:
                    prev = datetime.fromisoformat(nearest_due.replace("Z", "+00:00")).astimezone(timezone.utc)
                    if due_at < prev:
                        nearest_due = due_at.isoformat()
                except Exception:
                    nearest_due = due_at.isoformat()
        task_summary = {
            "open_tasks_count": len(open_rows),
            "overdue_tasks_count": overdue_count,
            "is_overdue": overdue_count > 0,
            "nearest_due_at": nearest_due,
        }
    except Exception as e:
        if not _is_missing_table_error(str(e)):
            print(f"[CardsContext] task summary failed (ignored): {e}")

    tl_rows: list[dict[str, Any]] = []
    try:
        tl_resp = (
            supabase_admin.table("status_transition_logs")
            .select("id,created_at,comment,payload")
            .eq("manuscript_id", id)
            .order("created_at", desc=False)
            .limit(300)
            .execute()
        )
        tl_rows = getattr(tl_resp, "data", None) or []
    except Exception as e:
        print(f"[CardsContext] precheck timeline failed (ignored): {e}")

    aid = str(ms.get("assistant_editor_id") or "").strip()
    assistant_profile: dict[str, Any] = {}
    if aid:
        try:
            p = (
                supabase_admin.table("user_profiles")
                .select("id,full_name,email")
                .eq("id", aid)
                .single()
                .execute()
            )
            assistant_profile = getattr(p, "data", None) or {}
        except Exception:
            assistant_profile = {}

    role_map = {
        "intake": "managing_editor",
        "technical": "assistant_editor",
        "academic": "editor_in_chief",
    }
    pre_stage = str(ms.get("pre_check_status") or "intake").strip().lower() or "intake"
    current_status = normalize_status(str(ms.get("status") or "")) or str(ms.get("status") or "").strip().lower()
    in_precheck = current_status == ManuscriptStatus.PRE_CHECK.value
    current_role = role_map.get(pre_stage, "managing_editor") if in_precheck else "completed"
    current_assignee = None
    current_assignee_label = None
    if in_precheck and pre_stage == "technical" and aid:
        current_assignee = {
            "id": aid,
            "full_name": assistant_profile.get("full_name"),
            "email": assistant_profile.get("email"),
        }
    elif in_precheck and pre_stage == "academic":
        current_assignee_label = "Journal EIC Queue"
    elif in_precheck and pre_stage == "intake":
        current_assignee_label = "Managing Editor Queue"
    elif not in_precheck:
        current_assignee_label = "Pre-check completed"

    assigned_at = None
    technical_completed_at = None
    academic_completed_at = None
    for row in tl_rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        action = str(payload.get("action") or "")
        if not action.startswith("precheck_"):
            continue
        created_at = str(row.get("created_at") or "")
        if action in {"precheck_assign_ae", "precheck_reassign_ae"}:
            assigned_at = created_at or assigned_at
        if action in {"precheck_technical_pass", "precheck_technical_revision", "precheck_technical_to_under_review"}:
            technical_completed_at = created_at or technical_completed_at
        if action in {"precheck_academic_to_review", "precheck_academic_to_decision"}:
            academic_completed_at = created_at or academic_completed_at

    role_queue = {
        "current_role": current_role,
        "current_assignee": current_assignee,
        "current_assignee_label": current_assignee_label,
        "assigned_at": assigned_at,
        "technical_completed_at": technical_completed_at,
        "academic_completed_at": academic_completed_at,
    }

    return {
        "success": True,
        "data": {
            "task_summary": task_summary,
            "role_queue": role_queue,
        },
    }
