from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.models.manuscript import normalize_status
from app.services.production_workspace_service_workflow_common import (
    ACTIVE_CYCLE_STATUSES,
    POST_ACCEPTANCE_ALLOWED,
    is_table_missing_error,
)


def _find_display_cycle(cycles: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    active = next((row for row in cycles if str(row.get("status") or "") in ACTIVE_CYCLE_STATUSES), None)
    latest_approved = next((row for row in cycles if str(row.get("status") or "") == "approved_for_publish"), None)
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
                    and active
                    and str(active.get("status") or "") in {"draft", "in_layout_revision", "author_corrections_submitted"}
                ),
                "can_approve": bool(can_manage_production and active and str(active.get("status") or "") == "author_confirmed"),
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
        except Exception as exc:
            if is_table_missing_error(exc, "production_cycles"):
                raise HTTPException(status_code=500, detail="DB not migrated: production_cycles table missing") from exc
            raise HTTPException(status_code=500, detail=f"Failed to list production queue: {exc}") from exc

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
            pass

        unique_cycles: dict[str, dict[str, Any]] = {}
        for row in cycles:
            cycle_id = str(row.get("id") or "").strip()
            if cycle_id:
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
                        "proof_due_at": cycle.get("proof_due_at"),
                        "updated_at": cycle.get("updated_at") or cycle.get("created_at"),
                    },
                    "action_url": f"/editor/production/{manuscript_id}",
                }
            )
        return output
