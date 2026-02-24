from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.models.manuscript import ManuscriptStatus, normalize_status
from app.models.production_workspace import (
    CreateProductionCycleRequest,
    SubmitProofreadingRequest,
    UpdateProductionCycleEditorsRequest,
)


POST_ACCEPTANCE_ALLOWED = {
    ManuscriptStatus.APPROVED.value,
    ManuscriptStatus.LAYOUT.value,
    ManuscriptStatus.ENGLISH_EDITING.value,
    ManuscriptStatus.PROOFREADING.value,
}

ACTIVE_CYCLE_STATUSES = {
    "draft",
    "awaiting_author",
    "author_corrections_submitted",
    "author_confirmed",
    "in_layout_revision",
}

AUTHOR_CONTEXT_VISIBLE_STATUSES = {
    "awaiting_author",
    "author_corrections_submitted",
    "author_confirmed",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _to_utc_datetime(raw: Any) -> datetime | None:
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw.astimezone(timezone.utc)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return None
    return None


def _is_truthy_env(name: str, default: str = "0") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "y",
    }


def _is_table_missing_error(error: Exception, table_name: str) -> bool:
    text = str(error).lower()
    return table_name.lower() in text and "does not exist" in text


def _is_missing_column_error(error: Exception, column_name: str) -> bool:
    text = str(error).lower()
    return column_name.lower() in text and ("column" in text or "schema cache" in text)


def _safe_filename(filename: str) -> str:
    return str(filename or "proof.pdf").replace("/", "_").replace("\\", "_")


class ProductionWorkspaceWorkflowMixin:
    def get_workspace_context(
        self,
        *,
        manuscript_id: str,
        user_id: str,
        profile_roles: list[str] | None,
    ) -> dict[str, Any]:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        cycles = self._get_cycles(manuscript_id)
        active = next((c for c in cycles if str(c.get("status") or "") in ACTIVE_CYCLE_STATUSES), None)
        # 中文注释：
        # - cycle 核准后会进入 approved_for_publish，不再属于 active；
        # - 但 PE 仍需要可读访问 workspace（查看核准结果/当前清样），否则前端会误显示 unavailable。
        latest_approved = next((c for c in cycles if str(c.get("status") or "") == "approved_for_publish"), None)
        display_cycle = active or latest_approved
        self._ensure_editor_access(
            manuscript=manuscript, user_id=user_id, roles=roles, cycle=display_cycle, purpose="read"
        )

        manuscript_status = normalize_status(str(manuscript.get("status") or "")) or ""
        active_layout_id = str((active or {}).get("layout_editor_id") or "").strip() if active else ""
        active_collabs = set(self._normalize_uuid_list((active or {}).get("collaborator_editor_ids"))) if active else set()
        can_manage_production = bool(roles.intersection({"admin", "managing_editor", "editor_in_chief"})) or bool(
            "production_editor" in roles and active and (active_layout_id == str(user_id) or str(user_id) in active_collabs)
        )
        can_create = can_manage_production and manuscript_status in POST_ACCEPTANCE_ALLOWED and active is None

        return {
            "manuscript": {
                "id": manuscript.get("id"),
                "title": manuscript.get("title") or "Untitled",
                "status": manuscript.get("status"),
                "author_id": manuscript.get("author_id"),
                "editor_id": manuscript.get("editor_id"),
                "owner_id": manuscript.get("owner_id"),
                "assistant_editor_id": manuscript.get("assistant_editor_id"),
                "pdf_url": self._signed_url("manuscripts", str(manuscript.get("file_path") or "")),
            },
            "active_cycle": self._format_cycle(display_cycle, include_signed_url=True) if display_cycle else None,
            "cycle_history": [self._format_cycle(c, include_signed_url=False) for c in cycles],
            "permissions": {
                "can_create_cycle": can_create,
                "can_manage_editors": bool(roles.intersection({"admin", "managing_editor", "editor_in_chief"})),
                "can_upload_galley": bool(
                    can_manage_production
                    and active
                    and str(active.get("status") or "")
                    in {"draft", "in_layout_revision", "author_corrections_submitted"}
                ),
                "can_approve": bool(
                    can_manage_production
                    and active
                    and str(active.get("status") or "") == "author_confirmed"
                ),
            },
        }

    def create_cycle(
        self,
        *,
        manuscript_id: str,
        user_id: str,
        profile_roles: list[str] | None,
        request: CreateProductionCycleRequest,
    ) -> dict[str, Any]:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        self._ensure_editor_access(manuscript=manuscript, user_id=user_id, roles=roles, purpose="write")

        status = normalize_status(str(manuscript.get("status") or "")) or ""
        if status not in POST_ACCEPTANCE_ALLOWED:
            raise HTTPException(
                status_code=422,
                detail=f"Production cycle requires status in {sorted(POST_ACCEPTANCE_ALLOWED)}",
            )

        if request.proof_due_at <= _utc_now():
            raise HTTPException(status_code=422, detail="proof_due_at must be in the future")

        active = next(
            (c for c in self._get_cycles(manuscript_id) if str(c.get("status") or "") in ACTIVE_CYCLE_STATUSES),
            None,
        )
        if active:
            raise HTTPException(status_code=409, detail="An active production cycle already exists")

        # MVP 约束：当前只支持稿件 owner(author_id) 作为责任作者。
        manuscript_author = str(manuscript.get("author_id") or "").strip()
        if manuscript_author and manuscript_author != str(request.proofreader_author_id):
            raise HTTPException(
                status_code=422,
                detail="proofreader_author_id must match manuscript author_id in MVP",
            )

        # 中文注释：
        # - Production workspace 的写操作只允许 production_editor/admin 等角色；
        # - 如果 layout_editor_id 不是 production_editor，会导致被分配的人无法进入队列/上传清样。
        layout_editor_id = str(request.layout_editor_id)
        layout_roles = self._get_profile_roles(layout_editor_id)
        if not layout_roles:
            raise HTTPException(status_code=422, detail="layout_editor_id user not found")
        if not layout_roles.intersection({"production_editor", "admin"}):
            raise HTTPException(status_code=422, detail="layout_editor_id must have production_editor role")

        raw_collabs = [str(uid) for uid in (request.collaborator_editor_ids or [])]
        collab_ids = []
        seen = set()
        for cid in raw_collabs:
            c = str(cid or "").strip()
            if not c or c == layout_editor_id or c in seen:
                continue
            seen.add(c)
            collab_ids.append(c)
        # 防止异常 payload 导致过大数组写入
        if len(collab_ids) > 20:
            raise HTTPException(status_code=422, detail="Too many collaborator editors (max 20)")
        for cid in collab_ids:
            roles_set = self._get_profile_roles(cid)
            if not roles_set:
                raise HTTPException(status_code=422, detail="collaborator_editor_ids contains unknown user")
            if not roles_set.intersection({"production_editor", "admin"}):
                raise HTTPException(status_code=422, detail="collaborator_editor_ids must have production_editor role")

        now = _utc_now_iso()
        payload = {
            "manuscript_id": manuscript_id,
            "cycle_no": self._next_cycle_no(manuscript_id),
            "status": "draft",
            "layout_editor_id": layout_editor_id,
            "collaborator_editor_ids": collab_ids,
            "proofreader_author_id": str(request.proofreader_author_id),
            "proof_due_at": request.proof_due_at.isoformat(),
            "created_at": now,
            "updated_at": now,
        }
        try:
            resp = self.client.table("production_cycles").insert(payload).execute()
            rows = getattr(resp, "data", None) or []
            if not rows:
                raise HTTPException(status_code=500, detail="Failed to create production cycle")
            row = rows[0]
        except HTTPException:
            raise
        except Exception as e:
            if _is_table_missing_error(e, "production_cycles"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: production_cycles table missing",
                ) from e
            if "idx_production_cycles_active_unique" in str(e):
                raise HTTPException(status_code=409, detail="An active production cycle already exists") from e
            raise HTTPException(status_code=500, detail=f"Failed to create production cycle: {e}") from e

        self._insert_log(
            manuscript_id=manuscript_id,
            from_status=None,
            to_status="draft",
            changed_by=user_id,
            comment="production cycle created",
            payload={
                "event_type": "production_cycle_created",
                "cycle_id": row.get("id"),
                "proof_due_at": row.get("proof_due_at"),
            },
        )

        return self._format_cycle(row, include_signed_url=False)

    def update_cycle_editors(
        self,
        *,
        manuscript_id: str,
        cycle_id: str,
        user_id: str,
        profile_roles: list[str] | None,
        request: UpdateProductionCycleEditorsRequest,
    ) -> dict[str, Any]:
        """
        更新 production cycle 的负责人/协作者列表（仅 ME/EIC/Admin）。
        """
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        if not roles.intersection({"admin", "managing_editor", "editor_in_chief"}):
            raise HTTPException(status_code=403, detail="Forbidden")

        cycle = self._get_cycle(manuscript_id=manuscript_id, cycle_id=cycle_id)
        self._ensure_editor_access(manuscript=manuscript, user_id=user_id, roles=roles, cycle=cycle, purpose="write")

        now = _utc_now_iso()
        patch: dict[str, Any] = {"updated_at": now}

        # 1) layout editor
        next_layout_id = str(cycle.get("layout_editor_id") or "").strip()
        if request.layout_editor_id is not None:
            next_layout_id = str(request.layout_editor_id)
            next_layout_roles = self._get_profile_roles(next_layout_id)
            if not next_layout_roles:
                raise HTTPException(status_code=422, detail="layout_editor_id user not found")
            if not next_layout_roles.intersection({"production_editor", "admin"}):
                raise HTTPException(status_code=422, detail="layout_editor_id must have production_editor role")
            patch["layout_editor_id"] = next_layout_id

        # 2) collaborators
        if request.collaborator_editor_ids is not None:
            raw_collabs = [str(uid) for uid in (request.collaborator_editor_ids or [])]
            collab_ids: list[str] = []
            seen: set[str] = set()
            for cid in raw_collabs:
                c = str(cid or "").strip()
                if not c or c == next_layout_id or c in seen:
                    continue
                seen.add(c)
                collab_ids.append(c)
            if len(collab_ids) > 20:
                raise HTTPException(status_code=422, detail="Too many collaborator editors (max 20)")
            for cid in collab_ids:
                r = self._get_profile_roles(cid)
                if not r:
                    raise HTTPException(status_code=422, detail="collaborator_editor_ids contains unknown user")
                if not r.intersection({"production_editor", "admin"}):
                    raise HTTPException(status_code=422, detail="collaborator_editor_ids must have production_editor role")
            patch["collaborator_editor_ids"] = collab_ids
        else:
            # 若只改 layout editor，也要确保协作者列表不包含新的 layout editor
            existing = self._normalize_uuid_list(cycle.get("collaborator_editor_ids"))
            cleaned = [cid for cid in existing if str(cid).strip() and str(cid) != next_layout_id]
            if cleaned != existing:
                patch["collaborator_editor_ids"] = cleaned

        # No-op guard: 仅 updated_at 则不写
        if set(patch.keys()) == {"updated_at"}:
            return self._format_cycle(cycle, include_signed_url=False)

        try:
            resp = (
                self.client.table("production_cycles")
                .update(patch)
                .eq("id", cycle_id)
                .eq("manuscript_id", manuscript_id)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
            if not rows:
                raise HTTPException(status_code=500, detail="Failed to update production cycle editors")
            row = rows[0]
        except HTTPException:
            raise
        except Exception as e:
            if _is_missing_column_error(e, "collaborator_editor_ids"):
                raise HTTPException(status_code=500, detail="DB not migrated: collaborator_editor_ids column missing") from e
            raise HTTPException(status_code=500, detail=f"Failed to update production cycle editors: {e}") from e

        self._insert_log(
            manuscript_id=manuscript_id,
            from_status=str(cycle.get("status") or ""),
            to_status=str(row.get("status") or ""),
            changed_by=user_id,
            comment="production cycle editors updated",
            payload={
                "event_type": "production_cycle_editors_updated",
                "cycle_id": cycle_id,
                "layout_editor_id": row.get("layout_editor_id"),
                "collaborator_editor_ids": self._normalize_uuid_list(row.get("collaborator_editor_ids")),
            },
        )

        return self._format_cycle(row, include_signed_url=False)

    def list_my_queue(
        self,
        *,
        user_id: str,
        profile_roles: list[str] | None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Production Editor Queue:
        - 返回 layout_editor_id == 当前用户 或 collaborator_editor_ids 包含当前用户，且处于活跃状态的 production cycles。
        - 返回值用于前端 /editor/production 列表页。
        """
        roles = self._roles(profile_roles)
        if not roles.intersection({"admin", "production_editor"}):
            raise HTTPException(status_code=403, detail="Forbidden")

        safe_limit = max(1, min(int(limit or 50), 200))
        active_statuses = sorted(ACTIVE_CYCLE_STATUSES)

        uid = str(user_id)
        cycles: list[dict[str, Any]] = []
        try:
            primary = (
                self.client.table("production_cycles")
                .select("id,manuscript_id,cycle_no,status,proof_due_at,updated_at,created_at")
                .eq("layout_editor_id", uid)
                .in_("status", active_statuses)
                .order("updated_at", desc=True)
                .limit(safe_limit)
                .execute()
            )
            cycles.extend(getattr(primary, "data", None) or [])
        except Exception as e:
            if _is_table_missing_error(e, "production_cycles"):
                raise HTTPException(status_code=500, detail="DB not migrated: production_cycles table missing") from e
            raise HTTPException(status_code=500, detail=f"Failed to list production queue: {e}") from e

        # 协作者队列：支持多个 production editor 协作同一轮次
        try:
            collab = (
                self.client.table("production_cycles")
                .select("id,manuscript_id,cycle_no,status,proof_due_at,updated_at,created_at")
                .contains("collaborator_editor_ids", [uid])
                .in_("status", active_statuses)
                .order("updated_at", desc=True)
                .limit(safe_limit)
                .execute()
            )
            cycles.extend(getattr(collab, "data", None) or [])
        except Exception:
            # 中文注释：部分老环境可能未迁移 collaborator_editor_ids；忽略协作者队列即可。
            pass

        # 去重 + 排序（updated_at 优先）
        uniq: dict[str, dict[str, Any]] = {}
        for row in cycles:
            cid = str(row.get("id") or "").strip()
            if not cid:
                continue
            uniq[cid] = row
        cycles = list(uniq.values())
        cycles.sort(
            key=lambda x: str(x.get("updated_at") or x.get("created_at") or ""),
            reverse=True,
        )
        cycles = cycles[:safe_limit]
        if not cycles:
            return []

        manuscript_ids = [str(c.get("manuscript_id") or "").strip() for c in cycles if str(c.get("manuscript_id") or "").strip()]
        manuscript_ids = list(dict.fromkeys(manuscript_ids))
        if not manuscript_ids:
            return []

        try:
            ms_resp = (
                self.client.table("manuscripts")
                .select("id,title,status,journal_id,journals(title,slug)")
                .in_("id", manuscript_ids)
                .execute()
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load manuscripts for production queue: {e}") from e

        ms_rows: list[dict[str, Any]] = getattr(ms_resp, "data", None) or []
        ms_map = {str(row.get("id") or ""): row for row in ms_rows if str(row.get("id") or "").strip()}

        out: list[dict[str, Any]] = []
        for cycle in cycles:
            mid = str(cycle.get("manuscript_id") or "").strip()
            ms = ms_map.get(mid) or {}
            journal_row = ms.get("journals") or None
            out.append(
                {
                    "manuscript": {
                        "id": mid,
                        "title": ms.get("title") or "Untitled",
                        "status": ms.get("status"),
                        "journal": {
                            "id": ms.get("journal_id"),
                            "title": (journal_row or {}).get("title"),
                            "slug": (journal_row or {}).get("slug"),
                        }
                        if ms.get("journal_id") or journal_row
                        else None,
                    },
                    "cycle": {
                        "id": cycle.get("id"),
                        "cycle_no": cycle.get("cycle_no"),
                        "status": cycle.get("status"),
                        "proof_due_at": cycle.get("proof_due_at"),
                        "updated_at": cycle.get("updated_at") or cycle.get("created_at"),
                    },
                    "action_url": f"/editor/production/{mid}",
                }
            )
        return out

    def upload_galley(
        self,
        *,
        manuscript_id: str,
        cycle_id: str,
        user_id: str,
        profile_roles: list[str] | None,
        filename: str,
        content: bytes,
        version_note: str,
        proof_due_at: datetime | None,
        content_type: str | None,
    ) -> dict[str, Any]:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)

        if not content:
            raise HTTPException(status_code=400, detail="Galley file is empty")
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Galley file too large (max 50MB)")
        if not str(filename or "").lower().endswith(".pdf"):
            raise HTTPException(status_code=422, detail="Only PDF galley files are supported")

        note = str(version_note or "").strip()
        if not note:
            raise HTTPException(status_code=422, detail="version_note is required")

        cycle = self._get_cycle(manuscript_id=manuscript_id, cycle_id=cycle_id)
        self._ensure_editor_access(
            manuscript=manuscript, user_id=user_id, roles=roles, cycle=cycle, purpose="write"
        )
        old_status = str(cycle.get("status") or "")
        if old_status not in {"draft", "in_layout_revision", "author_corrections_submitted"}:
            raise HTTPException(status_code=409, detail=f"Cannot upload galley in cycle status '{old_status}'")

        due = proof_due_at or None
        if due is not None and due <= _utc_now():
            raise HTTPException(status_code=422, detail="proof_due_at must be in the future")

        self._ensure_bucket("production-proofs", public=False)
        object_path = (
            f"production_cycles/{manuscript_id}/"
            f"cycle-{int(cycle.get('cycle_no') or 0)}/{uuid4()}_{_safe_filename(filename)}"
        )

        try:
            self.client.storage.from_("production-proofs").upload(
                object_path,
                content,
                {"content-type": content_type or "application/pdf"},
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload galley: {e}") from e

        now = _utc_now_iso()
        patch: dict[str, Any] = {
            "status": "awaiting_author",
            "galley_bucket": "production-proofs",
            "galley_path": object_path,
            "version_note": note,
            "updated_at": now,
        }
        if due is not None:
            patch["proof_due_at"] = due.isoformat()

        try:
            resp = (
                self.client.table("production_cycles")
                .update(patch)
                .eq("id", cycle_id)
                .eq("manuscript_id", manuscript_id)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
            if not rows:
                raise HTTPException(status_code=500, detail="Failed to update cycle after galley upload")
            row = rows[0]
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update cycle: {e}") from e

        self._insert_log(
            manuscript_id=manuscript_id,
            from_status=old_status,
            to_status="awaiting_author",
            changed_by=user_id,
            comment="galley uploaded",
            payload={
                "event_type": "galley_uploaded",
                "cycle_id": cycle_id,
                "galley_path": object_path,
                "version_note": note,
                "proof_due_at": row.get("proof_due_at"),
            },
        )

        self._notify(
            user_id=str(row.get("proofreader_author_id") or ""),
            manuscript_id=manuscript_id,
            title="Proofreading Required",
            content=f"New galley proof is ready for manuscript '{manuscript.get('title') or manuscript_id}'.",
            action_url=f"/proofreading/{manuscript_id}",
        )

        return self._format_cycle(row, include_signed_url=True)

    def get_galley_signed_url(
        self,
        *,
        manuscript_id: str,
        cycle_id: str,
        user_id: str,
        profile_roles: list[str] | None,
    ) -> str:
        manuscript = self._get_manuscript(manuscript_id)
        cycle = self._get_cycle(manuscript_id=manuscript_id, cycle_id=cycle_id)
        roles = self._roles(profile_roles)

        is_internal = roles.intersection({"admin", "managing_editor", "editor_in_chief", "production_editor"})
        if is_internal:
            self._ensure_editor_access(
                manuscript=manuscript, user_id=user_id, roles=roles, cycle=cycle, purpose="read"
            )
        else:
            self._ensure_author_or_internal_access(
                manuscript=manuscript,
                cycle=cycle,
                user_id=user_id,
                roles=roles,
            )

        bucket = str(cycle.get("galley_bucket") or "production-proofs")
        path = str(cycle.get("galley_path") or "")
        if not path:
            raise HTTPException(status_code=404, detail="Galley proof not uploaded")
        signed = self._signed_url(bucket, path)
        if not signed:
            raise HTTPException(status_code=500, detail="Failed to sign galley URL")
        return signed

    def get_author_proofreading_context(
        self,
        *,
        manuscript_id: str,
        user_id: str,
        profile_roles: list[str] | None,
    ) -> dict[str, Any]:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)

        # 作者侧读取“当前可见”轮次：
        # - awaiting_author: 可提交
        # - author_corrections_submitted / author_confirmed: 提交后回看（只读）
        try:
            resp = (
                self.client.table("production_cycles")
                .select(
                    "id,manuscript_id,cycle_no,status,layout_editor_id,proofreader_author_id,"
                    "galley_bucket,galley_path,version_note,proof_due_at,approved_by,approved_at,created_at,updated_at"
                )
                .eq("manuscript_id", manuscript_id)
                .in_("status", sorted(AUTHOR_CONTEXT_VISIBLE_STATUSES))
                .order("cycle_no", desc=True)
                .order("updated_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
        except Exception as e:
            if _is_table_missing_error(e, "production_cycles"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: production_cycles table missing",
                ) from e
            raise

        if not rows:
            raise HTTPException(status_code=404, detail="No proofreading task available")

        cycle = rows[0]
        self._ensure_author_or_internal_access(
            manuscript=manuscript,
            cycle=cycle,
            user_id=user_id,
            roles=roles,
        )

        cycle_status = str(cycle.get("status") or "")
        can_act_on_cycle = cycle_status == "awaiting_author"
        cycle_data = self._format_cycle(cycle, include_signed_url=True)
        latest = cycle_data.get("latest_response")
        active_latest = latest if self._is_response_current_for_cycle(cycle=cycle, response=latest) else None
        cycle_data["latest_response"] = active_latest
        read_only = (not can_act_on_cycle) or (active_latest is not None)

        due_raw = cycle.get("proof_due_at")
        due_at: datetime | None = None
        if isinstance(due_raw, datetime):
            due_at = due_raw
        elif isinstance(due_raw, str) and due_raw:
            try:
                due_at = datetime.fromisoformat(due_raw.replace("Z", "+00:00"))
            except Exception:
                due_at = None

        if due_at and due_at < _utc_now():
            read_only = True

        return {
            "manuscript": {
                "id": manuscript.get("id"),
                "title": manuscript.get("title") or "Untitled",
                "status": manuscript.get("status"),
            },
            "cycle": cycle_data,
            "can_submit": can_act_on_cycle and not read_only,
            "is_read_only": read_only,
        }

    def submit_proofreading(
        self,
        *,
        manuscript_id: str,
        cycle_id: str,
        user_id: str,
        profile_roles: list[str] | None,
        request: SubmitProofreadingRequest,
    ) -> dict[str, Any]:
        manuscript = self._get_manuscript(manuscript_id)
        cycle = self._get_cycle(manuscript_id=manuscript_id, cycle_id=cycle_id)
        roles = self._roles(profile_roles)

        is_internal = self._ensure_author_or_internal_access(
            manuscript=manuscript,
            cycle=cycle,
            user_id=user_id,
            roles=roles,
        )
        if is_internal:
            raise HTTPException(status_code=403, detail="Internal users cannot submit author proofreading")

        if str(cycle.get("status") or "") != "awaiting_author":
            raise HTTPException(status_code=409, detail="Cycle is not awaiting author response")

        existing = self._get_latest_response(str(cycle.get("id") or ""))
        existing_is_current = self._is_response_current_for_cycle(cycle=cycle, response=existing)
        if existing_is_current:
            raise HTTPException(status_code=409, detail="Proofreading response already submitted")

        due_raw = cycle.get("proof_due_at")
        due_at: datetime | None = None
        if isinstance(due_raw, datetime):
            due_at = due_raw
        elif isinstance(due_raw, str) and due_raw:
            try:
                due_at = datetime.fromisoformat(due_raw.replace("Z", "+00:00"))
            except Exception:
                due_at = None

        now = _utc_now()
        if due_at and now > due_at:
            raise HTTPException(status_code=422, detail="Proofreading deadline has passed")

        decision = str(request.decision)
        new_status = "author_confirmed" if decision == "confirm_clean" else "author_corrections_submitted"

        submitted_at = now.isoformat()
        response_reused = False
        try:
            if existing and not existing_is_current and str(existing.get("id") or "").strip():
                response_reused = True
                response_id = str(existing.get("id") or "").strip()
                resp = (
                    self.client.table("production_proofreading_responses")
                    .update(
                        {
                            "author_id": user_id,
                            "decision": decision,
                            "summary": request.summary,
                            "submitted_at": submitted_at,
                            "is_late": bool(due_at and now > due_at),
                        }
                    )
                    .eq("id", response_id)
                    .eq("cycle_id", cycle_id)
                    .eq("manuscript_id", manuscript_id)
                    .execute()
                )
                rows = getattr(resp, "data", None) or []
                if not rows:
                    raise HTTPException(status_code=500, detail="Failed to update proofreading response")
                response_row = rows[0]
            else:
                response_payload = {
                    "cycle_id": cycle_id,
                    "manuscript_id": manuscript_id,
                    "author_id": user_id,
                    "decision": decision,
                    "summary": request.summary,
                    "submitted_at": submitted_at,
                    "is_late": bool(due_at and now > due_at),
                    "created_at": submitted_at,
                }
                resp = self.client.table("production_proofreading_responses").insert(response_payload).execute()
                rows = getattr(resp, "data", None) or []
                if not rows:
                    raise HTTPException(status_code=500, detail="Failed to save proofreading response")
                response_row = rows[0]
        except HTTPException:
            raise
        except Exception as e:
            if _is_table_missing_error(e, "production_proofreading_responses"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: production_proofreading_responses table missing",
                ) from e
            raise HTTPException(status_code=500, detail=f"Failed to save proofreading response: {e}") from e

        response_id = str(response_row.get("id") or "").strip()
        try:
            if response_id:
                self.client.table("production_correction_items").delete().eq("response_id", response_id).execute()
        except Exception as e:
            if _is_table_missing_error(e, "production_correction_items"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: production_correction_items table missing",
                ) from e
            raise HTTPException(status_code=500, detail=f"Failed to reset correction items: {e}") from e

        if decision == "submit_corrections":
            items = []
            for idx, item in enumerate(request.corrections):
                items.append(
                    {
                        "response_id": response_id,
                        "line_ref": item.line_ref,
                        "original_text": item.original_text,
                        "suggested_text": item.suggested_text,
                        "reason": item.reason,
                        "sort_order": idx,
                    }
                )
            try:
                if items:
                    self.client.table("production_correction_items").insert(items).execute()
            except Exception as e:
                if _is_table_missing_error(e, "production_correction_items"):
                    raise HTTPException(
                        status_code=500,
                        detail="DB not migrated: production_correction_items table missing",
                    ) from e
                raise HTTPException(status_code=500, detail=f"Failed to save correction items: {e}") from e

        try:
            self.client.table("production_cycles").update(
                {
                    "status": new_status,
                    "updated_at": submitted_at,
                }
            ).eq("id", cycle_id).eq("manuscript_id", manuscript_id).execute()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update cycle status: {e}") from e

        self._insert_log(
            manuscript_id=manuscript_id,
            from_status="awaiting_author",
            to_status=new_status,
            changed_by=user_id,
            comment="proofreading submitted",
            payload={
                "event_type": "proofreading_submitted",
                "cycle_id": cycle_id,
                "decision": decision,
                "response_id": response_row.get("id"),
                "response_reused": response_reused,
            },
        )

        if decision == "submit_corrections":
            recipients: list[str] = []
            layout_id = str(cycle.get("layout_editor_id") or "").strip()
            if layout_id:
                recipients.append(layout_id)
            recipients.extend(self._normalize_uuid_list(cycle.get("collaborator_editor_ids")))
            if not recipients:
                fallback = str(manuscript.get("editor_id") or "").strip()
                if fallback:
                    recipients.append(fallback)
            recipients = list(dict.fromkeys([r for r in recipients if str(r).strip()]))
            for uid in recipients:
                self._notify(
                    user_id=uid,
                    manuscript_id=manuscript_id,
                    title="Proof Corrections Submitted",
                    content=f"Author submitted corrections for manuscript '{manuscript.get('title') or manuscript_id}'.",
                    action_url=f"/editor/production/{manuscript_id}",
                )
        else:
            self._notify(
                user_id=str(manuscript.get("editor_id") or manuscript.get("owner_id") or ""),
                manuscript_id=manuscript_id,
                title="Proofreading Confirmed",
                content=f"Author confirmed galley proof for manuscript '{manuscript.get('title') or manuscript_id}'.",
                action_url=f"/editor/production/{manuscript_id}",
            )

        return {
            "response_id": response_row.get("id"),
            "cycle_id": cycle_id,
            "decision": decision,
            "submitted_at": response_row.get("submitted_at") or submitted_at,
        }

    def approve_cycle(
        self,
        *,
        manuscript_id: str,
        cycle_id: str,
        user_id: str,
        profile_roles: list[str] | None,
    ) -> dict[str, Any]:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        cycle = self._get_cycle(manuscript_id=manuscript_id, cycle_id=cycle_id)
        self._ensure_editor_access(
            manuscript=manuscript, user_id=user_id, roles=roles, cycle=cycle, purpose="write"
        )
        if str(cycle.get("status") or "") != "author_confirmed":
            raise HTTPException(
                status_code=422,
                detail="Cycle can be approved only after author_confirmed",
            )

        galley_path = str(cycle.get("galley_path") or "").strip()
        if not galley_path:
            raise HTTPException(status_code=422, detail="Cannot approve cycle without galley proof")

        now = _utc_now_iso()
        try:
            resp = (
                self.client.table("production_cycles")
                .update(
                    {
                        "status": "approved_for_publish",
                        "approved_by": user_id,
                        "approved_at": now,
                        "updated_at": now,
                    }
                )
                .eq("id", cycle_id)
                .eq("manuscript_id", manuscript_id)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
            if not rows:
                raise HTTPException(status_code=500, detail="Failed to approve cycle")
            row = rows[0]
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to approve cycle: {e}") from e

        # 与现有 publish gate 对齐：尽量同步 final_pdf_path（若列缺失按环境降级）
        try:
            self.client.table("manuscripts").update({"final_pdf_path": galley_path}).eq(
                "id", manuscript_id
            ).execute()
        except Exception as e:
            if _is_missing_column_error(e, "final_pdf_path"):
                if _is_truthy_env("PRODUCTION_GATE_ENABLED", "0"):
                    raise HTTPException(
                        status_code=500,
                        detail="Database schema missing final_pdf_path while PRODUCTION_GATE_ENABLED=1",
                    ) from e
            else:
                raise

        self._insert_log(
            manuscript_id=manuscript_id,
            from_status="author_confirmed",
            to_status="approved_for_publish",
            changed_by=user_id,
            comment="production cycle approved",
            payload={
                "event_type": "production_approved",
                "cycle_id": cycle_id,
                "galley_path": galley_path,
            },
        )

        self._notify(
            user_id=str(manuscript.get("author_id") or ""),
            manuscript_id=manuscript_id,
            title="Production Approved",
            content=f"Your proofreading cycle was approved for publication: '{manuscript.get('title') or manuscript_id}'.",
            action_url=f"/dashboard",
        )

        return {
            "cycle_id": cycle_id,
            "status": "approved_for_publish",
            "approved_at": row.get("approved_at") or now,
            "approved_by": str(row.get("approved_by") or user_id),
        }

