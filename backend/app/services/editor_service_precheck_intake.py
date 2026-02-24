from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from app.models.manuscript import ManuscriptStatus, PreCheckStatus, normalize_status


class EditorServicePrecheckIntakeMixin:
    def get_intake_queue(
        self,
        page: int = 1,
        page_size: int = 20,
        *,
        q: str | None = None,
        overdue_only: bool = False,
        viewer_user_id: str | None = None,
        viewer_roles: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        ME Intake Queue:
        - Active: status=pre_check & pre_check_status=intake
        - Passive placeholder: status=minor_revision 且来源于 precheck_intake_revision（等待作者 resubmit）
        """
        selects = [
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id,author_id,journal_id,journals(title,slug)",
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id,author_id,journal_id",
            "id,title,created_at,updated_at,status,pre_check_status,assistant_editor_id,owner_id,author_id",
        ]
        fetch_end = max(page * page_size - 1, page_size - 1)

        active_rows: list[dict[str, Any]] = []
        active_last_error: Exception | None = None
        for select_clause in selects:
            try:
                query = (
                    self.client.table("manuscripts")
                    .select(select_clause)
                    .eq("status", ManuscriptStatus.PRE_CHECK.value)
                    .or_(f"pre_check_status.eq.{PreCheckStatus.INTAKE.value},pre_check_status.is.null")
                    .order("updated_at", desc=True)
                    .order("created_at", desc=True)
                    .range(0, fetch_end)
                )
                resp = query.execute()
                active_rows = getattr(resp, "data", None) or []
                break
            except Exception as e:
                active_last_error = e
                lowered = str(e).lower()
                if "journals" in lowered or "schema cache" in lowered or "pgrst" in lowered:
                    continue
                raise
        if not active_rows and active_last_error:
            # 若因 schema 漂移导致多次降级仍失败，则抛出原始异常便于定位。
            # 这里仅在 rows 为空且确实经历过异常时触发。
            lowered = str(active_last_error).lower()
            if "schema cache" in lowered or "could not find" in lowered:
                raise active_last_error

        waiting_rows_candidates: list[dict[str, Any]] = []
        waiting_last_error: Exception | None = None
        for select_clause in selects:
            try:
                query = (
                    self.client.table("manuscripts")
                    .select(select_clause)
                    .eq("status", ManuscriptStatus.MINOR_REVISION.value)
                    .order("updated_at", desc=True)
                    .order("created_at", desc=True)
                    .range(0, fetch_end)
                )
                resp = query.execute()
                waiting_rows_candidates = getattr(resp, "data", None) or []
                break
            except Exception as e:
                waiting_last_error = e
                lowered = str(e).lower()
                if "journals" in lowered or "schema cache" in lowered or "pgrst" in lowered:
                    continue
                raise
        if not waiting_rows_candidates and waiting_last_error:
            lowered = str(waiting_last_error).lower()
            if "schema cache" in lowered or "could not find" in lowered:
                # 中文注释: “灰态占位”不可用时降级为仅返回 active intake，不阻断主流程。
                waiting_rows_candidates = []

        # Intake 列表不需要加载完整 pre-check 时间线，避免每次刷新多打一条审计日志聚合查询。
        active_out = [self._map_precheck_row(r) for r in active_rows]
        for row in active_out:
            row["intake_actionable"] = True
            row["waiting_resubmit"] = False
            row["waiting_resubmit_at"] = None
            row["waiting_resubmit_reason"] = None

        waiting_ids = [
            str(row.get("id") or "").strip()
            for row in waiting_rows_candidates
            if str(row.get("id") or "").strip()
        ]
        waiting_reason_map = self._load_latest_precheck_intake_revision_logs(waiting_ids)
        waiting_out: list[dict[str, Any]] = []
        for row in waiting_rows_candidates:
            mid = str(row.get("id") or "").strip()
            reason_meta = waiting_reason_map.get(mid)
            if not mid or not reason_meta:
                continue
            out_row = dict(row)
            out_row["pre_check_status"] = "awaiting_resubmit"
            out_row["current_role"] = "author"
            out_row["current_assignee"] = None
            out_row["intake_actionable"] = False
            out_row["waiting_resubmit"] = True
            out_row["waiting_resubmit_at"] = reason_meta.get("created_at")
            out_row["waiting_resubmit_reason"] = reason_meta.get("comment")
            waiting_out.append(out_row)

        out = [*active_out, *waiting_out]

        # 补齐 owner/author 展示字段（full_name/email/affiliation），用于 Intake 决策信息补全。
        profile_ids = sorted(
            {
                str(pid)
                for row in out
                for pid in (row.get("owner_id"), row.get("author_id"))
                if str(pid or "").strip()
            }
        )
        profile_map: dict[str, dict[str, Any]] = {}
        if profile_ids:
            try:
                prof = (
                    self.client.table("user_profiles")
                    .select("id,full_name,email,affiliation")
                    .in_("id", profile_ids)
                    .execute()
                )
                for p in (getattr(prof, "data", None) or []):
                    pid = str(p.get("id") or "")
                    if pid:
                        profile_map[pid] = p
            except Exception as e:
                print(f"[Intake] load owner/author profiles failed (ignored): {e}")

        for row in out:
            oid = str(row.get("owner_id") or "")
            aid = str(row.get("author_id") or "")
            row["owner"] = (
                {
                    "id": oid,
                    "full_name": (profile_map.get(oid) or {}).get("full_name"),
                    "email": (profile_map.get(oid) or {}).get("email"),
                }
                if oid
                else None
            )
            row["author"] = (
                {
                    "id": aid,
                    "full_name": (profile_map.get(aid) or {}).get("full_name"),
                    "email": (profile_map.get(aid) or {}).get("email"),
                    "affiliation": (profile_map.get(aid) or {}).get("affiliation"),
                }
                if aid
                else None
            )
            journal = row.get("journals")
            if isinstance(journal, list):
                row["journal"] = journal[0] if journal else None
            elif isinstance(journal, dict):
                row["journal"] = journal
            else:
                row["journal"] = None

        now = datetime.now(timezone.utc)
        for row in out:
            if bool(row.get("waiting_resubmit")):
                row["intake_elapsed_hours"] = None
                row["is_overdue"] = False
                row["intake_priority"] = "normal"
                continue
            created_raw = str(row.get("created_at") or "")
            created_at: datetime | None = None
            if created_raw:
                try:
                    created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
                except Exception:
                    created_at = None
            if created_at is None:
                row["intake_elapsed_hours"] = None
                row["is_overdue"] = False
                row["intake_priority"] = "normal"
            else:
                elapsed_hours = max(0, int((now - created_at).total_seconds() // 3600))
                is_overdue = elapsed_hours >= 48
                row["intake_elapsed_hours"] = elapsed_hours
                row["is_overdue"] = is_overdue
                row["intake_priority"] = "high" if is_overdue else "normal"

        keyword = str(q or "").strip().lower()
        if keyword:
            out = [
                row
                for row in out
                if keyword in str(row.get("title") or "").lower()
                or keyword in str(row.get("id") or "").lower()
                or keyword in str(((row.get("owner") or {}).get("full_name") or "")).lower()
                or keyword in str(((row.get("author") or {}).get("full_name") or "")).lower()
                or keyword in str(((row.get("journal") or {}).get("title") or "")).lower()
                or keyword in str(row.get("waiting_resubmit_reason") or "").lower()
            ]

        if overdue_only:
            out = [row for row in out if bool(row.get("is_overdue"))]

        out = self._apply_process_visibility_scope(
            rows=out,
            viewer_user_id=viewer_user_id,
            viewer_roles=viewer_roles,
        )

        # 按 updated_at/created_at 全局排序后再分页，避免 active/passive 合并后顺序错乱。
        def _sort_key(item: dict[str, Any]) -> tuple[str, str]:
            updated = str(item.get("updated_at") or "")
            created = str(item.get("created_at") or "")
            return (updated, created)

        out.sort(key=_sort_key, reverse=True)
        start = max((page - 1) * page_size, 0)
        end = start + page_size
        return out[start:end]

    def assign_ae(
        self,
        manuscript_id: UUID,
        ae_id: UUID,
        current_user_id: UUID,
        *,
        owner_id: UUID | None = None,
        start_external_review: bool = False,
        bind_owner_if_empty: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Assign/Reassign AE with state guard + audit trail.
        """
        manuscript_id_str = str(manuscript_id)
        ae_id_str = str(ae_id)
        actor = str(current_user_id)
        now = self._now()

        ms = self._get_manuscript(manuscript_id_str)
        status = normalize_status(str(ms.get("status") or ""))
        pre = self._normalize_precheck_status(ms.get("pre_check_status"))
        ae_before = str(ms.get("assistant_editor_id") or "")
        owner_before = str(ms.get("owner_id") or "")

        if status != ManuscriptStatus.PRE_CHECK.value:
            raise HTTPException(status_code=400, detail="AE assignment only allowed in pre_check")
        if pre not in {PreCheckStatus.INTAKE.value, PreCheckStatus.TECHNICAL.value}:
            raise HTTPException(status_code=409, detail=f"Invalid pre-check stage for assignment: {pre}")
        if pre == PreCheckStatus.TECHNICAL.value and ae_before == ae_id_str:
            # 幂等：同一 AE 重复分派
            out = dict(ms)
            out["pre_check_status"] = pre
            out["assistant_editor_id"] = ae_id_str
            out["updated_at"] = now
            return self._map_precheck_row(out)

        action = "precheck_reassign_ae" if pre == PreCheckStatus.TECHNICAL.value and ae_before else "precheck_assign_ae"
        data = {
            "assistant_editor_id": ae_id_str,
            "pre_check_status": PreCheckStatus.TECHNICAL.value,
            "updated_at": now,
        }
        owner_override = str(owner_id or "").strip()
        if owner_override:
            # 中文注释:
            # - ME 在 Intake Queue 可一次性分配 AE + Owner；
            # - Owner 必须是内部员工（admin/managing_editor/owner），避免外键/越权问题。
            try:
                from app.services.owner_binding_service import validate_internal_owner_id
                validate_internal_owner_id(UUID(owner_override))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid owner_id: {e}") from e
            data["owner_id"] = owner_override
        elif bind_owner_if_empty and not owner_before:
            # 中文注释:
            # - Intake 一键分配场景下，若 owner 为空可自动兜底绑定当前 ME；
            # - 避免稿件离开 Intake 后由于 owner 为空造成后续权限/协作信息缺失。
            data["owner_id"] = actor
        # 条件更新，避免并发覆盖
        q = (
            self.client.table("manuscripts")
            .update(data)
            .eq("id", manuscript_id_str)
            .eq("status", ManuscriptStatus.PRE_CHECK.value)
        )
        if pre == PreCheckStatus.INTAKE.value:
            q = q.or_("pre_check_status.eq.intake,pre_check_status.is.null")
        else:
            q = q.eq("pre_check_status", PreCheckStatus.TECHNICAL.value)
        resp = q.execute()
        rows = getattr(resp, "data", None) or []
        if not rows:
            latest = self._get_manuscript(manuscript_id_str)
            if (
                normalize_status(str(latest.get("status") or "")) == ManuscriptStatus.PRE_CHECK.value
                and self._normalize_precheck_status(latest.get("pre_check_status")) == PreCheckStatus.TECHNICAL.value
                and str(latest.get("assistant_editor_id") or "") == ae_id_str
            ):
                return self._map_precheck_row(latest)
            raise HTTPException(status_code=409, detail="Assignment conflict: manuscript state changed")

        updated = rows[0]
        owner_after = (data.get("owner_id") if data.get("owner_id") else (owner_before or None))
        self._safe_insert_transition_log(
            manuscript_id=manuscript_id_str,
            from_status=ManuscriptStatus.PRE_CHECK.value,
            to_status=ManuscriptStatus.PRE_CHECK.value,
            changed_by=actor,
            comment=f"assign ae: {ae_id_str}",
            payload={
                "action": action,
                "pre_check_from": pre,
                "pre_check_to": PreCheckStatus.TECHNICAL.value,
                "assistant_editor_before": ae_before or None,
                "assistant_editor_after": ae_id_str,
                "owner_before": owner_before or None,
                "owner_after": owner_after,
                "decision": None,
                "idempotency_key": idempotency_key,
            },
            created_at=now,
        )
        mapped = self._map_precheck_row(updated)

        if not start_external_review:
            return mapped

        # 中文注释:
        # - 入口页“通过并分配 AE”可选择一键进入 under_review；
        # - 该路径等价于 ME 完成技术审查后直接发起外审，避免稿件掉出 Intake 但仍停留 pre_check。
        moved = self.editorial.update_status(
            manuscript_id=manuscript_id_str,
            to_status=ManuscriptStatus.UNDER_REVIEW.value,
            changed_by=actor,
            comment="intake approve + assign AE + start external review",
            allow_skip=False,
            extra_updates={"pre_check_status": None},
            payload={
                "action": "precheck_assign_ae_start_review",
                "pre_check_from": PreCheckStatus.TECHNICAL.value,
                "pre_check_to": None,
                "assistant_editor_before": ae_before or None,
                "assistant_editor_after": ae_id_str,
                "owner_before": owner_before or None,
                "owner_after": owner_after,
                "decision": "pass",
                "source": "intake_assign_modal",
                "idempotency_key": idempotency_key,
            },
        )
        return moved

    def request_intake_revision(
        self,
        manuscript_id: UUID,
        current_user_id: UUID,
        *,
        comment: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        ME 入口技术审查：退回作者修改（非学术拒稿）。

        中文注释:
        - 仅允许在 pre_check/intake 阶段执行；
        - 结果流转到 minor_revision，作者修回后再进入流程；
        - 幂等处理：若已在 minor_revision，重复提交直接返回当前稿件。
        """
        manuscript_id_str = str(manuscript_id)
        actor = str(current_user_id)
        comment_clean = (comment or "").strip()
        if not comment_clean:
            raise HTTPException(status_code=422, detail="comment is required")

        ms = self._get_manuscript(manuscript_id_str)
        status = normalize_status(str(ms.get("status") or ""))
        pre = self._normalize_precheck_status(ms.get("pre_check_status"))

        if status == ManuscriptStatus.MINOR_REVISION.value:
            return dict(ms)

        if status != ManuscriptStatus.PRE_CHECK.value:
            raise HTTPException(status_code=409, detail="Intake revision only allowed in pre_check")
        if pre != PreCheckStatus.INTAKE.value:
            raise HTTPException(status_code=409, detail=f"Intake revision only allowed in intake stage, current={pre}")

        updated = self.editorial.update_status(
            manuscript_id=manuscript_id_str,
            to_status=ManuscriptStatus.MINOR_REVISION.value,
            changed_by=actor,
            comment=comment_clean,
            allow_skip=False,
            payload={
                "action": "precheck_intake_revision",
                "pre_check_from": PreCheckStatus.INTAKE.value,
                "pre_check_to": None,
                "decision": "revision",
                "idempotency_key": idempotency_key,
            },
        )
        return updated
