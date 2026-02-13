from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from fastapi import HTTPException

from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.role_matrix import ADMIN_ROLE
from app.lib.api_client import supabase_admin
from app.models.manuscript import ManuscriptStatus, normalize_status
from app.models.production_workspace import (
    CreateProductionCycleRequest,
    SubmitProofreadingRequest,
)
from app.services.notification_service import NotificationService


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


class ProductionWorkspaceService:
    """
    Feature 042: 录用后生产协作工作间。

    中文注释:
    - 管理 production cycle 生命周期。
    - 处理作者校对提交（confirm/corrections）。
    - 提供发布前核准门禁数据。
    """

    def __init__(self) -> None:
        self.client = supabase_admin
        self.notification = NotificationService()

    def _roles(self, profile_roles: list[str] | None) -> set[str]:
        return {str(r).strip().lower() for r in (profile_roles or []) if str(r).strip()}

    def _ensure_bucket(self, bucket: str, *, public: bool = False) -> None:
        storage = getattr(self.client, "storage", None)
        if storage is None or not hasattr(storage, "get_bucket") or not hasattr(storage, "create_bucket"):
            return
        try:
            storage.get_bucket(bucket)
        except Exception:
            try:
                storage.create_bucket(bucket, options={"public": bool(public)})
            except Exception:
                return

    def _signed_url(self, bucket: str, path: str, expires_in: int = 60 * 10) -> str | None:
        p = str(path or "").strip()
        if not p:
            return None
        try:
            signed = self.client.storage.from_(bucket).create_signed_url(p, expires_in)
            return (signed or {}).get("signedUrl") or (signed or {}).get("signedURL")
        except Exception:
            return None

    def _get_manuscript(self, manuscript_id: str) -> dict[str, Any]:
        try:
            try:
                resp = (
                    self.client.table("manuscripts")
                    .select(
                        "id,title,status,author_id,editor_id,owner_id,assistant_editor_id,file_path,final_pdf_path,updated_at"
                    )
                    .eq("id", manuscript_id)
                    .single()
                    .execute()
                )
            except Exception as first_err:
                if _is_missing_column_error(first_err, "final_pdf_path"):
                    resp = (
                        self.client.table("manuscripts")
                        .select(
                            "id,title,status,author_id,editor_id,owner_id,assistant_editor_id,file_path,updated_at"
                        )
                        .eq("id", manuscript_id)
                        .single()
                        .execute()
                    )
                else:
                    raise
        except Exception as e:
            raise HTTPException(status_code=404, detail="Manuscript not found") from e

        row = getattr(resp, "data", None) or None
        if not row:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        return row

    def _ensure_editor_access(
        self,
        *,
        manuscript: dict[str, Any],
        user_id: str,
        roles: set[str],
        cycle: dict[str, Any] | None = None,
        purpose: Literal["read", "write"] = "read",
    ) -> None:
        # Admin 永远放行；其余角色按“期刊 scope / 分配”组合判定。
        if ADMIN_ROLE in roles:
            return

        uid = str(user_id or "").strip()
        manuscript_id = str(manuscript.get("id") or "").strip()

        # 中文注释:
        # - 一个用户可能同时拥有多个角色（例如 assistant_editor + managing_editor）。
        # - 访问控制应按“任一角色满足即可放行”，避免因为缺少 journal scope 把已被分配的 AE 挡掉。
        # - 但“写操作”必须严格按角色语义执行，避免 ME/EIC 缺 scope 时被 AE 分配兜底放行造成越权。

        # 1) Production Editor: 仅允许访问“分配给自己”的 production cycle（layout_editor_id）。
        #    说明：write/read 都允许，但必须基于 cycle 的真实分配关系。
        if "production_editor" in roles and cycle is not None:
            layout_editor_id = str(cycle.get("layout_editor_id") or "").strip()
            if layout_editor_id and layout_editor_id == uid:
                return

        # 2) 写操作：ME/EIC 必须通过 journal scope；其余角色一律不允许写入 production。
        if purpose == "write":
            if roles.intersection({"managing_editor", "editor_in_chief"}):
                ensure_manuscript_scope_access(
                    manuscript_id=manuscript_id,
                    user_id=uid,
                    roles=list(roles),
                    allow_admin_bypass=True,
                )
                return
            raise HTTPException(status_code=403, detail="Forbidden")

        # 3) 读操作：ME/EIC 尝试按 journal scope 放行；失败时允许 AE 以“分配稿件”兜底读取。
        if roles.intersection({"managing_editor", "editor_in_chief"}):
            try:
                ensure_manuscript_scope_access(
                    manuscript_id=manuscript_id,
                    user_id=uid,
                    roles=list(roles),
                    allow_admin_bypass=True,
                )
                return
            except HTTPException:
                pass

        # 4) Assistant Editor: 仅允许访问“分配给自己”的稿件（读）。
        if "assistant_editor" in roles:
            assigned_ae = str(manuscript.get("assistant_editor_id") or "").strip()
            if assigned_ae and assigned_ae == uid:
                return

        raise HTTPException(status_code=403, detail="Forbidden")

    def _ensure_author_or_internal_access(
        self,
        *,
        manuscript: dict[str, Any],
        cycle: dict[str, Any],
        user_id: str,
        roles: set[str],
    ) -> bool:
        if roles.intersection({"admin", "managing_editor", "editor_in_chief"}):
            return True

        proofreader_id = str(cycle.get("proofreader_author_id") or "").strip()
        if proofreader_id and proofreader_id == str(user_id):
            return False
        if str(manuscript.get("author_id") or "").strip() == str(user_id):
            return False
        raise HTTPException(status_code=403, detail="Forbidden")

    def _get_cycles(self, manuscript_id: str) -> list[dict[str, Any]]:
        try:
            resp = (
                self.client.table("production_cycles")
                .select(
                    "id,manuscript_id,cycle_no,status,layout_editor_id,proofreader_author_id,"
                    "galley_bucket,galley_path,version_note,proof_due_at,approved_by,approved_at,created_at,updated_at"
                )
                .eq("manuscript_id", manuscript_id)
                .order("cycle_no", desc=True)
                .execute()
            )
            return getattr(resp, "data", None) or []
        except Exception as e:
            if _is_table_missing_error(e, "production_cycles"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: production_cycles table missing",
                ) from e
            raise

    def _get_cycle(self, *, manuscript_id: str, cycle_id: str) -> dict[str, Any]:
        try:
            resp = (
                self.client.table("production_cycles")
                .select(
                    "id,manuscript_id,cycle_no,status,layout_editor_id,proofreader_author_id,"
                    "galley_bucket,galley_path,version_note,proof_due_at,approved_by,approved_at,created_at,updated_at"
                )
                .eq("manuscript_id", manuscript_id)
                .eq("id", cycle_id)
                .single()
                .execute()
            )
            row = getattr(resp, "data", None) or None
        except Exception as e:
            if _is_table_missing_error(e, "production_cycles"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: production_cycles table missing",
                ) from e
            raise HTTPException(status_code=404, detail="Production cycle not found") from e

        if not row:
            raise HTTPException(status_code=404, detail="Production cycle not found")
        return row

    def _get_latest_response(self, cycle_id: str) -> dict[str, Any] | None:
        try:
            resp = (
                self.client.table("production_proofreading_responses")
                .select("id,cycle_id,manuscript_id,author_id,decision,summary,submitted_at,is_late,created_at")
                .eq("cycle_id", cycle_id)
                .order("submitted_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
        except Exception as e:
            if _is_table_missing_error(e, "production_proofreading_responses"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: production_proofreading_responses table missing",
                ) from e
            raise

        if not rows:
            return None

        row = rows[0]
        if str(row.get("decision") or "") == "submit_corrections":
            try:
                c = (
                    self.client.table("production_correction_items")
                    .select("id,line_ref,original_text,suggested_text,reason,sort_order")
                    .eq("response_id", row.get("id"))
                    .order("sort_order", desc=False)
                    .execute()
                )
                row["corrections"] = getattr(c, "data", None) or []
            except Exception:
                row["corrections"] = []
        else:
            row["corrections"] = []
        return row

    def _format_cycle(self, row: dict[str, Any], *, include_signed_url: bool) -> dict[str, Any]:
        bucket = str(row.get("galley_bucket") or "").strip()
        path = str(row.get("galley_path") or "").strip()
        return {
            "id": row.get("id"),
            "manuscript_id": row.get("manuscript_id"),
            "cycle_no": row.get("cycle_no"),
            "status": row.get("status"),
            "layout_editor_id": row.get("layout_editor_id"),
            "proofreader_author_id": row.get("proofreader_author_id"),
            "galley_bucket": bucket or None,
            "galley_path": path or None,
            "galley_signed_url": self._signed_url(bucket, path) if include_signed_url and bucket and path else None,
            "version_note": row.get("version_note"),
            "proof_due_at": row.get("proof_due_at"),
            "approved_by": row.get("approved_by"),
            "approved_at": row.get("approved_at"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "latest_response": self._get_latest_response(str(row.get("id") or "")),
        }

    def _next_cycle_no(self, manuscript_id: str) -> int:
        cycles = self._get_cycles(manuscript_id)
        if not cycles:
            return 1
        try:
            return int(cycles[0].get("cycle_no") or 0) + 1
        except Exception:
            return 1

    def _insert_log(
        self,
        *,
        manuscript_id: str,
        from_status: str | None,
        to_status: str,
        changed_by: str,
        comment: str,
        payload: dict[str, Any],
    ) -> None:
        now = _utc_now_iso()
        base_row = {
            "manuscript_id": manuscript_id,
            "from_status": from_status,
            "to_status": to_status,
            "comment": comment,
            "changed_by": changed_by,
            "created_at": now,
        }
        rows: list[dict[str, Any]] = []

        # 1) 优先写入带 payload 的版本（审计事件完整）。
        row_with_payload = dict(base_row)
        row_with_payload["payload"] = payload
        rows.append(row_with_payload)

        # 2) 兼容：某些云端/老 schema 可能缺 payload 列（写入降级）。
        rows.append(dict(base_row))

        # 3) 兼容：changed_by 外键指向 auth.users，在测试/种子数据下可能不存在。
        #    用 changed_by=None 写入，同时把原值放进 payload 以便追溯。
        row_no_fk = dict(base_row)
        row_no_fk["changed_by"] = None
        row_no_fk["payload"] = {**payload, "changed_by_raw": changed_by}
        rows.append(row_no_fk)

        # 4) 最小兜底：避免所有 insert 都失败导致无审计。
        rows.append(
            {
                "manuscript_id": manuscript_id,
                "from_status": from_status,
                "to_status": to_status,
                "comment": comment,
                "changed_by": None,
                "created_at": now,
            }
        )

        for row in rows:
            try:
                self.client.table("status_transition_logs").insert(row).execute()
                return
            except Exception as e:
                # 缺 payload 列时，尝试去掉 payload 再写一次
                if "payload" in row and _is_missing_column_error(e, "payload"):
                    fallback = dict(row)
                    fallback.pop("payload", None)
                    try:
                        self.client.table("status_transition_logs").insert(fallback).execute()
                        return
                    except Exception:
                        pass
                continue
        return

    def _notify(self, *, user_id: str | None, manuscript_id: str, title: str, content: str, action_url: str) -> None:
        uid = str(user_id or "").strip()
        if not uid:
            return
        self.notification.create_notification(
            user_id=uid,
            manuscript_id=manuscript_id,
            action_url=action_url,
            type="system",
            title=title,
            content=content,
        )

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
        self._ensure_editor_access(
            manuscript=manuscript, user_id=user_id, roles=roles, cycle=active, purpose="read"
        )

        manuscript_status = normalize_status(str(manuscript.get("status") or "")) or ""
        can_manage_production = bool(roles.intersection({"admin", "managing_editor", "editor_in_chief"})) or bool(
            "production_editor" in roles
            and active
            and str(active.get("layout_editor_id") or "").strip() == str(user_id)
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
            "active_cycle": self._format_cycle(active, include_signed_url=True) if active else None,
            "cycle_history": [self._format_cycle(c, include_signed_url=False) for c in cycles],
            "permissions": {
                "can_create_cycle": can_create,
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

        now = _utc_now_iso()
        payload = {
            "manuscript_id": manuscript_id,
            "cycle_no": self._next_cycle_no(manuscript_id),
            "status": "draft",
            "layout_editor_id": str(request.layout_editor_id),
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

    def list_my_queue(
        self,
        *,
        user_id: str,
        profile_roles: list[str] | None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Production Editor Queue:
        - 仅返回 layout_editor_id == 当前用户 且处于活跃状态的 production cycles。
        - 返回值用于前端 /editor/production 列表页。
        """
        roles = self._roles(profile_roles)
        if not roles.intersection({"admin", "production_editor"}):
            raise HTTPException(status_code=403, detail="Forbidden")

        safe_limit = max(1, min(int(limit or 50), 200))
        active_statuses = sorted(ACTIVE_CYCLE_STATUSES)

        try:
            resp = (
                self.client.table("production_cycles")
                .select("id,manuscript_id,cycle_no,status,proof_due_at,updated_at,created_at")
                .eq("layout_editor_id", str(user_id))
                .in_("status", active_statuses)
                .order("updated_at", desc=True)
                .limit(safe_limit)
                .execute()
            )
        except Exception as e:
            if _is_table_missing_error(e, "production_cycles"):
                raise HTTPException(status_code=500, detail="DB not migrated: production_cycles table missing") from e
            raise HTTPException(status_code=500, detail=f"Failed to list production queue: {e}") from e

        cycles: list[dict[str, Any]] = getattr(resp, "data", None) or []
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
        latest = self._get_latest_response(str(cycle.get("id") or ""))
        read_only = (not can_act_on_cycle) or (latest is not None)

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
            "cycle": self._format_cycle(cycle, include_signed_url=True),
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
        if existing:
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
        try:
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

        if decision == "submit_corrections":
            items = []
            for idx, item in enumerate(request.corrections):
                items.append(
                    {
                        "response_id": response_row.get("id"),
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
            },
        )

        if decision == "submit_corrections":
            self._notify(
                user_id=str(cycle.get("layout_editor_id") or manuscript.get("editor_id") or ""),
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

    def assert_publish_gate_ready(self, *, manuscript_id: str) -> dict[str, Any] | None:
        """
        发布前核准门禁：
        - 严格模式（PRODUCTION_CYCLE_STRICT=1）下，必须存在 approved_for_publish 轮次。
        - 非严格模式下，若没有任何生产轮次则降级放行（兼容历史数据）。
        """
        strict = _is_truthy_env("PRODUCTION_CYCLE_STRICT", "0")

        try:
            resp = (
                self.client.table("production_cycles")
                .select("id,manuscript_id,cycle_no,status,galley_path,approved_at")
                .eq("manuscript_id", manuscript_id)
                .order("cycle_no", desc=True)
                .limit(1)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
        except Exception as e:
            if _is_table_missing_error(e, "production_cycles"):
                return None
            raise HTTPException(status_code=500, detail=f"Failed to validate production cycle gate: {e}") from e

        if not rows:
            if strict:
                raise HTTPException(status_code=403, detail="Production approval required before publish")
            return None

        latest = rows[0]
        if str(latest.get("status") or "") != "approved_for_publish":
            raise HTTPException(status_code=403, detail="Latest production cycle is not approved for publish")
        if not str(latest.get("galley_path") or "").strip():
            raise HTTPException(status_code=403, detail="Approved production cycle is missing galley proof")
        return latest
