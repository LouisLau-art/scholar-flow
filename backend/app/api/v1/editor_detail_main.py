from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from fastapi import Request

from app.api.v1 import editor_detail_runtime as runtime
from app.models.internal_task import InternalTaskStatus
from app.models.manuscript import ManuscriptStatus, normalize_status

logger = logging.getLogger("scholarflow.editor_detail_main")


def _serialize_assignment_email_event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "assignment_id": row.get("assignment_id"),
        "manuscript_id": row.get("manuscript_id"),
        "status": str(row.get("status") or "").strip().lower() or None,
        "event_type": str(row.get("event_type") or "").strip().lower() or None,
        "template_name": row.get("template_name"),
        "created_at": row.get("created_at"),
        "error_message": row.get("error_message"),
        "provider_id": row.get("provider_id"),
        "idempotency_key": row.get("idempotency_key"),
    }


def _load_assignment_email_events(*, assignment_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    normalized_ids = [str(item or "").strip() for item in assignment_ids if str(item or "").strip()]
    if not normalized_ids:
        return {}
    try:
        rows = (
            runtime.supabase_admin.table("email_logs")
            .select(
                "assignment_id, manuscript_id, template_name, status, event_type, error_message, provider_id, idempotency_key, created_at"
            )
            .in_("assignment_id", normalized_ids)
            .order("created_at", desc=True)
            .execute()
        )
        out: dict[str, list[dict[str, Any]]] = {}
        for row in (getattr(rows, "data", None) or []):
            assignment_id = str(row.get("assignment_id") or "").strip()
            if not assignment_id:
                continue
            out.setdefault(assignment_id, []).append(_serialize_assignment_email_event(row))
        return out
    except Exception:
        return {}


def _load_reviewer_assignments_for_detail(manuscript_id: str) -> list[dict[str, Any]]:
    select_variants = (
        "id,reviewer_id,status,due_at,invited_at,opened_at,accepted_at,declined_at,last_reminded_at,decline_reason,decline_note,created_at,round_number,selected_by,selected_via,invited_by,invited_via,cancelled_at,cancelled_by,cancel_reason,cancel_via",
        "id,reviewer_id,status,due_at,invited_at,opened_at,accepted_at,declined_at,last_reminded_at,decline_reason,decline_note,created_at,round_number",
        "id,reviewer_id,status,due_at,invited_at,opened_at,accepted_at,declined_at,last_reminded_at,created_at,round_number",
        "id,reviewer_id,status,due_at,invited_at,opened_at,accepted_at,declined_at,last_reminded_at,created_at",
        "id,reviewer_id,status,due_at,invited_at,created_at",
    )
    last_exc: Exception | None = None
    for select_clause in select_variants:
        try:
            ra_resp = (
                runtime.supabase_admin.table("review_assignments")
                .select(select_clause)
                .eq("manuscript_id", manuscript_id)
                .order("created_at", desc=True)
                .execute()
            )
            return getattr(ra_resp, "data", None) or []
        except Exception as exc:
            last_exc = exc
            if not runtime._is_schema_compat_error(exc):
                raise
    if last_exc:
        raise last_exc
    return []


async def get_editor_manuscript_detail_impl(
    request: Request,
    id: str,
    skip_cards: bool,
    include_heavy: bool,
    current_user: dict,
    profile: dict,
):
    """
    Feature 028 / US2: Editor 专用稿件详情（包含 invoice_metadata、owner/editor profile、journal 信息）。
    """
    runtime._require_action_or_403(action="manuscript:view_detail", roles=profile.get("roles") or [])

    ms = runtime._load_manuscript_or_404(id)
    runtime._authorize_manuscript_detail_access(
        manuscript_id=id,
        manuscript=ms,
        current_user=current_user,
        profile=profile,
    )

    t_total_start = perf_counter()
    timings: dict[str, float] = {}

    def _mark(name: str, t_start: float) -> None:
        timings[name] = round((perf_counter() - t_start) * 1000, 1)

    force_refresh = runtime._is_force_refresh_request(request)
    # 轻量详情模式：skip_cards=true 时默认跳过重查询。
    # include_heavy=true 可用于前端二次补拉（不阻塞首屏）。
    load_heavy_blocks = (not skip_cards) or bool(include_heavy)
    ms["is_deferred_context_loaded"] = bool(load_heavy_blocks)

    # 票据/支付状态（容错：没有 invoice 也不应 500）
    invoice = None
    t0 = perf_counter()
    try:
        inv_resp = (
            runtime.supabase_admin.table("invoices")
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

    # 重区块上下文（files/reviewer invites/revisions）：
    # - 首屏轻量请求默认跳过；
    # - include_heavy=true 或 skip_cards=false 时加载；
    # - 用短缓存削峰，并允许 x-sf-force-refresh 强制绕过。
    mf_rows: list[dict[str, Any]] = []
    rr_rows: list[dict[str, Any]] = []
    ra_rows: list[dict[str, Any]] = []
    email_log_rows: list[dict[str, Any]] = []
    ms["latest_author_response_letter"] = None
    ms["latest_author_response_submitted_at"] = None
    ms["latest_author_response_round"] = None
    ms["author_response_history"] = []
    if load_heavy_blocks:
        heavy_cache_key = f"mid={id}|{runtime._editor_detail_data_source_marker()}"
        heavy_ctx: dict[str, Any] | None = None
        t0 = perf_counter()
        if not force_refresh:
            heavy_ctx = runtime._detail_heavy_block_cache.get(heavy_cache_key)
        if heavy_ctx is not None:
            _mark("heavy_ctx_cache", t0)
            mf_rows = list(heavy_ctx.get("manuscript_files") or [])
            rr_rows = list(heavy_ctx.get("review_reports") or [])
            ra_rows = list(heavy_ctx.get("review_assignments") or [])
            email_log_rows = list(heavy_ctx.get("email_logs") or [])
            ms["latest_author_response_letter"] = heavy_ctx.get("latest_author_response_letter")
            ms["latest_author_response_submitted_at"] = heavy_ctx.get("latest_author_response_submitted_at")
            ms["latest_author_response_round"] = heavy_ctx.get("latest_author_response_round")
            ms["author_response_history"] = list(heavy_ctx.get("author_response_history") or [])
            timings["manuscript_files"] = 0.0
            timings["review_reports"] = 0.0
            timings["revisions"] = 0.0
            timings["review_assignments"] = 0.0
            timings["email_logs"] = 0.0
        else:
            _mark("heavy_ctx_cache", t0)
            # Feature 033: 内部文件（cover letter / editor peer review attachments）
            t0 = perf_counter()
            try:
                mf = (
                    runtime.supabase_admin.table("manuscript_files")
                    .select("id,file_type,bucket,path,original_filename,content_type,created_at,uploaded_by")
                    .eq("manuscript_id", id)
                    .order("created_at", desc=True)
                    .execute()
                )
                mf_rows = getattr(mf, "data", None) or []
            except Exception as e:
                # 中文注释: 云端未应用 migration 时不应导致详情页 500
                if not runtime._is_missing_table_error(str(e)):
                    logger.warning("[ManuscriptFiles] load manuscript_files failed (ignored): %s", e)
            _mark("manuscript_files", t0)

            # 审稿报告（用于附件 + submitted_at 聚合），尽量复用同一查询结果，避免重复打 DB。
            t0 = perf_counter()
            try:
                rr = (
                    runtime.supabase_admin.table("review_reports")
                    .select("id,reviewer_id,attachment_path,created_at,status")
                    .eq("manuscript_id", id)
                    .order("created_at", desc=True)
                    .execute()
                )
                rr_rows = getattr(rr, "data", None) or []
            except Exception as e:
                logger.warning("[ReviewReports] load failed (ignored): %s", e)
            _mark("review_reports", t0)

            # 作者最近一次修回说明（Response Letter）
            t0 = perf_counter()
            revision_snapshot = runtime._load_revision_response_snapshot(id)
            ms["latest_author_response_letter"] = revision_snapshot.get("latest_author_response_letter")
            ms["latest_author_response_submitted_at"] = revision_snapshot.get("latest_author_response_submitted_at")
            ms["latest_author_response_round"] = revision_snapshot.get("latest_author_response_round")
            ms["author_response_history"] = list(revision_snapshot.get("author_response_history") or [])
            _mark("revisions", t0)

            # Reviewer 邀请时间线
            t0 = perf_counter()
            try:
                ra_rows = _load_reviewer_assignments_for_detail(id)
            except Exception as e:
                logger.warning("[ReviewerInvites] load failed (ignored): %s", e)
            _mark("review_assignments", t0)

            t0 = perf_counter()
            assignment_ids = [str(row.get("id") or "").strip() for row in ra_rows if str(row.get("id") or "").strip()]
            email_events_map = _load_assignment_email_events(assignment_ids=assignment_ids)
            for assignment_id in assignment_ids:
                email_log_rows.extend(email_events_map.get(assignment_id, []))
            _mark("email_logs", t0)

            runtime._detail_heavy_block_cache.set(
                heavy_cache_key,
                {
                    "manuscript_files": mf_rows,
                    "review_reports": rr_rows,
                    "review_assignments": ra_rows,
                    "email_logs": email_log_rows,
                    "latest_author_response_letter": ms.get("latest_author_response_letter"),
                    "latest_author_response_submitted_at": ms.get("latest_author_response_submitted_at"),
                    "latest_author_response_round": ms.get("latest_author_response_round"),
                    "author_response_history": ms.get("author_response_history") or [],
                },
                ttl_sec=runtime._DETAIL_HEAVY_BLOCK_CACHE_TTL_SEC,
            )
    else:
        timings["manuscript_files"] = 0.0
        timings["review_reports"] = 0.0
        timings["revisions"] = 0.0
        timings["review_assignments"] = 0.0
        timings["email_logs"] = 0.0

    # 预审时间线
    tl_rows: list[dict[str, Any]] = []
    t0 = perf_counter()
    if not skip_cards:
        try:
            tl_resp = (
                runtime.supabase_admin.table("status_transition_logs")
                .select("id,created_at,comment,payload")
                .eq("manuscript_id", id)
                .order("created_at", desc=False)
                .limit(300)
                .execute()
            )
            tl_rows = getattr(tl_resp, "data", None) or []
        except Exception as e:
            logger.warning("[PrecheckTimeline] load failed (ignored): %s", e)
    _mark("status_logs", t0)

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
                runtime.supabase_admin.table("internal_tasks")
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
            if not runtime._is_missing_table_error(str(e)):
                logger.warning("[InternalTasks] task summary failed (ignored): %s", e)
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
    if ms.get("academic_editor_id"):
        profile_ids.add(str(ms["academic_editor_id"]))
    for row in rr_rows:
        rid = str(row.get("reviewer_id") or "").strip()
        if rid:
            profile_ids.add(rid)
    for row in ra_rows:
        rid = str(row.get("reviewer_id") or "").strip()
        if rid:
            profile_ids.add(rid)
        selected_by = str(row.get("selected_by") or "").strip()
        if selected_by:
            profile_ids.add(selected_by)
        invited_by = str(row.get("invited_by") or "").strip()
        if invited_by:
            profile_ids.add(invited_by)
        cancelled_by = str(row.get("cancelled_by") or "").strip()
        if cancelled_by:
            profile_ids.add(cancelled_by)

    profiles_map: dict[str, dict] = {}
    t0 = perf_counter()
    if profile_ids:
        try:
            p = (
                runtime.supabase_admin.table("user_profiles")
                .select("id,email,full_name,roles,affiliation")
                .in_("id", sorted(profile_ids))
                .execute()
            )
            for row in (getattr(p, "data", None) or []):
                pid = str(row.get("id") or "")
                if pid:
                    profiles_map[pid] = row
        except Exception as e:
            logger.warning("[Profiles] load failed (ignored): %s", e)
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
            cache_hit, cached_profile = runtime._get_cached_auth_profile(str(uid))
            if cache_hit:
                if cached_profile:
                    profiles_map[str(uid)] = cached_profile
                continue
            try:
                res = runtime.supabase_admin.auth.admin.get_user_by_id(str(uid))
                user = getattr(res, "user", None)
                if user is None and isinstance(res, dict):
                    user = res.get("user") or res.get("data")
                if not user:
                    runtime._set_cached_auth_profile(str(uid), None)
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
                runtime._set_cached_auth_profile(str(uid), profiles_map[str(uid)])
            except Exception:
                runtime._set_cached_auth_profile(str(uid), None)
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
    academic_editor_id = str(ms.get("academic_editor_id") or "").strip()
    ms["academic_editor"] = (
        {
            "id": academic_editor_id,
            "full_name": (profiles_map.get(academic_editor_id) or {}).get("full_name"),
            "email": (profiles_map.get(academic_editor_id) or {}).get("email"),
        }
        if academic_editor_id
        else None
    )

    # 作者元信息兜底：若 invoice_metadata 未填写，详情页仍可回显作者姓名与机构。
    meta = ms.get("invoice_metadata")
    if not isinstance(meta, dict):
        meta = {}
        ms["invoice_metadata"] = meta
    if not str(meta.get("authors") or "").strip():
        raw_authors = ms.get("authors")
        if isinstance(raw_authors, list):
            joined_authors = ", ".join(str(item or "").strip() for item in raw_authors if str(item or "").strip())
            meta["authors"] = joined_authors or None
        else:
            meta["authors"] = str((ms.get("author") or {}).get("full_name") or "").strip() or None
    if not str(meta.get("affiliation") or "").strip():
        author_contacts = ms.get("author_contacts") if isinstance(ms.get("author_contacts"), list) else []
        corresponding = next(
            (item for item in author_contacts if isinstance(item, dict) and item.get("is_corresponding")),
            author_contacts[0] if author_contacts else None,
        )
        meta["affiliation"] = (
            str((corresponding or {}).get("affiliation") or "").strip()
            or str((ms.get("author") or {}).get("affiliation") or "").strip()
            or None
        )

    # 文件签名（原稿 PDF + 审稿附件）
    file_path = str(ms.get("file_path") or "").strip()
    original_signed_url = runtime._get_signed_url("manuscripts", file_path) if file_path else None
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
                "signed_url": runtime._get_signed_url(bucket, path),
                "created_at": row.get("created_at"),
                "uploaded_by": row.get("uploaded_by"),
            }
        )

    # 从同一份 review_reports 行中同时构建:
    # - reviewer report 附件列表
    # - reviewer 提交时间 submitted_map（用于 Reviewer Invite Timeline）
    reviewer_assignment_counts: dict[str, int] = {}
    for row in ra_rows:
        rid = str(row.get("reviewer_id") or "").strip()
        if not rid:
            continue
        reviewer_assignment_counts[rid] = reviewer_assignment_counts.get(rid, 0) + 1

    submitted_map: dict[str, str] = {}
    for row in rr_rows:
        rid = str(row.get("reviewer_id") or "").strip()
        status_raw = str(row.get("status") or "").lower()
        created_at = str(row.get("created_at") or "")
        # 中文注释: review_reports 当前没有 assignment_id。
        # 当同一 reviewer 在同一稿件存在多轮 assignment 时，无法安全判断这份报告属于哪一轮，
        # 宁可不在详情页伪装成某一轮已提交，也不要把 submitted_at 错贴到所有轮次上。
        if (
            rid
            and reviewer_assignment_counts.get(rid, 0) == 1
            and status_raw == "completed"
            and rid not in submitted_map
            and created_at
        ):
            submitted_map[rid] = created_at

    for row in rr_rows:
        path = str(row.get("attachment_path") or "").strip()
        if not path:
            continue
        rid = str(row.get("reviewer_id") or "").strip()
        prof = profiles_map.get(rid) or {}
        signed_url = runtime._get_signed_url("review-attachments", path)
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
        "academic": "academic_editor",
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
    elif in_precheck and pre_stage == "academic" and ms.get("academic_editor_id"):
        academic_editor_id = str(ms.get("academic_editor_id"))
        aprof = profiles_map.get(academic_editor_id) or {}
        current_assignee = {
            "id": academic_editor_id,
            "full_name": aprof.get("full_name"),
            "email": aprof.get("email"),
        }
        current_assignee_label = "Assigned Academic Editor"
    elif in_precheck and pre_stage == "academic":
        current_assignee_label = "Academic Editor Queue"
    elif in_precheck and pre_stage == "intake":
        current_assignee_label = "Managing Editor Queue"
    elif not in_precheck:
        current_assignee_label = "Pre-check completed"

    ms["precheck_timeline"] = []
    assigned_at = None
    technical_completed_at = None
    academic_completed_at = None
    academic_submitted_at = str(ms.get("academic_submitted_at") or "").strip() or None
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
        "academic_submitted_at": academic_submitted_at,
        "academic_completed_at": academic_completed_at,
    }

    # Feature 037: Reviewer invite timeline（Editor 可见）
    ms["reviewer_invites"] = []
    email_events_by_assignment: dict[str, list[dict[str, Any]]] = {}
    for row in email_log_rows:
        assignment_id = str(row.get("assignment_id") or "").strip()
        if not assignment_id:
            continue
        email_events_by_assignment.setdefault(assignment_id, []).append(row)
    for row in ra_rows:
        rid = str(row.get("reviewer_id") or "").strip()
        prof = profiles_map.get(rid) or {}
        assignment_id = str(row.get("id") or "").strip()
        email_events = email_events_by_assignment.get(assignment_id, [])
        latest_email = email_events[0] if email_events else {}
        selected_by_id = str(row.get("selected_by") or "").strip()
        invited_by_id = str(row.get("invited_by") or "").strip()
        cancelled_by_id = str(row.get("cancelled_by") or "").strip()
        selected_by_profile = profiles_map.get(selected_by_id) or {}
        invited_by_profile = profiles_map.get(invited_by_id) or {}
        cancelled_by_profile = profiles_map.get(cancelled_by_id) or {}
        status_raw = str(row.get("status") or "").lower()
        if status_raw in {"completed", "submitted"} or submitted_map.get(rid):
            invite_state = "submitted"
        elif status_raw == "cancelled" or row.get("cancelled_at"):
            invite_state = "cancelled"
        elif status_raw in {"declined", "decline"} or row.get("declined_at"):
            invite_state = "declined"
        elif status_raw in {"accepted", "agree", "agreed"} or row.get("accepted_at"):
            invite_state = "accepted"
        elif status_raw == "opened" or row.get("opened_at"):
            invite_state = "opened"
        elif status_raw == "invited" or row.get("invited_at"):
            invite_state = "invited"
        else:
            invite_state = "selected"

        ms["reviewer_invites"].append(
            {
                "id": row.get("id"),
                "reviewer_id": row.get("reviewer_id"),
                "reviewer_name": prof.get("full_name"),
                "reviewer_email": prof.get("email"),
                "status": invite_state,
                "round_number": row.get("round_number"),
                "added_by_id": selected_by_id or None,
                "added_by_name": selected_by_profile.get("full_name"),
                "added_by_email": selected_by_profile.get("email"),
                "added_via": row.get("selected_via"),
                "invited_by_id": invited_by_id or None,
                "invited_by_name": invited_by_profile.get("full_name"),
                "invited_by_email": invited_by_profile.get("email"),
                "invited_via": row.get("invited_via"),
                "cancelled_by_id": cancelled_by_id or None,
                "cancelled_by_name": cancelled_by_profile.get("full_name"),
                "cancelled_by_email": cancelled_by_profile.get("email"),
                "cancelled_at": row.get("cancelled_at"),
                "cancel_reason": row.get("cancel_reason"),
                "cancel_via": row.get("cancel_via"),
                "due_at": row.get("due_at"),
                "invited_at": row.get("invited_at"),
                "opened_at": row.get("opened_at"),
                "accepted_at": row.get("accepted_at"),
                "declined_at": row.get("declined_at"),
                "last_reminded_at": row.get("last_reminded_at"),
                "submitted_at": submitted_map.get(rid),
                "decline_reason": row.get("decline_reason"),
                "decline_note": row.get("decline_note"),
                "latest_email_status": latest_email.get("status"),
                "latest_email_at": latest_email.get("created_at"),
                "latest_email_error": latest_email.get("error_message"),
                "email_events": email_events,
            }
        )

    total_ms = round((perf_counter() - t_total_start) * 1000, 1)
    timing_text = " ".join([f"{k}={v}ms" for k, v in timings.items()])
    logger.info("[EditorDetail:%s] total=%sms %s", id, total_ms, timing_text)

    return {"success": True, "data": ms}
