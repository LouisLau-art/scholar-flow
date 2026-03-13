from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.models.manuscript import normalize_status
from app.services.production_workspace_service_workflow_common import (
    ACTIVE_CYCLE_STATUSES,
    POST_ACCEPTANCE_ALLOWED,
    is_table_missing_error,
    is_missing_column_error,
    production_sop_schema_http_error,
)


def _find_display_cycle(cycles: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    from app.services.production_workspace_service import _derive_cycle_stage
    active = None
    latest_approved = None
    for row in cycles:
        stage = _derive_cycle_stage(status=row.get("status"), stage=row.get("stage"))
        if stage and stage not in {"cancelled", "ready_to_publish"}:
            if active is None:
                active = row
        if stage == "ready_to_publish":
            if latest_approved is None:
                latest_approved = row
    return active, (active or latest_approved)


class ProductionWorkspaceWorkflowCycleContextQueueMixin:
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
        active, display_cycle = _find_display_cycle(cycles)
        self._ensure_editor_access(
            manuscript=manuscript,
            user_id=user_id,
            roles=roles,
            cycle=display_cycle,
            purpose="read",
        )

        from app.services.production_workspace_service import _derive_cycle_stage
        active_stage = _derive_cycle_stage(status=active.get("status"), stage=active.get("stage")) if active else None

        manuscript_status = normalize_status(str(manuscript.get("status") or "")) or ""
        active_layout_id = str((active or {}).get("layout_editor_id") or "").strip() if active else ""
        active_collabs = set(self._normalize_uuid_list((active or {}).get("collaborator_editor_ids"))) if active else set()
        is_manager = bool(roles.intersection({"admin", "managing_editor", "editor_in_chief"}))
        is_cycle_editor = bool(
            "production_editor" in roles and active and (active_layout_id == str(user_id) or str(user_id) in active_collabs)
        )
        can_manage_production = is_manager or is_cycle_editor
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
            "cycle_history": [self._format_cycle(row, include_signed_url=False) for row in cycles],
            "permissions": {
                "can_create_cycle": can_create,
                "can_manage_editors": is_manager,
                "can_upload_galley": bool(
                    can_manage_production
                    and active_stage in {"received", "typesetting", "language_editing", "pdf_preparation", "ae_final_review"}
                ),
                "can_approve": bool(
                    can_manage_production 
                    and active_stage == "ae_final_review"
                ),
            },
        }

    def list_my_queue(
        self,
        *,
        user_id: str,
        profile_roles: list[str] | None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        roles = self._roles(profile_roles)
        if not roles.intersection({"admin", "managing_editor", "editor_in_chief", "production_editor", "assistant_editor"}):
            raise HTTPException(status_code=403, detail="Forbidden")

        safe_limit = max(1, min(int(limit or 50), 200))
        uid = str(user_id)
        cycles: list[dict[str, Any]] = []
        
        from app.services.production_workspace_service import _derive_cycle_stage, _derive_current_assignee_id
        
        try:
            sop_select = (
                "id,manuscript_id,cycle_no,status,stage,current_assignee_id,"
                "coordinator_ae_id,typesetter_id,language_editor_id,pdf_editor_id,"
                "layout_editor_id,collaborator_editor_ids,proof_due_at,updated_at,created_at"
            )
            primary = (
                self.client.table("production_cycles")
                .select(sop_select)
                .or_(
                    f"current_assignee_id.eq.{uid},"
                    f"coordinator_ae_id.eq.{uid},"
                    f"typesetter_id.eq.{uid},"
                    f"language_editor_id.eq.{uid},"
                    f"pdf_editor_id.eq.{uid},"
                    f"layout_editor_id.eq.{uid}"
                )
                .order("updated_at", desc=True)
                .limit(safe_limit * 2)
                .execute()
            )
            cycles.extend(getattr(primary, "data", None) or [])
            
            collab = (
                self.client.table("production_cycles")
                .select(sop_select)
                .contains("collaborator_editor_ids", [uid])
                .order("updated_at", desc=True)
                .limit(safe_limit * 2)
                .execute()
            )
            cycles.extend(getattr(collab, "data", None) or [])
        except Exception as e:
            if any(
                is_missing_column_error(e, col)
                for col in [
                    "stage",
                    "current_assignee_id",
                    "coordinator_ae_id",
                    "typesetter_id",
                    "language_editor_id",
                    "pdf_editor_id",
                    "collaborator_editor_ids",
                ]
            ):
                raise production_sop_schema_http_error("production_cycles queue columns missing") from e
            if is_table_missing_error(e, "production_cycles"):
                raise production_sop_schema_http_error("production_cycles table missing") from e
            raise HTTPException(status_code=500, detail=f"Failed to list production queue: {e}") from e

        unique_cycles: dict[str, dict[str, Any]] = {}
        for row in cycles:
            cycle_id = str(row.get("id") or "").strip()
            if not cycle_id:
                continue
                
            stage = _derive_cycle_stage(status=row.get("status"), stage=row.get("stage"))
            if stage in {"cancelled", "ready_to_publish"}:
                continue
                
            current_assignee_id = _derive_current_assignee_id(row)
            collaborators = self._normalize_uuid_list(row.get("collaborator_editor_ids"))
            
            if (current_assignee_id == uid or 
                uid in collaborators or 
                row.get("layout_editor_id") == uid or
                row.get("coordinator_ae_id") == uid):
                unique_cycles[cycle_id] = row

        selected_cycles = list(unique_cycles.values())
        selected_cycles.sort(
            key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""),
            reverse=True,
        )
        selected_cycles = selected_cycles[:safe_limit]
        if not selected_cycles:
            return []

        manuscript_ids = [
            str(row.get("manuscript_id") or "").strip()
            for row in selected_cycles
            if str(row.get("manuscript_id") or "").strip()
        ]
        manuscript_ids = list(dict.fromkeys(manuscript_ids))
        if not manuscript_ids:
            return []

        try:
            manuscript_resp = (
                self.client.table("manuscripts")
                .select("id,title,status,journal_id,journals(title,slug)")
                .in_("id", manuscript_ids)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to load manuscripts for production queue: {exc}") from exc

        manuscript_rows: list[dict[str, Any]] = getattr(manuscript_resp, "data", None) or []
        manuscript_map = {
            str(row.get("id") or ""): row for row in manuscript_rows if str(row.get("id") or "").strip()
        }

        output: list[dict[str, Any]] = []
        for cycle in selected_cycles:
            manuscript_id = str(cycle.get("manuscript_id") or "").strip()
            manuscript = manuscript_map.get(manuscript_id) or {}
            journal = manuscript.get("journals") or None
            output.append(
                {
                    "manuscript": {
                        "id": manuscript_id,
                        "title": manuscript.get("title") or "Untitled",
                        "status": manuscript.get("status"),
                        "journal": {
                            "id": manuscript.get("journal_id"),
                            "title": (journal or {}).get("title"),
                            "slug": (journal or {}).get("slug"),
                        }
                        if manuscript.get("journal_id") or journal
                        else None,
                    },
                    "cycle": {
                        "id": cycle.get("id"),
                        "cycle_no": cycle.get("cycle_no"),
                        "status": cycle.get("status"),
                        "stage": _derive_cycle_stage(status=cycle.get("status"), stage=cycle.get("stage")),
                        "proof_due_at": cycle.get("proof_due_at"),
                        "updated_at": cycle.get("updated_at") or cycle.get("created_at"),
                    },
                    "action_url": f"/editor/production/{manuscript_id}",
                }
            )
        return output
