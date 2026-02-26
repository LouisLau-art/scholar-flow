from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.models.manuscript import normalize_status
from app.models.production_workspace import (
    CreateProductionCycleRequest,
    UpdateProductionCycleEditorsRequest,
)
from app.services.production_workspace_service_workflow_common import (
    ACTIVE_CYCLE_STATUSES,
    POST_ACCEPTANCE_ALLOWED,
    is_missing_column_error,
    is_table_missing_error,
    safe_filename,
    utc_now,
    utc_now_iso,
)

_PRODUCTION_EDITOR_ROLES = {"production_editor", "admin"}
_MANAGER_ROLES = {"admin", "managing_editor", "editor_in_chief"}
_UPLOAD_ALLOWED_STATUSES = {"draft", "in_layout_revision", "author_corrections_submitted"}


def _normalize_collaborators(
    *,
    raw_ids: list[str],
    layout_editor_id: str,
) -> list[str]:
    collab_ids: list[str] = []
    seen: set[str] = set()
    for raw_id in raw_ids:
        value = str(raw_id or "").strip()
        if not value or value == layout_editor_id or value in seen:
            continue
        seen.add(value)
        collab_ids.append(value)
    return collab_ids


def _validate_production_editor_roles(*, service, user_ids: list[str]) -> None:
    for user_id in user_ids:
        roles = service._get_profile_roles(user_id)
        if not roles:
            raise HTTPException(status_code=422, detail="collaborator_editor_ids contains unknown user")
        if not roles.intersection(_PRODUCTION_EDITOR_ROLES):
            raise HTTPException(status_code=422, detail="collaborator_editor_ids must have production_editor role")


class ProductionWorkspaceWorkflowCycleWritesMixin:
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
        if request.proof_due_at <= utc_now():
            raise HTTPException(status_code=422, detail="proof_due_at must be in the future")

        active = next(
            (row for row in self._get_cycles(manuscript_id) if str(row.get("status") or "") in ACTIVE_CYCLE_STATUSES),
            None,
        )
        if active:
            raise HTTPException(status_code=409, detail="An active production cycle already exists")

        manuscript_author = str(manuscript.get("author_id") or "").strip()
        if manuscript_author and manuscript_author != str(request.proofreader_author_id):
            raise HTTPException(
                status_code=422,
                detail="proofreader_author_id must match manuscript author_id in MVP",
            )

        layout_editor_id = str(request.layout_editor_id)
        layout_roles = self._get_profile_roles(layout_editor_id)
        if not layout_roles:
            raise HTTPException(status_code=422, detail="layout_editor_id user not found")
        if not layout_roles.intersection(_PRODUCTION_EDITOR_ROLES):
            raise HTTPException(status_code=422, detail="layout_editor_id must have production_editor role")

        collab_ids = _normalize_collaborators(
            raw_ids=[str(uid) for uid in (request.collaborator_editor_ids or [])],
            layout_editor_id=layout_editor_id,
        )
        if len(collab_ids) > 20:
            raise HTTPException(status_code=422, detail="Too many collaborator editors (max 20)")
        _validate_production_editor_roles(service=self, user_ids=collab_ids)

        now = utc_now_iso()
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
        except Exception as exc:
            if is_table_missing_error(exc, "production_cycles"):
                raise HTTPException(status_code=500, detail="DB not migrated: production_cycles table missing") from exc
            if "idx_production_cycles_active_unique" in str(exc):
                raise HTTPException(status_code=409, detail="An active production cycle already exists") from exc
            raise HTTPException(status_code=500, detail=f"Failed to create production cycle: {exc}") from exc

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
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        if not roles.intersection(_MANAGER_ROLES):
            raise HTTPException(status_code=403, detail="Forbidden")

        cycle = self._get_cycle(manuscript_id=manuscript_id, cycle_id=cycle_id)
        self._ensure_editor_access(
            manuscript=manuscript,
            user_id=user_id,
            roles=roles,
            cycle=cycle,
            purpose="write",
        )

        patch: dict[str, Any] = {"updated_at": utc_now_iso()}
        next_layout_id = str(cycle.get("layout_editor_id") or "").strip()
        if request.layout_editor_id is not None:
            next_layout_id = str(request.layout_editor_id)
            next_layout_roles = self._get_profile_roles(next_layout_id)
            if not next_layout_roles:
                raise HTTPException(status_code=422, detail="layout_editor_id user not found")
            if not next_layout_roles.intersection(_PRODUCTION_EDITOR_ROLES):
                raise HTTPException(status_code=422, detail="layout_editor_id must have production_editor role")
            patch["layout_editor_id"] = next_layout_id

        if request.collaborator_editor_ids is not None:
            collab_ids = _normalize_collaborators(
                raw_ids=[str(uid) for uid in (request.collaborator_editor_ids or [])],
                layout_editor_id=next_layout_id,
            )
            if len(collab_ids) > 20:
                raise HTTPException(status_code=422, detail="Too many collaborator editors (max 20)")
            _validate_production_editor_roles(service=self, user_ids=collab_ids)
            patch["collaborator_editor_ids"] = collab_ids
        else:
            existing = self._normalize_uuid_list(cycle.get("collaborator_editor_ids"))
            cleaned = [cid for cid in existing if str(cid).strip() and str(cid) != next_layout_id]
            if cleaned != existing:
                patch["collaborator_editor_ids"] = cleaned

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
        except Exception as exc:
            if is_missing_column_error(exc, "collaborator_editor_ids"):
                raise HTTPException(status_code=500, detail="DB not migrated: collaborator_editor_ids column missing") from exc
            raise HTTPException(status_code=500, detail=f"Failed to update production cycle editors: {exc}") from exc

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
            manuscript=manuscript,
            user_id=user_id,
            roles=roles,
            cycle=cycle,
            purpose="write",
        )
        old_status = str(cycle.get("status") or "")
        if old_status not in _UPLOAD_ALLOWED_STATUSES:
            raise HTTPException(status_code=409, detail=f"Cannot upload galley in cycle status '{old_status}'")

        due = proof_due_at or None
        if due is not None and due <= utc_now():
            raise HTTPException(status_code=422, detail="proof_due_at must be in the future")

        self._ensure_bucket("production-proofs", public=False)
        object_path = (
            f"production_cycles/{manuscript_id}/"
            f"cycle-{int(cycle.get('cycle_no') or 0)}/{uuid4()}_{safe_filename(filename)}"
        )
        try:
            self.client.storage.from_("production-proofs").upload(
                object_path,
                content,
                {"content-type": content_type or "application/pdf"},
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to upload galley: {exc}") from exc

        patch: dict[str, Any] = {
            "status": "awaiting_author",
            "galley_bucket": "production-proofs",
            "galley_path": object_path,
            "version_note": note,
            "updated_at": utc_now_iso(),
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
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to update cycle: {exc}") from exc

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
